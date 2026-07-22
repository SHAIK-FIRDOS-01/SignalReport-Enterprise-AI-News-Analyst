import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from dotenv import load_dotenv
import redis.asyncio as aioredis

# Load env variables (GNEWS_API_KEY, GROQ_API_KEY, etc.)
load_dotenv()

from news_ingestion import NewsIngestionService
from scraper_service import ContentScraperService
from nlp_processing import NLPProcessingService
from ai_service import AIService
from hn_ingestion import HackerNewsIngestionService

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

# Redis PubSub Listener
async def redis_listener():
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    r = await aioredis.from_url(redis_url)
    pubsub = r.pubsub()
    await pubsub.subscribe('news_alerts')
    
    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = message['data'].decode('utf-8')
                await manager.broadcast(data)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe('news_alerts')
        await r.aclose()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    listener_task = asyncio.create_task(redis_listener())
    yield
    # Shutdown
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="SignalReport Ingestion & AI Microservice",
    description="Decoupled high-compute microservice for NLP, LLM, and Ingestion operations.",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize services
news_service = NewsIngestionService()
scraper_service = ContentScraperService()
nlp_service = NLPProcessingService()
ai_service = AIService()
hn_service = HackerNewsIngestionService()

# Request schemas
class FetchNewsRequest(BaseModel):
    query: str = "AI advancements"
    lang: Optional[str] = None
    country: Optional[str] = None
    max_results: int = 10
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    sortby: Optional[str] = "publishedAt"
    nullable: Optional[str] = None

class FetchHeadlinesRequest(BaseModel):
    category: str = "general"
    query: Optional[str] = None
    lang: Optional[str] = None
    country: Optional[str] = None
    max_results: int = 10
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    nullable: Optional[str] = None

class FetchHNRequest(BaseModel):
    limit: int = 10

class ScrapeRequest(BaseModel):
    url: str

class NLPProcessRequest(BaseModel):
    text: str

class EnhanceRequest(BaseModel):
    content: str
    nlp_context: Dict[str, Any]

class ExplainTermRequest(BaseModel):
    term: str
    context: str

class AskQuestionRequest(BaseModel):
    question: str
    context: str
    source_url: Optional[str] = None

class BriefingArticle(BaseModel):
    title: str
    content: str
    source_url: Optional[str] = None

class SynthesizeRequest(BaseModel):
    articles: list[BriefingArticle]


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "gnews": "configured" if news_service.api_key else "missing_key",
            "groq": "configured" if ai_service.client else "missing_key"
        }
    }

@app.post("/news/fetch")
async def fetch_news(req: FetchNewsRequest):
    try:
        articles = await news_service.fetch_news(
            query=req.query,
            lang=req.lang,
            country=req.country,
            max_results=req.max_results,
            from_date=req.from_date,
            to_date=req.to_date,
            sortby=req.sortby,
            nullable=req.nullable
        )
        return {"articles": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/news/headlines")
async def fetch_top_headlines(req: FetchHeadlinesRequest):
    try:
        articles = await news_service.fetch_top_headlines(
            category=req.category,
            query=req.query,
            lang=req.lang,
            country=req.country,
            max_results=req.max_results,
            from_date=req.from_date,
            to_date=req.to_date,
            nullable=req.nullable
        )
        return {"articles": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/news/hn/top")
async def fetch_hn_top(req: FetchHNRequest):
    try:
        articles = await hn_service.fetch_top_stories(limit=req.limit)
        return {"articles": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/news/hn/new")
async def fetch_hn_new(req: FetchHNRequest):
    try:
        articles = await hn_service.fetch_new_stories(limit=req.limit)
        return {"articles": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scraper/scrape")
async def scrape_content(req: ScrapeRequest):
    try:
        content = await scraper_service.scrape_full_content(req.url)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/nlp/process")
async def process_nlp(req: NLPProcessRequest):
    try:
        result = await nlp_service.process_content(req.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/enhance")
async def enhance_content(req: EnhanceRequest):
    try:
        result = await ai_service.enhance_and_vectorize(req.content, req.nlp_context)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/explain-term")
async def explain_term(req: ExplainTermRequest):
    try:
        definition = await ai_service.explain_term(req.term, req.context)
        return {"definition": definition}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/ask-question")
async def ask_question(req: AskQuestionRequest):
    try:
        answer = await ai_service.answer_question(req.question, req.context, req.source_url)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/synthesize")
async def synthesize_briefing(req: SynthesizeRequest):
    try:
        articles_list = [{"title": a.title, "content": a.content, "source_url": a.source_url} for a in req.articles]
        briefing = await ai_service.generate_briefing(articles_list)
        return {"briefing": briefing}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect the client to send much, just keep connection open
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

