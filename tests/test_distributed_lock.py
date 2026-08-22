import os
import sys
from pathlib import Path
import pytest
import fakeredis

# Set up paths
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"

for p in [str(root_dir), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()

from core.redis_client import (
    redis_distributed_lock,
    INGESTION_LOCK_KEY,
    LockAcquisitionError,
    get_redis_client,
)


@pytest.fixture
def fake_redis():
    server = fakeredis.FakeServer()
    client = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    return client


def test_lock_constants():
    """Verify INGESTION_LOCK_KEY constant."""
    assert INGESTION_LOCK_KEY == "INGESTION_LOCK_KEY"


def test_distributed_lock_acquisition_and_release(fake_redis):
    """Verify Worker A acquires lock and releases it cleanly upon context exit."""
    assert fake_redis.get(INGESTION_LOCK_KEY) is None
    
    with redis_distributed_lock(lock_key=INGESTION_LOCK_KEY, timeout=600, redis_client=fake_redis) as acquired:
        assert acquired is True
        # Verify key exists in redis with expiration
        lock_val = fake_redis.get(INGESTION_LOCK_KEY)
        assert lock_val is not None
        ttl = fake_redis.ttl(INGESTION_LOCK_KEY)
        assert 0 < ttl <= 600
        
    # After exit, lock must be released
    assert fake_redis.get(INGESTION_LOCK_KEY) is None


def test_distributed_lock_mutual_exclusion(fake_redis):
    """Verify Worker B fails to acquire lock while Worker A holds it."""
    with redis_distributed_lock(lock_key=INGESTION_LOCK_KEY, timeout=600, redis_client=fake_redis) as worker_a_acquired:
        assert worker_a_acquired is True
        
        # Worker B tries to acquire same lock
        with redis_distributed_lock(lock_key=INGESTION_LOCK_KEY, timeout=600, redis_client=fake_redis) as worker_b_acquired:
            assert worker_b_acquired is False
            
    # Now that Worker A has exited, Worker B should succeed
    with redis_distributed_lock(lock_key=INGESTION_LOCK_KEY, timeout=600, redis_client=fake_redis) as worker_b_retry:
        assert worker_b_retry is True


def test_distributed_lock_raises_on_failure_flag(fake_redis):
    """Verify raise_on_failure=True raises LockAcquisitionError if lock is busy."""
    with redis_distributed_lock(lock_key=INGESTION_LOCK_KEY, timeout=600, redis_client=fake_redis) as acquired:
        assert acquired is True
        with pytest.raises(LockAcquisitionError):
            with redis_distributed_lock(
                lock_key=INGESTION_LOCK_KEY,
                timeout=600,
                raise_on_failure=True,
                redis_client=fake_redis
            ):
                pass


def test_distributed_lock_releases_on_exception(fake_redis):
    """Verify lock is released even if exception occurs inside with block."""
    try:
        with redis_distributed_lock(lock_key=INGESTION_LOCK_KEY, timeout=600, redis_client=fake_redis) as acquired:
            assert acquired is True
            raise RuntimeError("Task failed catastrophically")
    except RuntimeError:
        pass
        
    # Lock must be released despite exception
    assert fake_redis.get(INGESTION_LOCK_KEY) is None
