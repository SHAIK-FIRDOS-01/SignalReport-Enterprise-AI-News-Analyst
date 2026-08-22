import os
from pathlib import Path
import pytest


def test_backend_workspace_isolation():
    """Verify /backend has independent requirements.txt and .env.example with required variables."""
    root_dir = Path(__file__).resolve().parent.parent
    backend_dir = root_dir / "backend"
    
    assert backend_dir.exists(), "backend directory must exist"
    
    req_file = backend_dir / "requirements.txt"
    assert req_file.exists(), "backend/requirements.txt must exist"
    req_content = req_file.read_text()
    assert "Django" in req_content
    assert "argon2-cffi" in req_content
    assert "PyJWT" in req_content
    assert "pgvector" in req_content
    assert "django-redis" in req_content
    
    env_example = backend_dir / ".env.example"
    assert env_example.exists(), "backend/.env.example must exist"
    env_content = env_example.read_text()
    assert "SECRET_KEY" in env_content
    assert "INTERNAL_SERVICE_KEY" in env_content
    assert "REDIS_URL" in env_content
    assert "DB_NAME" in env_content
    assert "MICROSERVICE_URL" in env_content


def test_ai_engine_workspace_isolation():
    """Verify /services/ai_engine has independent requirements.txt, .env.example, and FastAPI scaffold."""
    root_dir = Path(__file__).resolve().parent.parent
    ai_engine_dir = root_dir / "services" / "ai_engine"
    
    assert ai_engine_dir.exists(), "services/ai_engine directory must exist"
    
    req_file = ai_engine_dir / "requirements.txt"
    assert req_file.exists(), "services/ai_engine/requirements.txt must exist"
    req_content = req_file.read_text()
    assert "fastapi" in req_content.lower()
    assert "uvicorn" in req_content.lower()
    assert "pydantic" in req_content.lower()
    assert "httpx" in req_content.lower()
    assert "redis" in req_content.lower()
    
    env_example = ai_engine_dir / ".env.example"
    assert env_example.exists(), "services/ai_engine/.env.example must exist"
    env_content = env_example.read_text()
    assert "INTERNAL_SERVICE_KEY" in env_content
    assert "GROQ_API_KEY" in env_content
    assert "REDIS_URL" in env_content


def test_ai_engine_app_import():
    """Verify FastAPI application instance in /services/ai_engine can be imported and configured."""
    import sys
    root_dir = Path(__file__).resolve().parent.parent
    ai_engine_dir = str(root_dir / "services" / "ai_engine")
    if ai_engine_dir not in sys.path:
        sys.path.insert(0, ai_engine_dir)
        
    from main import app
    from fastapi import FastAPI
    assert isinstance(app, FastAPI)
    assert "AI Engine" in app.title or "SignalReport" in app.title
