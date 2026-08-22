import os
import uuid
import logging
from contextlib import contextmanager
from typing import Generator, Optional
import redis
from django.conf import settings

logger = logging.getLogger(__name__)

INGESTION_LOCK_KEY = "INGESTION_LOCK_KEY"

# Lua script to release lock safely only if the token matches
RELEASE_LOCK_LUA_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class LockAcquisitionError(Exception):
    """Raised when a distributed lock cannot be acquired and raise_on_failure is True."""
    pass


def get_redis_client() -> redis.Redis:
    """Return a configured Redis client instance using settings.REDIS_URL."""
    redis_url = getattr(settings, 'REDIS_URL', os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0'))
    return redis.Redis.from_url(redis_url, decode_responses=True)


@contextmanager
def redis_distributed_lock(
    lock_key: str = INGESTION_LOCK_KEY,
    timeout: int = 600,
    raise_on_failure: bool = False,
    redis_client: Optional[redis.Redis] = None
) -> Generator[bool, None, None]:
    """
    Distributed Redis Lock context manager to prevent race conditions across scheduled tasks:
    - Atomically sets lock_key with a unique UUID token via `SET key token NX EX timeout`.
    - Safely releases the lock on exit using Lua verification so workers only release their own locks.
    - Yields True if acquired, False otherwise (or raises LockAcquisitionError if raise_on_failure=True).
    """
    client = redis_client or get_redis_client()
    lock_token = str(uuid.uuid4())
    acquired = False

    try:
        # Atomic SET key token NX EX timeout
        acquired = bool(client.set(lock_key, lock_token, nx=True, ex=timeout))
    except Exception as e:
        logger.error(f"Redis distributed lock error on key '{lock_key}': {e}")
        if raise_on_failure:
            raise LockAcquisitionError(f"Redis connection failure while acquiring lock '{lock_key}': {e}")
        yield False
        return

    if not acquired:
        logger.info(f"Distributed lock for '{lock_key}' is currently held by another worker.")
        if raise_on_failure:
            raise LockAcquisitionError(f"Could not acquire distributed lock for '{lock_key}'. Lock is currently held.")
        yield False
        return

    try:
        logger.debug(f"Acquired distributed lock '{lock_key}' with token '{lock_token}' for {timeout}s.")
        yield True
    finally:
        # Safe release: verify the token is still ours before deleting
        try:
            client.eval(RELEASE_LOCK_LUA_SCRIPT, 1, lock_key, lock_token)
            logger.debug(f"Released distributed lock '{lock_key}'.")
        except Exception as e:
            # Fallback simple check
            try:
                if client.get(lock_key) == lock_token:
                    client.delete(lock_key)
            except Exception:
                pass
            logger.warning(f"Error during distributed lock release for '{lock_key}': {e}")
