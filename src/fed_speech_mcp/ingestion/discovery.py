"""Discovery mechanisms for Fed speeches via RSS feeds and index pages."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import feedparser
import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


@dataclass
class DiscoveredDocument:
    """A discovered document from RSS or index page."""

    url: str
    title: str
    published_at: Optional[datetime]
    doc_type: str  # "speech" or "testimony"
    speaker_name: Optional[str] = None


class FedDiscovery:
    """Discovery service for Federal Reserve speeches and testimonies."""

    # Official Fed RSS feeds
    RSS_FEEDS = {
        "speeches": "https://www.federalreserve.gov/feeds/speeches.xml",
        "testimony": "https://www.federalreserve.gov/feeds/testimony.xml",
    }

    # Index page URLs (for backfill)
    INDEX_URLS = {
        "speeches": "https://www.federalreserve.gov/newsevents/speeches.htm",
        "testimony": "https://www.federalreserve.gov/newsevents/testimony.htm",
    }

    BASE_URL = "https://www.federalreserve.gov"

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        """Initialize the discovery service.

        Args:
            http_client: Optional async HTTP client for making requests.
        """
        self._client = http_client
        self._seen_urls: set[str] = set()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create an HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "FedSpeechMCP/1.0 (Research; Academic)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
                follow_redirects=True,
            )
        return self._client

    async def discover_from_rss(
        self, doc_type: str = "speeches"
    ) -> list[DiscoveredDocument]:
        """Discover documents from RSS feed.

        Args:
            doc_type: Type of documents to discover ("speeches" or "testimony").

        Returns:
            List of discovered documents.
        """
        if doc_type not in self.RSS_FEEDS:
            raise ValueError(f"Unknown doc_type: {doc_type}")

        client = await self._get_client()
        feed_url = self.RSS_FEEDS[doc_type]

        try:
            response = await client.get(feed_url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Failed to fetch RSS feed: {e}") from e

        feed = feedparser.parse(response.text)
        documents = []

        for entry in feed.entries:
            url = entry.get("link", "")
            if not url or url in self._seen_urls:
                continue

            # Parse publication date
            published_at = None
            if "published_parsed" in entry and entry.published_parsed:
                published_at = datetime(*entry.published_parsed[:6])
            elif "updated_parsed" in entry and entry.updated_parsed:
                published_at = datetime(*entry.updated_parsed[:6])

            # Extract speaker name from title if present
            title = entry.get("title", "")
            speaker_name = self._extract_speaker_from_title(title)

            doc = DiscoveredDocument(
                url=url,
                title=title,
                published_at=published_at,
                doc_type="testimony" if doc_type == "testimony" else "speech",
                speaker_name=speaker_name,
            )
            documents.append(doc)
            self._seen_urls.add(url)

        return documents

    async def discover_from_index(
        self, doc_type: str = "speeches", year: Optional[int] = None
    ) -> list[DiscoveredDocument]:
        """Discover documents from index pages.

        Args:
            doc_type: Type of documents to discover ("speeches" or "testimony").
            year: Optional year to filter by.

        Returns:
            List of discovered documents.
        """
        if doc_type not in self.INDEX_URLS:
            raise ValueError(f"Unknown doc_type: {doc_type}")

        client = await self._get_client()
        index_url = self.INDEX_URLS[doc_type]

        # Add year filter if specified
        if year:
            index_url = f"{index_url}?year={year}"

        try:
            response = await client.get(index_url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Failed to fetch index page: {e}") from e

        soup = BeautifulSoup(response.text, "lxml")
        documents = []

        # Find speech/testimony entries in the index
        # The Fed website uses a specific structure for listing items
        entries = soup.select(".row.eventlist .col-xs-12, .row.eventlist .itemTitle")

        if not entries:
            # Alternative selector for different page layouts
            entries = soup.select("div.row div.col-md-9, div.eventlist__event")

        for entry in entries:
            link = entry.find("a")
            if not link:
                continue

            href = link.get("href", "")
            if not href:
                continue

            # Make URL absolute
            url = urljoin(self.BASE_URL, href)

            # Skip if already seen or not a speech/testimony page
            if url in self._seen_urls:
                continue
            if "/speech/" not in url and "/testimony/" not in url:
                continue

            title = link.get_text(strip=True)

            # Try to extract date
            date_elem = entry.find(class_="eventlist__date") or entry.find("time")
            published_at = None
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                try:
                    published_at = date_parser.parse(date_text)
                except (ValueError, TypeError):
                    pass

            speaker_name = self._extract_speaker_from_title(title)

            doc = DiscoveredDocument(
                url=url,
                title=title,
                published_at=published_at,
                doc_type="testimony" if "testimony" in url else "speech",
                speaker_name=speaker_name,
            )
            documents.append(doc)
            self._seen_urls.add(url)

        return documents

    async def discover_all(
        self, include_index: bool = False, years: Optional[list[int]] = None
    ) -> list[DiscoveredDocument]:
        """Discover all documents from RSS feeds and optionally index pages.

        Args:
            include_index: Whether to also scan index pages.
            years: Optional list of years to scan for index pages.

        Returns:
            Combined list of discovered documents.
        """
        all_docs = []

        # Discover from RSS feeds first (preferred)
        for doc_type in ["speeches", "testimony"]:
            try:
                docs = await self.discover_from_rss(doc_type)
                all_docs.extend(docs)
            except Exception as e:
                # Log but continue with other sources
                print(f"Warning: Failed to discover from {doc_type} RSS: {e}")

        # Optionally scan index pages for backfill
        if include_index:
            scan_years = years or [datetime.now().year]
            for doc_type in ["speeches", "testimony"]:
                for year in scan_years:
                    try:
                        docs = await self.discover_from_index(doc_type, year)
                        all_docs.extend(docs)
                    except Exception as e:
                        print(f"Warning: Failed to discover from {doc_type} index for {year}: {e}")

        return all_docs

    def _extract_speaker_from_title(self, title: str) -> Optional[str]:
        """Try to extract speaker name from title.

        Fed titles often follow patterns like:
        - "Speech by Governor X..."
        - "Testimony by Chair Y..."
        - "Chair Powell's Speech..."
        """
        # Common patterns
        patterns = [
            r"(?:Speech|Testimony|Remarks)\s+by\s+(?:Governor|Chair|Vice Chair)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"(?:Governor|Chair|Vice Chair)\s+([A-Z][a-z]+)'s",
            r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s+(?:Governor|Chair|Vice Chair)",
        ]

        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1)

        return None

    def clear_seen(self) -> None:
        """Clear the set of seen URLs for fresh discovery."""
        self._seen_urls.clear()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

