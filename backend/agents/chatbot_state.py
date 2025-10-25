from typing import TypedDict, List, Union, Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from backend.db.models import AutomationRun, AutomationTool

class StepLogItem(TypedDict):
    step: int
    action: str
    status: str

class ChatBotState(TypedDict):
    messages: List[BaseMessage]
    next: Optional[str]
    loop_count: int
    user_goal: str
    current_step: str
    goal_complete: bool
    steps_log: List[StepLogItem]
    automation_run_id: Optional[int]
    automation_tool_id: Optional[int]