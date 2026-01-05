"""Content fetcher for Fed speech pages."""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx


@dataclass
class FetchedContent:
    """Fetched content from a URL."""

    url: str
    content: str
    content_type: str
    fetched_at: datetime
    status_code: int
    content_hash: str


class FedFetcher:
    """Fetcher for Federal Reserve speech content."""

    def __init__(
        self,
        http_client: Optional[httpx.AsyncClient] = None,
        raw_storage_path: Optional[Path] = None,
        max_retries: int = 3,
    ):
        """Initialize the fetcher.

        Args:
            http_client: Optional async HTTP client.
            raw_storage_path: Optional path to store raw content.
            max_retries: Maximum number of retry attempts.
        """
        self._client = http_client
        self._raw_storage_path = raw_storage_path
        self._max_retries = max_retries

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create an HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "FedSpeechMCP/1.0 (Research; Academic)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf;q=0.8,*/*;q=0.7",
                },
                follow_redirects=True,
            )
        return self._client

    async def fetch(self, url: str) -> FetchedContent:
        """Fetch content from a URL with retry logic.

        Args:
            url: The URL to fetch.

        Returns:
            FetchedContent with the page content.

        Raises:
            RuntimeError: If fetching fails after all retries.
        """
        client = await self._get_client()
        last_error = None

        for attempt in range(self._max_retries):
            try:
                response = await client.get(url)
                response.raise_for_status()

                content = response.text
                content_type = response.headers.get("content-type", "text/html")
                fetched_at = datetime.utcnow()
                content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

                fetched = FetchedContent(
                    url=url,
                    content=content,
                    content_type=content_type,
                    fetched_at=fetched_at,
                    status_code=response.status_code,
                    content_hash=content_hash,
                )

                # Optionally save raw content
                if self._raw_storage_path:
                    await self._save_raw(fetched)

                return fetched

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code in (404, 410):
                    # Don't retry for not found or gone
                    raise RuntimeError(f"Document not found: {url}") from e
            except httpx.TimeoutException as e:
                last_error = e
                # Exponential backoff
                import asyncio
                await asyncio.sleep(2 ** attempt)
            except httpx.HTTPError as e:
                last_error = e
                import asyncio
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError(
            f"Failed to fetch {url} after {self._max_retries} attempts: {last_error}"
        )

    async def fetch_batch(
        self, urls: list[str], continue_on_error: bool = True
    ) -> dict[str, FetchedContent | Exception]:
        """Fetch multiple URLs.

        Args:
            urls: List of URLs to fetch.
            continue_on_error: Whether to continue if a fetch fails.

        Returns:
            Dictionary mapping URLs to FetchedContent or exceptions.
        """
        results = {}

        for url in urls:
            try:
                results[url] = await self.fetch(url)
            except Exception as e:
                if continue_on_error:
                    results[url] = e
                else:
                    raise

        return results

    async def _save_raw(self, content: FetchedContent) -> None:
        """Save raw content for traceability.

        Args:
            content: The fetched content to save.
        """
        if not self._raw_storage_path:
            return

        self._raw_storage_path.mkdir(parents=True, exist_ok=True)

        # Create filename from URL hash and timestamp
        url_hash = hashlib.sha256(content.url.encode()).hexdigest()[:12]
        timestamp = content.fetched_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{url_hash}.html"

        filepath = self._raw_storage_path / filename

        # Save content with metadata header
        header = f"<!-- URL: {content.url}\n     Fetched: {content.fetched_at.isoformat()}\n     Hash: {content.content_hash}\n-->\n"
        full_content = header + content.content

        filepath.write_text(full_content, encoding="utf-8")

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

