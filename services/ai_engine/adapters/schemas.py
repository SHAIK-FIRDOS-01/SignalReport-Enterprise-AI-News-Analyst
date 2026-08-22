from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class RawSignalPayload(BaseModel):
    """
    Standardized payload format generated across all multi-stream ingestion adapters.
    """
    title: str = Field(..., description="Signal title or release name")
    source_url: str = Field(..., description="Canonical source URL")
    content_raw: str = Field(default="", description="Original raw snippet or body markdown")
    stream_source: str = Field(..., description="Originating stream ('hackernews', 'arxiv', 'github', 'rss')")
    signal_type: str = Field(default="GENERAL", description="Initial classification ('LAUNCH', 'FUNDING', 'RESEARCH', 'UPGRADE', 'BUZZ')")
    published_at: Optional[datetime] = Field(default=None, description="Publication timestamp")
    raw_metadata: Dict[str, Any] = Field(default_factory=dict, description="Stream-specific metadata (score, authors, repo, tag)")
