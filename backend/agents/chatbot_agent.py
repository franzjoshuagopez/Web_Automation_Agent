import re
import asyncio
from langchain_groq import ChatGroq
from langgraph.types import Send
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage, ToolMessage
from backend.agents.chatbot_state import ChatBotState
from backend.utils.ws_manager import safe_broadcast
from backend.utils.config import settings, max_history
from backend.tools.web_automation_tools import selenium_toolkit, TOOLS_REGISTRY
from backend.utils.logger import get_logger
import backend.tools.web_automation_tools as tools
from backend.db.crud import AutomationRun, AutomationTool, create_run, create_tool, update_run_status, update_tool_status

logger = get_logger(__name__)

llm_chat = ChatGroq(
    model=settings.GROQ_MODEL,
    temperature=settings.TEMPERATURE
    )

llm_with_tools = ChatGroq(
     model=settings.GROQ_MODEL,
     temperature=settings.TEMPERATURE,
     ).bind_tools(selenium_toolkit)

def agent_chat(state: ChatBotState) -> ChatBotState:
    """
        Take conversation state, return AI response.  
    """
    initial_prompt = SystemMessage(content="""
    You are a chatbot.
    - You will act as a friend to the user. you can talk about mundane topics and recent events.
    - Keep your replies short (1 - 3 sentences)
    - Respond in a human like fashion. do not sound robotic.
    - You will NOT accept orders from the user
    - You will NOT do tasks for the user
    """)
    
    trimmed_messages = state["messages"][-max_history:]
    
    ai_message = llm_chat.invoke([initial_prompt] + trimmed_messages)
    logger.info(f"AGENT OUTPUT: {ai_message.content}")

    safe_broadcast(f"🤖 AI: {ai_message.content}")

    state["messages"].append(ai_message)

    return state

def agent_web_automation(state: ChatBotState) -> ChatBotState:
    """
        Tool-using agent for browser automation tasks.
    """

    user_goal = state.get("user_goal", "")
    last_user_msg = state["messages"][-1].content if state["messages"] else ""

    initial_prompt = SystemMessage(content=f"""
    You are a web automation assistant that controls a browser using the provided tools.
    Be concise in reasoning (1-2 sentences) and avoid returning large DOM dumps.

    CURRENT USER GOAL: "{user_goal or last_user_msg}"

    Available primitives:
    - launch_browser(url) -> open / navigate (check session first; do not relaunch if session exists)
    - inspect_dom(url, max_elements=...) -> scans & caches DOM; returns: "Number of elements found visible and interactable: N"
    - query_dom_chunk(url, limit, offset, filters) -> returns compact element list from cache
    - get_element_details(selector_type, selector) -> returns detailed input/select values
    - find_element(url, tag, text, name, id) -> quick lookup returning a single element dict (if cached)
    - click_element(selector_type, selector)
    - type_text(selector_type, selector, text, clear_first=True)
    - select_dropdown(selector_type, selector, option, option_type)
    - check_checkbox(selector_type, selector)
    - read_text(selector_type, selector)
    - read_table(selector_type, selector)
    - get_attribute(selector_type, selector, attribute_name)
    - wait_for_element(selector_type, selector, condition) -> fallback for unusual dynamic cases

    Guidelines & constraints:
    1. Inspect vs Query
    - Use `inspect_dom` only to refresh/seed the DOM cache (max_elements=1000). It returns a short summary count.
    - Use `inspect_dom` when you think the website is in a new page or the url has changed before using `query_dom_chunk(...)` or other tools.
    - Use `query_dom_chunk(...)` to retrieve compact candidates; page with `offset` to fetch more.

    2. Picking & acting on elements
    - **Never invent selectors.** Use the provided `selector` from `query_dom_chunk` / `find_element` / `get_element_details`.
    - Prefer selecting by `idx` from `query_dom_chunk`; then call action tools with that element's `selector_type`+`selector`.
    - You do **not** need to call `wait_for_element` before every action — action tools already include a reasonable wait. Use `wait_for_element` only for unusual dynamic cases (long delays, new navigation).

    3. Safety and idempotency
    - Check `steps_log` and the current browser session state before repeating actions (e.g., avoid relaunching).
    - Limit to **at most 3 tool calls** per reasoning step; continue across graph iterations if needed.
    - Avoid destructive actions (account creation, purchases) unless user explicitly requests and confirms.

    4. Token efficiency
    - Do not ask to dump the full DOM. Work with compact `query_dom_chunk` results and request `get_element_details` only for elements you will act on.

    5. User interaction
    - If critical input (username/password/email) is missing, ask the user one concise clarifying question.
    - Do not store secrets in persistent state; request them from the user at point of use only.

    6. Success detection & termination
    - The USER is responsible for defining verification criteria (e.g., expected text, element, or URL change).
    - If no explicit verification criteria are provided, DO NOT invent or guess any. 
      Respond to the user: "User goal: '<insert user goal here>' has been completed. How should I verify success?"
    - For verification, use only `query_dom_chunk(...)` to check for the provided verification criteria.
      Do not use `find_element` or make assumptions.
    - Never guess or fabricate selectors or verification text.
    - Once the provided verification step is confirmed, respond: "User goal: '<insert user goal here>' has been completed and verified."

    Stop when the user's goal is satisfied or after reporting a clear failure and next steps. Keep tool calls minimal and use paging instead of requesting the entire DOM.
    """)

    trimmed_messages = trim_messages(state["messages"], max_history)

    steps_summary = "\n".join(
        [f"{s['step']}. {s['action']} -> {s['status']}" for s in state.get("steps_log", [])]
    )

    if steps_summary:
        system_steps = f"Steps already executed in this session:\n{steps_summary}\n\n" \
        f"Do not repeate these actions unless required."
    else:
        system_steps = "No steps executed yet."

    
    trimmed_messages.insert(0, SystemMessage(content=system_steps))

    if state.get("user_goal"):
        trimmed_messages.insert(0, SystemMessage(content=f"Reminder: The user's goal is: {state['user_goal']}"))
        

    logger.info(f"TRIMMED MESSAGES: {trimmed_messages}")

    result = llm_with_tools.invoke(
        [initial_prompt] + trimmed_messages
        )
    
    if "reasoning_content" in result.additional_kwargs:
        logger.info(f"AGENT OUTPUT: {result.additional_kwargs['reasoning_content']}")

        safe_broadcast(f"🤖 AI: {result.additional_kwargs['reasoning_content']}")

    state["messages"].append(result)

    if hasattr(result, "additional_kwargs"):
        tool_calls = result.additional_kwargs.get("tool_calls", [])
        logger.info(f"Tool calls: {tool_calls}")

    return state

async def route_messages(state: ChatBotState) -> ChatBotState:
    """
        Routes messages to either 'chat' or 'web_agent' node based on intent.
        returns the node name to use next.
    """
    messages = state.get("messages", [])

    if not messages:
       state["next"] = "chat"
       return state
    
    last_msg = messages[-1]

    if isinstance(last_msg, BaseMessage):
        last_message = str(last_msg.content) or ""
    elif isinstance(last_msg, dict):
        last_message = last_msg.get("content", "")
    elif isinstance(last_msg, str):
        last_message = last_msg
    else:
        last_message = ""
    
    last_message = last_message.lower()

    if isinstance(last_msg, HumanMessage):
        if "user_goal" not in state or state.get("goal_complete"):
            state["user_goal"] = last_message
            state["loop_count"] = 0
            state["goal_complete"] = False
            logger.info(f"New user goal set: {last_message}")
            run = await create_run(last_message)
            state["automation_run_id"] = run.id
        else:
            if any(kw in last_message.lower() for kw in ["open", "launch", "login", "start", "go to", "click", "press", "select"]):
                logger.info("Detected a new user goal mid session. resetting state.")
                state["user_goal"] = last_message
                state["loop_count"] = 0
                state["goal_complete"] = False
                run = await create_run(last_message)
                state["automation_run_id"] = run.id
        
        logger.info(f"USER GOAL IS SET: {state["user_goal"]}")
        logger.info(f"LOOP COUNT RESET: {state["loop_count"]}")

    automation_keywords = [
        "click", "open", "go to", "navigate", "type", "fill", "select",
        "check", "uncheck", "read", "scrape", "inspect", "browser", "element",
        "extract"
    ]

    if any(re.search(rf"\b{kw}\b", last_message) for kw in automation_keywords):
        state["next"] = "web_agent"
    else:
        state["next"] = "chat"
    
    return state

async def execute_tools(state: ChatBotState) -> ChatBotState:
    """
        Executes any tool calls from the last LLM message directly.
    """

    
    state.setdefault("steps_log", [])

    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", [])
    results = []

    for t in tool_calls:
        tool_name = t.get("name")
        args = t.get("args", {})
        run_id = state.get("automation_run_id")

        logger.info(f"Executing tool: {tool_name}")
        
        safe_broadcast(f"🧪 Executing tool: {tool_name}")

        tool_entry = await create_tool(run_id, tool_name, args)

        tool_id = None
        
        if tool_entry is not None:
            tool_id = tool_entry.id

        status = "Failed"
        tool_result = ""

        if tool_name not in TOOLS_REGISTRY:
            tool_result = f"Tool '{tool_name}' not found"
            status = "Failed"
            safe_broadcast(f"Tool '{tool_name}' not found")
        else:
            try:
                tool_result = await TOOLS_REGISTRY[tool_name].arun(args)
                logger.info(f"Executed {tool_name} successfully")
                status = "Success"
                safe_broadcast(f"✅ Executed {tool_name} sucessfully. result: {tool_result}")

            except Exception as e:
                tool_result = f"Tool {tool_name} failed with error: {e}"
                logger.exception(f"Error executing {tool_name}: {e}")
                status = "Failed"
                safe_broadcast(f"❌ Tool {tool_name} failed with error: {e}")
        
        if tool_id:
            await update_tool_status(tool_id, status, {"result": tool_result})

        state["steps_log"].append({
            "step": len(state["steps_log"]) + 1,
            "action": tool_name,
            "status": status
            })

        results.append(
            ToolMessage(
                tool_call_id=t.get("id"),
                name=tool_name,
                content=str(tool_result),
                function= args
            )
        )

    state["messages"].extend(results)
    return state

async def should_continue(state: ChatBotState) -> Send:
    """
        Determine whether the agent should continue reasoing after a tool execution.
        Stops when tool results indicate success or if loop count exceeds safety threshold
    """
    logger.info(f"LOOP COUNT GET: {state.get("loop_count", 0)}")
    state["loop_count"] = state.get("loop_count", 0) + 1
    logger.warning(f"LOOP COUNT IS: {state["loop_count"]}")
    if state["loop_count"] > tools.CURRENT_SETTINGS.loop_limit:
        logger.warning("Loop limit reached. Ending graph execution.")
        return Send("finalize_run", state)
    
    ai_messages = [m for m in state["messages"] if isinstance(m, AIMessage)]
    last_ai = ai_messages[-1] if ai_messages else None
    last_msg = state["messages"][-1]
    

    if last_ai and getattr(last_ai, "tool_calls", None):
        return Send("web_agent", state)
    
    if isinstance(last_msg.content, str):
        lower = last_msg.content.lower()
        goal = state.get("user_goal", "").lower()

        if any(w in lower for w in ["success", "completed", "done", "finished", "satisfied"]) \
            or (goal and goal.split()[0] in lower):
            state["goal_complete"] = True

            return Send("finalize_run", state)
    
    return Send("web_agent", state)

async def finalize_run(state: ChatBotState):
    run_id = state.get("automation_run_id")
    
    if run_id is not None:
        status = "Completed" if state.get("goal_complete") else "Failed"
        await update_run_status(run_id, status)
    
    return state

def trim_messages(messages, max_history=6):
    """
    Trims the conversation history safely, preserving:
    - Human messages (user input)
    - AI tool-call messages + their ToolMessage results
    This prevents orphaned ToolMessages that can cause Harmony errors.
    """
    trimmed = []
    recent = messages[-max_history:]  # limit message window first
    i = 0

    while i < len(recent):
        msg = recent[i]

        # Keep all human messages
        if msg.type == "human":
            trimmed.append(msg)

        # Keep AI tool-call messages and their corresponding ToolMessage result
        elif isinstance(msg, AIMessage) and msg.tool_calls:
            trimmed.append(msg)
            # If next message is a ToolMessage (the result), keep it too
            if i + 1 < len(recent) and isinstance(recent[i + 1], ToolMessage):
                trimmed.append(recent[i + 1])
                i += 1  # skip next since we already added it

        # Keep other AI replies (non-tool reasoning)
        elif isinstance(msg, AIMessage) and not msg.tool_calls:
            trimmed.append(msg)

        i += 1

    return trimmed