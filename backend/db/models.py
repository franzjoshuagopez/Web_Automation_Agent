from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Float, JSON, Boolean, UniqueConstraint, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.db.db import Base
from datetime import datetime
from typing import Optional

class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

class DOMPage(Base):
    __tablename__ = "dom_pages"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    #run_id: Mapped[int] = mapped_column(ForeignKey("automation_runs.id"), index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    inspected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    elements: Mapped["DOMElement"] = relationship("DOMElement", back_populates="page", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("url", name="uq_dompage_url"),)

class DOMElement(Base):
    __tablename__ = "dom_elements"
    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("dom_pages.id"), index=True)
    tag: Mapped[str] = mapped_column(String)
    element_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visible: Mapped[bool] = mapped_column(Boolean)
    enabled: Mapped[bool] = mapped_column(Boolean)
    selector_type: Mapped[str] = mapped_column(String)
    selector: Mapped[str] = mapped_column(Text)
    input_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    placeholder: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    options_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    href: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    method: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    page = relationship("DOMPage", back_populates="elements")

class AutomationRun(Base):
    __tablename__ = "automation_runs"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    tools: Mapped[list["AutomationTool"]] = relationship("AutomationTool", back_populates="run", cascade="all, delete-orphan")

class AutomationTool(Base):
    __tablename__ = "automation_tools"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("automation_runs.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    args: Mapped[str] = mapped_column(Text)
    result: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    run: Mapped["AutomationRun"] = relationship("AutomationRun", back_populates="tools")



