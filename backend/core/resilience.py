import random
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from django.conf import settings

logger = logging.getLogger(__name__)

DLQ_REDIS_KEY = "celery_dlq"
_IN_MEMORY_DLQ: List[Dict[str, Any]] = []


def calculate_backoff_with_jitter(
    retries: int,
    base: float = 2.0,
    min_jitter: float = 0.1,
    max_jitter: float = 1.0
) -> float:
    """
    Calculate exponential backoff interval with random jitter:
    Formula: 2^retries + uniform(min_jitter, max_jitter)
    Prevents thundering herd problems when upstream APIs return HTTP 429.
    """
    jitter = random.uniform(min_jitter, max_jitter)
    return round((base ** retries) + jitter, 4)


def route_to_dlq(task_name: str, payload: Dict[str, Any], error: str) -> str:
    """
    Route unrecoverable failed task payload to Dead Letter Queue (DLQ).
    """
    msg_id = str(uuid.uuid4())
    record = {
        "id": msg_id,
        "task_name": task_name,
        "payload": payload,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Store in memory for immediate access / fallback
    _IN_MEMORY_DLQ.insert(0, record)
    if len(_IN_MEMORY_DLQ) > 500:
        _IN_MEMORY_DLQ.pop()
        
    # Attempt to persist to Redis DLQ list
    try:
        from core.redis_client import get_redis_client
        r = get_redis_client()
        r.lpush(DLQ_REDIS_KEY, json.dumps(record))
        r.ltrim(DLQ_REDIS_KEY, 0, 999)
    except Exception as e:
        logger.debug(f"Redis not available for DLQ persistence; using memory store: {e}")

    logger.error(f"[DLQ] Task '{task_name}' failed permanently: {error} (Message ID: {msg_id})")
    return msg_id


def get_dlq_messages(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent Dead Letter Queue messages."""
    try:
        from core.redis_client import get_redis_client
        r = get_redis_client()
        raw_items = r.lrange(DLQ_REDIS_KEY, 0, limit - 1)
        if raw_items:
            return [json.loads(item) for item in raw_items]
    except Exception:
        pass
        
    return _IN_MEMORY_DLQ[:limit]
