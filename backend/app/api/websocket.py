from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as redis
import json

from app.core.config import settings

websocket_router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}
    
    async def connect(self, project_id: int, websocket: WebSocket):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
    
    def disconnect(self, project_id: int, websocket: WebSocket):
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
    
    async def broadcast(self, project_id: int, message: dict):
        """Broadcast message to all connections for a project."""
        if project_id in self.active_connections:
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


@websocket_router.websocket("/ws/projects/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: int
):
    """WebSocket endpoint for real-time project updates."""
    await manager.connect(project_id, websocket)
    
    # Subscribe to Redis pub/sub for this project
    redis_client = redis.from_url(settings.redis_url)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"project:{project_id}:updates")
    
    try:
        # Listen for messages from Redis
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await manager.broadcast(project_id, data)
    except WebSocketDisconnect:
        manager.disconnect(project_id, websocket)
        await pubsub.unsubscribe(f"project:{project_id}:updates")
    except Exception as e:
        manager.disconnect(project_id, websocket)
        await pubsub.unsubscribe(f"project:{project_id}:updates")
        raise e
    finally:
        await redis_client.close()