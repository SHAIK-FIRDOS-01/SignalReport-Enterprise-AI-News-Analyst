import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("ai_engine.websocket")


class ConnectionManager:
    """
    Manages active client WebSocket connections and broadcasts real-time intelligence alerts.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        if hasattr(websocket, "accept"):
            try:
                await websocket.accept()
            except Exception:
                pass
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active clients: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcasts JSON payload to all connected clients, pruning dead sockets."""
        dead_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug(f"Error sending message to client ({e}); marking for removal.")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


async def process_pubsub_message(raw_message: Dict[str, Any], manager: ConnectionManager):
    """
    Process raw Redis Pub/Sub message payload and broadcast to WebSocket manager.
    """
    if not raw_message or raw_message.get("type") != "message":
        return

    data = raw_message.get("data")
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    
    if isinstance(data, str):
        try:
            payload = json.loads(data)
        except Exception:
            payload = {"type": "raw_alert", "message": data}
    elif isinstance(data, dict):
        payload = data
    else:
        payload = {"type": "alert", "data": str(data)}

    await manager.broadcast(payload)


async def redis_pubsub_listener(manager: ConnectionManager, redis_url: str):
    """
    Background worker listening to Redis 'news_alerts' channel and forwarding to WebSockets.
    """
    import redis.asyncio as aioredis
    logger.info(f"Connecting to Redis Pub/Sub at {redis_url}...")
    
    try:
        r = aioredis.from_url(redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe("news_alerts")
        logger.info("Successfully subscribed to 'news_alerts' Redis channel.")

        async for message in pubsub.listen():
            await process_pubsub_message(message, manager)
    except Exception as e:
        logger.warning(f"Redis Pub/Sub listener encountered error: {e}")
