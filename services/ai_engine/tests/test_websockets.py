import os
import sys
import json
import asyncio
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent.parent.parent
ai_engine_dir = root_dir / "services" / "ai_engine"

for p in [str(root_dir), str(ai_engine_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from services.ai_engine.websocket_manager import ConnectionManager
from services.ai_engine.main import app


@pytest.mark.asyncio
async def test_connection_manager_broadcast():
    """Verify ConnectionManager connects, disconnects, and broadcasts JSON messages."""
    manager = ConnectionManager()
    
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    
    await manager.connect(ws1)
    await manager.connect(ws2)
    assert len(manager.active_connections) == 2
    
    payload = {
        "type": "new_articles",
        "count": 5,
        "message": "5 new AI signals ingested!"
    }
    
    await manager.broadcast(payload)
    
    ws1.send_json.assert_awaited_once_with(payload)
    ws2.send_json.assert_awaited_once_with(payload)
    
    manager.disconnect(ws1)
    assert len(manager.active_connections) == 1
    assert ws2 in manager.active_connections


def test_websocket_endpoint_connection():
    """Verify WebSocket client connects to /ws/alerts and receives live broadcasts."""
    client = TestClient(app)
    
    with client.websocket_connect("/ws/alerts") as websocket:
        # Send a heartbeat/ping from client
        websocket.send_json({"action": "ping"})
        data = websocket.receive_json()
        assert data.get("type") in ("pong", "connected")


@pytest.mark.asyncio
async def test_redis_pubsub_bridge_dispatches_to_manager():
    """Verify Redis PubSub listener receives published messages and calls manager.broadcast."""
    from services.ai_engine.websocket_manager import process_pubsub_message
    
    manager = ConnectionManager()
    ws = AsyncMock()
    await manager.connect(ws)
    
    raw_redis_msg = {
        "type": "message",
        "channel": b"news_alerts",
        "data": json.dumps({
            "type": "signal_alert",
            "title": "DeepSeek V3 Released",
            "signal_type": "LAUNCH"
        }).encode("utf-8")
    }
    
    await process_pubsub_message(raw_redis_msg, manager)
    
    ws.send_json.assert_awaited_once()
    broadcasted = ws.send_json.call_args[0][0]
    assert broadcasted["title"] == "DeepSeek V3 Released"
    assert broadcasted["signal_type"] == "LAUNCH"
