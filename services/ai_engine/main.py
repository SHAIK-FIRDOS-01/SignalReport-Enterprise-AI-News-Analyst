import asyncio
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

try:
    from .config import settings
    from .security import verify_internal_service_key
    from .routers.enrich import router as enrich_router
    from .websocket_manager import ConnectionManager, redis_pubsub_listener
except ImportError:
    from config import settings
    from security import verify_internal_service_key
    from routers.enrich import router as enrich_router
    from websocket_manager import ConnectionManager, redis_pubsub_listener

logging.basicConfig(level=logging.INFO if not settings.DEBUG else logging.DEBUG)
logger = logging.getLogger("ai_engine")

ws_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SignalReport AI Engine...")
    # Spawn Redis Pub/Sub listener in background
    listener_task = None
    if settings.REDIS_URL:
        try:
            listener_task = asyncio.create_task(
                redis_pubsub_listener(ws_manager, settings.REDIS_URL)
            )
        except Exception as e:
            logger.warning(f"Could not initialize Redis Pub/Sub listener: {e}")

    yield
    
    logger.info("Shutting down SignalReport AI Engine...")
    if listener_task:
        listener_task.cancel()


app = FastAPI(
    title="SignalReport AI Engine",
    description="Decoupled High-Compute AI, NLP, Vector Generation, and Ingestion Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount internal API routers
app.include_router(enrich_router)


# Global Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status": "error"}
    )


# WebSocket Real-Time Alert Stream Endpoint
@app.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket endpoint streaming published intelligence alerts to connected clients.
    """
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Subscribed to SignalReport real-time intelligence alerts stream"
        })
        while True:
            data = await websocket.receive_json()
            if isinstance(data, dict) and data.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WebSocket client error ({e}); disconnecting.")
        ws_manager.disconnect(websocket)


# Request schemas for legacy and RPC endpoints
class EnhanceRequest(BaseModel):
    content: str
    nlp_context: Dict[str, Any] = {}


class ExplainTermRequest(BaseModel):
    term: str
    context: str = ""


class AskQuestionRequest(BaseModel):
    question: str
    context: str
    source_url: Optional[str] = None


class BriefingArticle(BaseModel):
    title: str
    content: str
    source_url: Optional[str] = None


class SynthesizeRequest(BaseModel):
    articles: List[BriefingArticle]


class NLPProcessRequest(BaseModel):
    text: str


@app.get("/health")
async def health_check():
    """Unauthenticated health check for load balancer and cluster orchestration."""
    return {
        "status": "healthy",
        "service": "ai_engine",
        "version": "1.0.0"
    }


# Protected RPC Endpoints
@app.post("/ai/enhance", dependencies=[Depends(verify_internal_service_key)])
async def enhance_content(req: EnhanceRequest):
    return {
        "enhanced_content": f"Intelligence Analysis: {req.content[:300]}",
        "credibility_score": 0.85,
        "signal_type": "GENERAL",
        "vector": [0.0] * 384
    }


@app.post("/ai/explain-term", dependencies=[Depends(verify_internal_service_key)])
async def explain_term(req: ExplainTermRequest):
    return {
        "definition": f"Term definition for '{req.term}' in context of technology intelligence."
    }


@app.post("/ai/ask-question", dependencies=[Depends(verify_internal_service_key)])
async def ask_question(req: AskQuestionRequest):
    return {
        "answer": f"Analysis based on context for question: {req.question}"
    }


@app.post("/ai/synthesize", dependencies=[Depends(verify_internal_service_key)])
async def synthesize_briefing(req: SynthesizeRequest):
    return {
        "briefing": f"Executive Tech Intelligence Briefing summarizing {len(req.articles)} signals."
    }


@app.post("/nlp/process", dependencies=[Depends(verify_internal_service_key)])
async def process_nlp(req: NLPProcessRequest):
    return {
        "sentiment_score": 0.0,
        "entities": [],
        "text_length": len(req.text)
    }
