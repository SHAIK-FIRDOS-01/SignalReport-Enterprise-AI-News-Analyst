from datetime import datetime
from typing import Dict, Any, Optional
from .schemas import RawSignalPayload


class GitHubReleaseAdapter:
    """Adapter for GitHub Releases REST API."""

    def parse_release(self, release: Dict[str, Any], repo_name: str) -> Optional[RawSignalPayload]:
        if not release:
            return None

        tag_name = release.get("tag_name", "")
        name = release.get("name") or tag_name
        title = f"[{repo_name}] {name}"
        html_url = release.get("html_url") or f"https://github.com/{repo_name}/releases/tag/{tag_name}"
        body = release.get("body", "") or f"Release {tag_name} for repository {repo_name}"
        
        published_at = None
        if release.get("published_at"):
            try:
                published_at = datetime.fromisoformat(release["published_at"].replace("Z", "+00:00"))
            except Exception:
                pass

        return RawSignalPayload(
            title=title,
            source_url=html_url,
            content_raw=body,
            stream_source="github",
            signal_type="UPGRADE",
            published_at=published_at,
            raw_metadata={
                "tag_name": tag_name,
                "repo": repo_name,
                "release_id": release.get("id"),
                "author": release.get("author", {}).get("login", ""),
            }
        )
