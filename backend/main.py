from fastapi import FastAPI
from backend.api.routes import router as api_router

app = FastAPI(title="Web Automation Agent")

app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Hello from the backend"}