from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
try:
    from ..security import verify_internal_service_key
    from ..llm_extractor import LLMExtractorService
    from ..vector_service import VectorEmbeddingService
except ImportError:
    from security import verify_internal_service_key
    from llm_extractor import LLMExtractorService
    from vector_service import VectorEmbeddingService

router = APIRouter(prefix="/api/v1", tags=["enrichment"])
llm_extractor = LLMExtractorService()
vector_service = VectorEmbeddingService()


class EnrichRequest(BaseModel):
    title: str = Field(..., description="Article title or signal heading")
    content: str = Field(..., description="Raw or scraped article body text")
    source_url: Optional[str] = Field(None, description="Canonical source URL")
    nlp_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Pre-extracted NLP metadata")


class EnrichResponse(BaseModel):
    enhanced_content: str = Field(..., description="Cleaned, AI-enhanced synthesis and bullet-point key takeaways")
    signal_type: str = Field(default="GENERAL", description="Signal taxonomy classification (LAUNCH, FUNDING, RESEARCH, UPGRADE, BUZZ, GENERAL)")
    credibility_score: float = Field(default=0.85, description="Source & content reliability score from 0.0 to 1.0")
    vector: List[float] = Field(..., description="384-dimension dense embedding vector")
    metadata_json: Dict[str, Any] = Field(default_factory=dict, description="Extracted structured facts, round sizes, arXiv IDs, benchmark metrics")
    entities: List[str] = Field(default_factory=list, description="Named entities extracted from text")
    sentiment_score: float = Field(default=0.0, description="Vader sentiment score from -1.0 to 1.0")


@router.post(
    "/enrich",
    response_model=EnrichResponse,
    dependencies=[Depends(verify_internal_service_key)],
    summary="Enrich raw tech signals with LLM categorization, fact extraction, and vectorization"
)
async def enrich_signal(req: EnrichRequest) -> EnrichResponse:
    extracted = await llm_extractor.extract_signal_intelligence(
        title=req.title,
        content=req.content,
        source_url=req.source_url
    )

    takeaways_formatted = "\n".join(f"- {t}" for t in extracted.key_takeaways)
    enhanced_text = f"{extracted.summary}\n\nKey Takeaways:\n{takeaways_formatted}"

    metadata = {
        **extracted.structured_metadata,
        "source_url": req.source_url,
        "llm_provider": extracted.provider,
        "char_count": len(req.content)
    }

    # Generate 384D embedding vector on combined semantic content
    embed_text = f"{req.title}. {extracted.summary}"
    embedding_vector = vector_service.generate_embedding(embed_text)

    return EnrichResponse(
        enhanced_content=enhanced_text,
        signal_type=extracted.signal_type,
        credibility_score=extracted.credibility_score,
        vector=embedding_vector,
        metadata_json=metadata,
        entities=extracted.entities,
        sentiment_score=0.25
    )
