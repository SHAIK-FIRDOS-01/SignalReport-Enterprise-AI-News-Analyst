import os
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# Load env variables (GNEWS_API_KEY, GROQ_API_KEY, etc.)
load_dotenv()

from news_ingestion import NewsIngestionService
from scraper_service import ContentScraperService
from nlp_processing import NLPProcessingService
from ai_service import AIService

app = FastAPI(
    title="SignalReport Ingestion & AI Microservice",
    description="Decoupled high-compute microservice for NLP, LLM, and Ingestion operations.",
    version="1.0.0"
)

# Initialize services
news_service = NewsIngestionService()
scraper_service = ContentScraperService()
nlp_service = NLPProcessingService()
ai_service = AIService()

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

class BriefingArticle(BaseModel):
    title: str
    content: str

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
        answer = await ai_service.answer_question(req.question, req.context)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/synthesize")
async def synthesize_briefing(req: SynthesizeRequest):
    try:
        articles_list = [{"title": a.title, "content": a.content} for a in req.articles]
        briefing = await ai_service.generate_briefing(articles_list)
        return {"briefing": briefing}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
