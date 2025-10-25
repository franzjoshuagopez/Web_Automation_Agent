from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.api.routes import router as api_router
from backend.db.db import init_db
from backend.utils.logger import get_logger

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    from backend.db.db import engine
    await engine.dispose()

app = FastAPI(title="Web Automation Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Unexpected server error. Please contact IT support."}
    )

app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Hello from the backend"}