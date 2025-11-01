import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

ENV = os.getenv("ENV", "development")

DATABASE_URL =""


if ENV == "production":
    DATABASE_URL = os.getenv("PRODUCTION_BASE_URL")
    if DATABASE_URL is None:
        DATABASE_URL = "sqlite+aiosqlite:///./backend/memory/chatbot.db"
elif ENV == "development":
    DATABASE_URL = os.getenv("DEVELOPMENT_BASE_URL")
    if DATABASE_URL is None:
        DATABASE_URL = "sqlite+aiosqlite:///./backend/memory/chatbot.db"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False
    )

Base = declarative_base()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

