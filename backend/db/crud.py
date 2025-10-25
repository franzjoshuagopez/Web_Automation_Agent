import asyncio
import json
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.future import select
from sqlalchemy import delete, func
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from langchain_core.messages import HumanMessage, AIMessage
from backend.db.db import AsyncSessionLocal
from backend.db.models import Conversation, Message, DOMPage, DOMElement, AutomationRun, AutomationTool
from backend.agents.chatbot_state import ChatBotState
from backend.utils.decorators import with_retry
from backend.utils.logger import get_logger

logger = get_logger(__name__)

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))  
async def get_or_create_conversation(session_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            conv = Conversation(session_id=session_id)
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
        
        return conv

async def load_conversation_state(session_id: str) -> ChatBotState:
    conv = await get_or_create_conversation(session_id)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Message).where(Message.conversation_id == conv.id).order_by(Message.id)
        )
        messages = result.scalars().all()
    
    state: ChatBotState = {
        "messages": [],
        "next": None,
        "loop_count": 0,
        "user_goal": "",
        "current_step": "",
        "goal_complete": False,
        "steps_log": [],
        "automation_run_id": 0,
        "automation_tool_id": 0
        }

    for msg in messages:
        if msg.role == "user":
            state["messages"].append(HumanMessage(content=msg.content))
        else:
            state["messages"].append(AIMessage(content=msg.content))
    
    return state

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))    
async def add_message(conversation_id: int, role: str, content: str):
    async with AsyncSessionLocal() as session:
        msg = Message(conversation_id=conversation_id, role=role, content=content)
        try:
            session.add(msg)
            await session.commit()
            await session.refresh(msg)
        except SQLAlchemyError as e:
            await session.rollback()
            logger.exception("DB error while adding message")
            raise

        return msg

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def get_or_create_dom_page(url: str):
    async with AsyncSessionLocal() as session:
        page = await session.scalar(select(DOMPage).where(DOMPage.url == url))
        if not page:
            page = DOMPage(url=url)
            session.add(page)
            await session.commit()
            await session.refresh(page)
        return page
    
@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def add_dom_elements(page_id: int, elements_info: list[dict]):
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(DOMElement).where(DOMElement.page_id == page_id)
        )

        await session.commit()

        elements = [
            DOMElement(
                page_id=page_id,
                tag=info.get("tag"),
                element_id=info.get("id"),
                name=info.get("name"),
                text=info.get("text"),
                visible=info.get("visible"),
                enabled=info.get("enabled"),
                selector_type=info.get("selector_type"),
                selector=info.get("selector"),
                input_type=info.get("type"),
                placeholder=info.get("placeholder"),
                options_count=info.get("options_count"),
                href=info.get("href"),
                value=info.get("value"),
                action=info.get("action"),
                method=info.get("method")
            )
            for info in elements_info
        ] 
        
        logger.info(f"[add_dom_elements] Adding {len(elements)} elements for page_id={page_id}")

        session.add_all(elements)

        await session.commit()

        logger.info("[add_dom_elements] Commit complete")

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def get_dom_elements_by_page_id(page_id: int):
    async with AsyncSessionLocal() as session:
        stmt = select(DOMElement).where(DOMElement.page_id == page_id)
        result = await session.scalars(stmt)

        return result.all()

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def create_run(goal: str):
    async with AsyncSessionLocal() as session:
        new_run = AutomationRun(goal=goal, status="running")
        session.add(new_run)
        await session.commit()
        await session.refresh(new_run)

        return new_run

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def get_run_by_id(run_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AutomationRun).where(AutomationRun.id == run_id))
        
        return result.scalar_one_or_none()

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def get_runs(status: Optional[str] = None):
    async with AsyncSessionLocal() as session:
        stmt = select(AutomationRun).order_by(AutomationRun.started_at.desc())
        if status:
            stmt = stmt.where(AutomationRun.status == status)
        result = await session.execute(stmt)
        
        return result.scalars().all()

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def update_run_status(run_id: Optional[int], status: str):
    if run_id is None:
        return
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AutomationRun).where(AutomationRun.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            return None
        run.status = status
        run.finished_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(run)

        return run

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def delete_run(run_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(delete(AutomationRun).where(AutomationRun.id == run_id))
        await session.commit()

        return result.rowcount > 0

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def create_tool(run_id: Optional[int], name: str, args: dict):
    if run_id is None:
        return
    
    async with AsyncSessionLocal() as session:
        new_tool = AutomationTool(
            run_id=run_id,
            name=name,
            args=json.dumps(args),
            status="running"
        )
        session.add(new_tool)
        await session.commit()
        await session.refresh(new_tool)

        return new_tool

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def get_tool_by_id(tool_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AutomationTool).where(AutomationTool.id == tool_id))

        return result.scalar_one_or_none()

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def get_tools_by_run(run_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AutomationTool).where(AutomationTool.run_id == run_id).order_by(AutomationTool.started_at.asc()))

        return result.scalars().all()

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def update_tool_status(tool_id: int, status: str, result_data: Optional[dict]):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AutomationTool).where(AutomationTool.id == tool_id))
        tool = result.scalar_one_or_none() 
        if not tool:
            return None
        tool.status = status
        if result_data is not None:
            tool.result = json.dumps(result_data)
        tool.finished_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(tool)

        return tool

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def delete_tool(tool_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(delete(AutomationTool).where(AutomationTool.id == tool_id))
        await session.commit()

        return result.rowcount > 0

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def count_elements():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count()).select_from(DOMElement))
        
        return result.scalar() or 0

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def get_total_runtime():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AutomationRun.started_at, AutomationRun.finished_at).where(AutomationRun.finished_at.is_not(None)))
        rows = result.all()
        total_seconds = 0
        for started_at, finished_at in rows:
            if started_at and finished_at:
                total_seconds += (finished_at - started_at).total_seconds()
        
        return round(total_seconds / 60, 1)

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def get_success_rate():
    async with AsyncSessionLocal() as session:
        total_q = await session.execute(select(func.count()).select_from(AutomationRun))
        total = total_q.scalar() or 0
        if total == 0:
            return 0.0
        
        success_q = await session.execute(select(func.count()).select_from(AutomationRun).where(AutomationRun.status == "Completed"))
        success = success_q.scalar() or 0
        
        return round((success / total) * 100, 1)

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def get_failed_actions():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count()).select_from(AutomationRun).where(AutomationRun.status == "Failed"))

        return result.scalar() or 0

@with_retry(retries=3, delay=0.5, exceptions=(OperationalError, SQLAlchemyError))
async def get_recent_activity(limit: int = 10):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AutomationTool).order_by(AutomationTool.started_at.desc()).limit(limit))
        tools = result.scalars().all()

        def map_tool(tool):
            status = "success" if (tool.status or "").lower() == "success" else "error"
            time_ago = humanize_time(tool.started_at)
            
            return {
                "id": tool.id,
                "action": tool.name or "Unknown tool",
                "time": time_ago,
                "status": status,
            }
        
        return [map_tool(tool) for tool in tools]

def humanize_time(dt: datetime):
    if not dt:
        return "unknown"
    
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    diff = now - dt

    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        mins = int(diff.total_seconds() / 60)
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    elif diff < timedelta(days=1):
        hrs = int(diff.total_seconds() / 3600)
        return f"{hrs} hour{'s' if hrs !=1 else ''} ago"
    else:
        days = diff.days
        return f"{days} day{'s' if days != 1 else ''} ago"