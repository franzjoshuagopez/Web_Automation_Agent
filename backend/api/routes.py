from fastapi import APIRouter, WebSocket

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            data = await websocket.receive_text()
            await websocket.send_text(f"You said: {data}")
        except Exception:
            break
