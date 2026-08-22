from datetime import datetime, timezone
from typing import Dict, Any, Optional
from .schemas import RawSignalPayload


class HackerNewsAdapter:
    """Adapter for HackerNews Firebase API item objects."""

    def parse_item(self, item: Dict[str, Any]) -> Optional[RawSignalPayload]:
        if not item or item.get("type") != "story":
            return None

        title = item.get("title", "").strip()
        item_id = item.get("id")
        url = item.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
        time_sec = item.get("time")
        published_at = datetime.fromtimestamp(time_sec, tz=timezone.utc) if time_sec else None

        signal_type = "BUZZ"

        return RawSignalPayload(
            title=title,
            source_url=url,
            content_raw=item.get("text", "") or title,
            stream_source="hackernews",
            signal_type=signal_type,
            published_at=published_at,
            raw_metadata={
                "hn_id": item_id,
                "score": item.get("score", 0),
                "by": item.get("by", ""),
                "descendants": item.get("descendants", 0),
            }
        )
