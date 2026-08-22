import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List
from .schemas import RawSignalPayload

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArXivAdapter:
    """Adapter for arXiv Atom XML feeds."""

    def parse_feed(self, xml_content: str) -> List[RawSignalPayload]:
        payloads = []
        if not xml_content:
            return payloads

        root = ET.fromstring(xml_content)
        entries = root.findall("atom:entry", ATOM_NS)

        for entry in entries:
            id_elem = entry.find("atom:id", ATOM_NS)
            title_elem = entry.find("atom:title", ATOM_NS)
            summary_elem = entry.find("atom:summary", ATOM_NS)
            published_elem = entry.find("atom:published", ATOM_NS)

            arxiv_id = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
            title = " ".join(title_elem.text.split()) if title_elem is not None and title_elem.text else ""
            summary = " ".join(summary_elem.text.split()) if summary_elem is not None and summary_elem.text else ""

            # Extract link
            link_elem = entry.find("atom:link[@rel='alternate']", ATOM_NS)
            url = link_elem.attrib.get("href", arxiv_id) if link_elem is not None else arxiv_id

            # Extract authors
            authors = []
            for author_elem in entry.findall("atom:author", ATOM_NS):
                name_elem = author_elem.find("atom:name", ATOM_NS)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text.strip())

            # Parse timestamp
            published_at = None
            if published_elem is not None and published_elem.text:
                try:
                    published_at = datetime.fromisoformat(published_elem.text.replace("Z", "+00:00"))
                except Exception:
                    pass

            payloads.append(
                RawSignalPayload(
                    title=title,
                    source_url=url,
                    content_raw=summary,
                    stream_source="arxiv",
                    signal_type="RESEARCH",
                    published_at=published_at,
                    raw_metadata={
                        "arxiv_id": arxiv_id,
                        "authors": authors,
                    }
                )
            )

        return payloads
