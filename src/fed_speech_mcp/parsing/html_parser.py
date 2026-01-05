"""HTML parser for Federal Reserve speech pages."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup, NavigableString
from dateutil import parser as date_parser


@dataclass
class ParsedContent:
    """Parsed content from a Fed speech page."""

    title: str
    raw_text: str
    clean_text: str
    published_at: Optional[datetime] = None
    speaker_name: Optional[str] = None
    speaker_role: Optional[str] = None
    event_name: Optional[str] = None
    event_location: Optional[str] = None
    doc_type: str = "speech"
    has_qa: bool = False
    paragraphs: list[str] = field(default_factory=list)


class FedHTMLParser:
    """Parser for Federal Reserve speech HTML pages."""

    # Role keywords for detection
    ROLE_PATTERNS = {
        "Chair": [
            r"\bChair(?:man|woman)?\b(?!\s*(?:Vice|of the))",
            r"\bChair of the Federal Reserve\b",
        ],
        "Vice Chair": [
            r"\bVice Chair(?:man|woman)?\b",
            r"\bVice Chairman\b",
            r"\bVice Chairwoman\b",
        ],
        "Governor": [
            r"\bGovernor\b",
            r"\bFederal Reserve Governor\b",
        ],
    }

    # Boilerplate patterns to remove
    BOILERPLATE_PATTERNS = [
        r"^\s*Home\s*$",
        r"^\s*News & Events\s*$",
        r"^\s*Speeches\s*$",
        r"^\s*Testimony\s*$",
        r"^\s*Share\s*$",
        r"^\s*Print\s*$",
        r"^\s*Subscribe\s*$",
        r"^\s*RSS\s*$",
        r"^\s*Last Update:\s*",
        r"^\s*Accessibility\s*$",
        r"^\s*Contact\s*Us\s*$",
        r"^\s*\d+\s*$",  # Page numbers
    ]

    def parse(self, html_content: str, url: str = "") -> ParsedContent:
        """Parse a Fed speech HTML page.

        Args:
            html_content: The HTML content to parse.
            url: Original URL for context.

        Returns:
            ParsedContent with extracted information.
        """
        soup = BeautifulSoup(html_content, "lxml")

        # Extract metadata
        title = self._extract_title(soup)
        published_at = self._extract_date(soup)
        speaker_name, speaker_role = self._extract_speaker(soup, title)
        event_name, event_location = self._extract_event(soup)
        doc_type = self._detect_doc_type(soup, url, title)

        # Extract text content
        raw_text, paragraphs = self._extract_text(soup)
        clean_text = self._clean_text(raw_text)

        # Detect Q&A section
        has_qa = self._detect_qa(raw_text)

        return ParsedContent(
            title=title,
            raw_text=raw_text,
            clean_text=clean_text,
            published_at=published_at,
            speaker_name=speaker_name,
            speaker_role=speaker_role,
            event_name=event_name,
            event_location=event_location,
            doc_type=doc_type,
            has_qa=has_qa,
            paragraphs=paragraphs,
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the title from the page."""
        # Try specific Fed page structure first
        title_elem = soup.select_one("h3.title, .title h3, h1.title")
        if title_elem:
            return title_elem.get_text(strip=True)

        # Try article title
        title_elem = soup.select_one("article h1, .article-title, .speech-title")
        if title_elem:
            return title_elem.get_text(strip=True)

        # Fall back to page title
        title_elem = soup.find("title")
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            # Remove common suffixes
            title_text = re.sub(
                r"\s*[-|]\s*(?:Federal Reserve|Board of Governors).*$",
                "",
                title_text,
            )
            return title_text

        # Try first h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        return "Untitled Speech"

    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract the publication date."""
        # Try specific date elements
        date_selectors = [
            ".article__time time",
            ".eventlist__time time",
            "time[datetime]",
            ".date",
            ".speech-date",
            ".article-date",
        ]

        for selector in date_selectors:
            elem = soup.select_one(selector)
            if elem:
                # Try datetime attribute first
                if elem.has_attr("datetime"):
                    try:
                        return date_parser.parse(elem["datetime"])
                    except (ValueError, TypeError):
                        pass

                # Try text content
                date_text = elem.get_text(strip=True)
                try:
                    return date_parser.parse(date_text)
                except (ValueError, TypeError):
                    pass

        # Try to find date in meta tags
        meta_date = soup.find("meta", {"name": "date"}) or soup.find(
            "meta", {"property": "article:published_time"}
        )
        if meta_date and meta_date.get("content"):
            try:
                return date_parser.parse(meta_date["content"])
            except (ValueError, TypeError):
                pass

        return None

    def _extract_speaker(
        self, soup: BeautifulSoup, title: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Extract speaker name and role."""
        speaker_name = None
        speaker_role = None

        # Try specific speaker element
        speaker_elem = soup.select_one(".speaker, .article__speaker, .speech-speaker")
        if speaker_elem:
            speaker_text = speaker_elem.get_text(strip=True)
            speaker_name, speaker_role = self._parse_speaker_text(speaker_text)
            if speaker_name:
                return speaker_name, speaker_role

        # Try to extract from title or subtitle
        subtitle = soup.select_one(".subtitle, h4.speaker")
        if subtitle:
            speaker_text = subtitle.get_text(strip=True)
            speaker_name, speaker_role = self._parse_speaker_text(speaker_text)
            if speaker_name:
                return speaker_name, speaker_role

        # Try to extract from title itself
        speaker_name, speaker_role = self._parse_speaker_text(title)

        return speaker_name, speaker_role

    def _parse_speaker_text(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """Parse speaker name and role from text."""
        speaker_role = None

        # Detect role
        for role, patterns in self.ROLE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    speaker_role = role
                    break
            if speaker_role:
                break

        # Extract name patterns
        name_patterns = [
            # "Governor Michelle W. Bowman"
            r"(?:Chair(?:man|woman)?|Vice Chair(?:man|woman)?|Governor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)",
            # "Jerome H. Powell, Chair"
            r"([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+),?\s+(?:Chair|Vice Chair|Governor)",
            # "Chair Powell"
            r"(?:Chair|Vice Chair|Governor)\s+([A-Z][a-z]+)",
        ]

        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1), speaker_role

        return None, speaker_role

    def _extract_event(
        self, soup: BeautifulSoup
    ) -> tuple[Optional[str], Optional[str]]:
        """Extract event name and location."""
        event_name = None
        event_location = None

        # Try event-specific elements
        event_elem = soup.select_one(".event, .speech-event, .article__event")
        if event_elem:
            event_name = event_elem.get_text(strip=True)

        location_elem = soup.select_one(".location, .speech-location, .article__location")
        if location_elem:
            event_location = location_elem.get_text(strip=True)

        # Try to find in "at the" patterns in subtitle or intro
        intro_text = ""
        for selector in [".subtitle", ".intro", ".speech-intro"]:
            elem = soup.select_one(selector)
            if elem:
                intro_text = elem.get_text()
                break

        if intro_text and not event_name:
            # "at the Economic Club of New York"
            match = re.search(r"at\s+(?:the\s+)?(.+?)(?:,|\.|$)", intro_text)
            if match:
                event_name = match.group(1).strip()

        if intro_text and not event_location:
            # "New York, New York" or "Washington, D.C."
            match = re.search(
                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?,\s+(?:[A-Z][a-z]+|[A-Z]{2}|D\.?C\.?))",
                intro_text,
            )
            if match:
                event_location = match.group(1).strip()

        return event_name, event_location

    def _detect_doc_type(
        self, soup: BeautifulSoup, url: str, title: str
    ) -> str:
        """Detect the document type."""
        # Check URL
        if "/testimony/" in url:
            return "testimony"

        # Check title
        title_lower = title.lower()
        if "testimony" in title_lower:
            return "testimony"
        if "prepared remarks" in title_lower:
            return "prepared_remarks"

        # Check page content
        page_text = soup.get_text().lower()
        if "testimony before" in page_text[:1000]:
            return "testimony"

        return "speech"

    def _extract_text(self, soup: BeautifulSoup) -> tuple[str, list[str]]:
        """Extract raw text and paragraphs from the speech content."""
        # Find the main content area
        content_selectors = [
            "article .col-md-8",
            ".article-content",
            ".speech-content",
            "article .content",
            "#article",
            "article",
            "main",
        ]

        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                break

        if not content_area:
            content_area = soup.body or soup

        # Remove unwanted elements
        for selector in ["nav", "header", "footer", ".breadcrumb", ".share", ".subscribe"]:
            for elem in content_area.select(selector):
                elem.decompose()

        # Extract paragraphs
        paragraphs = []
        for p in content_area.find_all(["p", "blockquote"]):
            text = p.get_text(strip=True)
            if text and not self._is_boilerplate(text):
                paragraphs.append(text)

        # Build raw text preserving structure
        raw_parts = []
        for elem in content_area.descendants:
            if isinstance(elem, NavigableString):
                text = str(elem).strip()
                if text and not self._is_boilerplate(text):
                    raw_parts.append(text)
            elif elem.name in ["br", "p", "div", "h1", "h2", "h3", "h4", "h5", "h6"]:
                raw_parts.append("\n")

        raw_text = " ".join(raw_parts)
        raw_text = re.sub(r"\s+", " ", raw_text).strip()
        raw_text = re.sub(r"\n\s*\n+", "\n\n", raw_text)

        return raw_text, paragraphs

    def _clean_text(self, raw_text: str) -> str:
        """Clean raw text by removing remaining boilerplate."""
        lines = raw_text.split("\n")
        clean_lines = []

        for line in lines:
            line = line.strip()
            if line and not self._is_boilerplate(line):
                clean_lines.append(line)

        clean_text = "\n".join(clean_lines)

        # Remove excessive whitespace
        clean_text = re.sub(r" +", " ", clean_text)
        clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)

        return clean_text.strip()

    def _is_boilerplate(self, text: str) -> bool:
        """Check if text is boilerplate content."""
        for pattern in self.BOILERPLATE_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        return len(text) < 3

    def _detect_qa(self, text: str) -> bool:
        """Detect if the speech contains a Q&A section."""
        qa_patterns = [
            r"\bQ\s*&\s*A\b",
            r"\bQuestions?\s+and\s+Answers?\b",
            r"\bQ:\s+",
            r"\bQuestion:\s+",
            r"\bAudience\s+(?:Member|Question)",
        ]

        for pattern in qa_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

