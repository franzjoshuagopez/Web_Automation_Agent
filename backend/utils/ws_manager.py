from typing import Set
from fastapi import WebSocket
import asyncio

active_connections: Set[WebSocket] = set()
MAIN_LOOP = asyncio.get_event_loop()

async def connect(ws: WebSocket):
    await ws.accept()
    active_connections.add(ws)

def disconnect(ws: WebSocket):
    active_connections.discard(ws)

async def broadcast(message: str):
    dead = []
    for ws in active_connections:
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    
    for d in dead:
        active_connections.discard(d)

def safe_broadcast(message: str):
    asyncio.run_coroutine_threadsafe(broadcast(message), MAIN_LOOP)
