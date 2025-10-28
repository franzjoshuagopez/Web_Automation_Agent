from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from backend.agents.chatbot_state import ChatBotState
from backend.agents.chatbot_agent import agent_chat, agent_web_automation, route_messages, execute_tools, should_continue, finalize_run
from backend.tools.web_automation_tools import selenium_toolkit
from backend.utils.logger import get_logger

logger = get_logger(__name__)

#tool_node = ToolNode(tools=selenium_toolkit)

logger.info("Building graph...")



graph_builder = StateGraph(ChatBotState)

graph_builder.add_node("chat", agent_chat)
graph_builder.add_node("web_agent", agent_web_automation)
graph_builder.add_node("router", route_messages)
graph_builder.add_node("tool", execute_tools)
graph_builder.add_node("should_continue", should_continue)
graph_builder.add_node("finalize_run", finalize_run)

graph_builder.add_edge(START, "router")

graph_builder.add_conditional_edges(
    "router",
    lambda state: state["next"],
    {
        "chat": "chat",
        "web_agent": "web_agent"
    }
)

graph_builder.add_edge("chat", END)

graph_builder.add_conditional_edges(
    "web_agent",
    lambda state: (
        "tool" if getattr(state["messages"][-1], "tool_calls", None) else "should_continue"
    ),
    {
        "tool": "tool",
        "should_continue": "should_continue"
    }
)

graph_builder.add_edge("tool", "should_continue")

graph_builder.add_edge("finalize_run", END)

chatbot_graph = graph_builder.compile()

logger.info("Building graph completed!")