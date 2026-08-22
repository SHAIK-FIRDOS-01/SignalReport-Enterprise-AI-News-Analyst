from datetime import datetime, timezone
import email.utils
from typing import List, Optional
import feedparser
from .schemas import RawSignalPayload


class RSSFeedAdapter:
    """Adapter for tech, funding, and launch RSS/Atom XML feeds."""

    def parse_feed(self, feed_content: str, source_name: str = "RSS") -> List[RawSignalPayload]:
        payloads = []
        if not feed_content:
            return payloads

        parsed = feedparser.parse(feed_content)
        for entry in parsed.entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "")
            description = getattr(entry, "description", "") or getattr(entry, "summary", "")

            # Infer signal type
            text_lower = (title + " " + description).lower()
            signal_type = "GENERAL"
            if any(k in text_lower for k in ("funding", "raised", "seed", "series a", "series b", "valuation", "invest")):
                signal_type = "FUNDING"
            elif any(k in text_lower for k in ("launch", "announcing", "unveils", "release")):
                signal_type = "LAUNCH"

            # Parse published date
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                except Exception:
                    pass
            elif hasattr(entry, "published"):
                try:
                    published_at = email.utils.parsedate_to_datetime(entry.published)
                except Exception:
                    pass

            payloads.append(
                RawSignalPayload(
                    title=title,
                    source_url=link,
                    content_raw=description,
                    stream_source="rss",
                    signal_type=signal_type,
                    published_at=published_at,
                    raw_metadata={
                        "feed_source": source_name,
                        "author": getattr(entry, "author", ""),
                    }
                )
            )

        return payloads
