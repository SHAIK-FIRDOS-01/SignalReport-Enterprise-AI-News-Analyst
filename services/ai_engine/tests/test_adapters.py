import os
import sys
from pathlib import Path
import pytest

root_dir = Path(__file__).resolve().parent.parent.parent.parent
ai_engine_dir = root_dir / "services" / "ai_engine"

for p in [str(root_dir), str(ai_engine_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from services.ai_engine.adapters.schemas import RawSignalPayload
from services.ai_engine.adapters.hn_adapter import HackerNewsAdapter
from services.ai_engine.adapters.arxiv_adapter import ArXivAdapter
from services.ai_engine.adapters.github_adapter import GitHubReleaseAdapter
from services.ai_engine.adapters.rss_adapter import RSSFeedAdapter


def test_hn_adapter_payload_parsing():
    """Verify HackerNewsAdapter parses Firebase story JSON into RawSignalPayload."""
    adapter = HackerNewsAdapter()
    sample_item = {
        "id": 40012345,
        "by": "dang",
        "title": "Show HN: SignalReport – Open Source Real-Time Tech Radar",
        "url": "https://github.com/SignalReport/SignalReport",
        "score": 450,
        "time": 1709000000,
        "type": "story",
        "descendants": 85
    }
    payload = adapter.parse_item(sample_item)
    assert isinstance(payload, RawSignalPayload)
    assert payload.stream_source == "hackernews"
    assert payload.signal_type == "BUZZ"
    assert "Show HN: SignalReport" in payload.title
    assert payload.source_url == "https://github.com/SignalReport/SignalReport"
    assert payload.raw_metadata["score"] == 450
    assert payload.raw_metadata["by"] == "dang"


def test_arxiv_adapter_xml_parsing():
    """Verify ArXivAdapter parses arXiv Atom XML into RawSignalPayload."""
    adapter = ArXivAdapter()
    sample_xml = """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>http://arxiv.org/abs/2403.99999v1</id>
            <updated>2026-03-15T12:00:00Z</updated>
            <published>2026-03-15T12:00:00Z</published>
            <title>MoE-Scale: Scaling Mixture-of-Experts for Sub-Millisecond Retrieval</title>
            <summary>We introduce MoE-Scale, a sparse architecture achieving state of the art results on MMLU.</summary>
            <author><name>Alice Researcher</name></author>
            <author><name>Bob Scientist</name></author>
            <link href="http://arxiv.org/abs/2403.99999v1" rel="alternate" type="text/html"/>
        </entry>
    </feed>
    """
    payloads = adapter.parse_feed(sample_xml)
    assert len(payloads) == 1
    p = payloads[0]
    assert isinstance(p, RawSignalPayload)
    assert p.stream_source == "arxiv"
    assert p.signal_type == "RESEARCH"
    assert "MoE-Scale" in p.title
    assert "Alice Researcher" in p.raw_metadata["authors"]
    assert p.raw_metadata["arxiv_id"] == "http://arxiv.org/abs/2403.99999v1"


def test_github_release_adapter_parsing():
    """Verify GitHubReleaseAdapter parses GitHub Releases API JSON."""
    adapter = GitHubReleaseAdapter()
    sample_release = {
        "id": 1456789,
        "tag_name": "v3.3.0",
        "name": "Llama 3.3 70B Release",
        "body": "## What's Changed\n* Added 128k context window support\n* Optimized FP8 quantization",
        "html_url": "https://github.com/meta-llama/llama3/releases/tag/v3.3.0",
        "published_at": "2026-03-10T18:30:00Z",
        "author": {"login": "meta-ai-bot"}
    }
    payload = adapter.parse_release(sample_release, repo_name="meta-llama/llama3")
    assert isinstance(payload, RawSignalPayload)
    assert payload.stream_source == "github"
    assert payload.signal_type == "UPGRADE"
    assert payload.raw_metadata["tag_name"] == "v3.3.0"
    assert payload.raw_metadata["repo"] == "meta-llama/llama3"
    assert "128k context" in payload.content_raw


def test_rss_feed_adapter_parsing():
    """Verify RSSFeedAdapter parses TechCrunch/VentureBeat RSS feeds into RawSignalPayload."""
    adapter = RSSFeedAdapter()
    sample_rss = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>TechCrunch Funding News</title>
            <item>
                <title>AI Infrastructure Startup Raises $50M Series B</title>
                <link>https://techcrunch.com/2026/03/ai-startup-funding</link>
                <description><![CDATA[The round was led by Andreessen Horowitz with participation from Founders Fund.]]></description>
                <pubDate>Mon, 16 Mar 2026 14:00:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    payloads = adapter.parse_feed(sample_rss, source_name="TechCrunch")
    assert len(payloads) == 1
    p = payloads[0]
    assert isinstance(p, RawSignalPayload)
    assert p.stream_source == "rss"
    assert p.signal_type in ("FUNDING", "LAUNCH")
    assert "Raises $50M" in p.title
    assert "Andreessen Horowitz" in p.content_raw
