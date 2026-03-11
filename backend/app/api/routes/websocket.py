import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.mock_data import MockDataService

router = APIRouter()

# Connection manager
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, data: dict):
        msg = json.dumps(data, default=str)
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)


manager = ConnectionManager()


@router.websocket("/live")
async def websocket_live(ws: WebSocket):
    """
    WebSocket endpoint that streams live traffic events.
    Clients receive events every ~2 seconds:
      - traffic_update: vehicle counts per junction
      - signal_change: new signal phase
      - emergency: emergency vehicle detected
      - stats: aggregated dashboard stats
    """
    await manager.connect(ws)
    mock = MockDataService()

    try:
        tick = 0
        while True:
            tick += 1
            events = mock.generate_tick(tick)
            for event in events:
                await ws.send_text(json.dumps(event, default=str))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)
