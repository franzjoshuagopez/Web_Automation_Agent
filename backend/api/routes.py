import uuid
from typing import cast, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from backend.agents.chatbot_state import ChatBotState
from backend.graphs.chatbot_graph import chatbot_graph
from backend.utils.ws_manager import connect, disconnect
from backend.db.crud import get_or_create_conversation, add_message, load_conversation_state
from backend.utils.decorators import with_retry
from backend.utils.logger import get_logger
from backend.tools.selenium_tools import DOM_CACHE
import backend.tools.web_automation_tools as tools
from backend.db.crud import count_elements, get_all_dom_elements, get_total_runtime, get_success_rate, get_failed_actions, get_recent_activity

logger = get_logger(__name__)

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.get("/api/settings")
def get_settings():
    """
        get current settings
    """
    return tools.CURRENT_SETTINGS

@router.post("/api/settings")
def update_settings(new_settings: tools.Settings):
    """
        Update settings and save to file
    """
    tools.CURRENT_SETTINGS = new_settings
    tools.save_settings(new_settings)

    return {"status": "ok", "updated": tools.CURRENT_SETTINGS.model_dump()}


@router.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await connect(websocket)

    session_id = str(uuid.uuid4())
    conversation = await get_or_create_conversation(session_id)

    state : ChatBotState = await load_conversation_state(session_id)

    try:
        while True:
            
            user_message = await websocket.receive_text()
            state["messages"].append(HumanMessage(content=user_message))

            await add_message(conversation.id, "user", user_message)


            result: Any = await call_agent(chatbot_graph, state)

            if isinstance(result, dict) and "messages" in result and isinstance(result["messages"], list):
                state = cast(ChatBotState,result)
            else:
                logger.warning("chatbot_graph returned unexpected result: %r", result)
                if isinstance(result, dict) and isinstance(result.get("messages"), list):
                    state = cast(ChatBotState, {"messages": result["messages"]})

            if state["messages"]:        
                ai_message = state["messages"][-1]
                text = getattr(ai_message, "content", str(ai_message))
                await add_message(conversation.id, "agent", text)
                await websocket.send_text(text)

    except WebSocketDisconnect:
        logger.info("Client disconnected...")
        await websocket.send_text("Client disconnected")
        await websocket.close(code=1000)
    
    except Exception as e:
        logger.exception("Agent call failed completely")
        fallback = "⚠️Failed: Sorry, something went wrong with the agent. Please call IT support."
        await websocket.send_text(fallback)
        await websocket.close(code=1000)
    
    finally:
        disconnect(websocket)
        
        return

@with_retry(retries=3, delay=1.0, exceptions=(Exception,))
async def call_agent(agent, state):
    """
        agent handler function for retries
    """
    config = RunnableConfig(recursion_limit=100)

    return await agent.ainvoke(state, config=config)

@router.get("/api/elements")
async def get_elements():
    """
        Returns all DOM elements inspected so far
    """
    dom_elements = await get_all_dom_elements()
    return dom_elements

@router.get("/api/dashboard")
async def get_dashboard_summary():
    stats = {
        "elements_inspected": await count_elements(),
        "total_runtime": await get_total_runtime(),
        "success_rate": await get_success_rate(),
        "failed_actions": await get_failed_actions(),
    }
    recent_actions = await get_recent_activity()

    return {"stats": stats, "recent_actions": recent_actions}
