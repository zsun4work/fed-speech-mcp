"""Normalizer for speech data to controlled vocabulary."""

import hashlib
import re
from datetime import datetime
from typing import Optional

from ..models import (
    DocType,
    Event,
    Features,
    Importance,
    ImportanceTier,
    Source,
    Speaker,
    SpeakerRole,
    Speech,
    TextContent,
    TopicFlags,
)
from .html_parser import ParsedContent


class SpeechNormalizer:
    """Normalizer for converting parsed content to structured Speech objects."""

    # Known Fed officials mapping (for name resolution)
    KNOWN_OFFICIALS = {
        "Powell": ("Jerome H. Powell", SpeakerRole.CHAIR),
        "Jerome Powell": ("Jerome H. Powell", SpeakerRole.CHAIR),
        "Jerome H. Powell": ("Jerome H. Powell", SpeakerRole.CHAIR),
        "Jefferson": ("Philip N. Jefferson", SpeakerRole.VICE_CHAIR),
        "Philip Jefferson": ("Philip N. Jefferson", SpeakerRole.VICE_CHAIR),
        "Philip N. Jefferson": ("Philip N. Jefferson", SpeakerRole.VICE_CHAIR),
        "Barr": ("Michael S. Barr", SpeakerRole.VICE_CHAIR),
        "Michael Barr": ("Michael S. Barr", SpeakerRole.VICE_CHAIR),
        "Michael S. Barr": ("Michael S. Barr", SpeakerRole.VICE_CHAIR),
        "Bowman": ("Michelle W. Bowman", SpeakerRole.GOVERNOR),
        "Michelle Bowman": ("Michelle W. Bowman", SpeakerRole.GOVERNOR),
        "Michelle W. Bowman": ("Michelle W. Bowman", SpeakerRole.GOVERNOR),
        "Waller": ("Christopher J. Waller", SpeakerRole.GOVERNOR),
        "Christopher Waller": ("Christopher J. Waller", SpeakerRole.GOVERNOR),
        "Christopher J. Waller": ("Christopher J. Waller", SpeakerRole.GOVERNOR),
        "Cook": ("Lisa D. Cook", SpeakerRole.GOVERNOR),
        "Lisa Cook": ("Lisa D. Cook", SpeakerRole.GOVERNOR),
        "Lisa D. Cook": ("Lisa D. Cook", SpeakerRole.GOVERNOR),
        "Kugler": ("Adriana D. Kugler", SpeakerRole.GOVERNOR),
        "Adriana Kugler": ("Adriana D. Kugler", SpeakerRole.GOVERNOR),
        "Adriana D. Kugler": ("Adriana D. Kugler", SpeakerRole.GOVERNOR),
    }

    # Role string to enum mapping
    ROLE_MAPPING = {
        "chair": SpeakerRole.CHAIR,
        "chairman": SpeakerRole.CHAIR,
        "chairwoman": SpeakerRole.CHAIR,
        "vice chair": SpeakerRole.VICE_CHAIR,
        "vice chairman": SpeakerRole.VICE_CHAIR,
        "vice chairwoman": SpeakerRole.VICE_CHAIR,
        "governor": SpeakerRole.GOVERNOR,
    }

    # Doc type mapping
    DOC_TYPE_MAPPING = {
        "speech": DocType.SPEECH,
        "testimony": DocType.TESTIMONY,
        "prepared_remarks": DocType.PREPARED_REMARKS,
    }

    def normalize(
        self,
        parsed: ParsedContent,
        url: str,
        retrieved_at: datetime,
    ) -> Speech:
        """Normalize parsed content into a Speech object.

        Args:
            parsed: The parsed content from HTML.
            url: The source URL.
            retrieved_at: When the content was retrieved.

        Returns:
            A normalized Speech object.
        """
        # Generate document ID
        doc_id = self._generate_doc_id(url, parsed.title, parsed.published_at)

        # Normalize speaker
        speaker = self._normalize_speaker(parsed.speaker_name, parsed.speaker_role)

        # Normalize doc type
        doc_type = self._normalize_doc_type(parsed.doc_type)

        # Create source info
        collection = "testimony" if doc_type == DocType.TESTIMONY else "speeches"
        source = Source(
            publisher="Board of Governors of the Federal Reserve System",
            collection=collection,
            url=url,
            retrieved_at=retrieved_at,
        )

        # Create event info
        event = Event(
            name=parsed.event_name,
            location=parsed.event_location,
        )

        # Create text content
        text = TextContent(
            raw=parsed.raw_text,
            clean=parsed.clean_text,
        )

        # Extract features
        features = self._extract_features(parsed)

        # Calculate importance
        importance = self._calculate_importance(speaker, doc_type, features)

        # Use current time if published_at is not available
        published_at = parsed.published_at or retrieved_at

        return Speech(
            doc_id=doc_id,
            source=source,
            published_at=published_at,
            title=parsed.title,
            speaker=speaker,
            doc_type=doc_type,
            event=event,
            text=text,
            features=features,
            importance=importance,
        )

    def _generate_doc_id(
        self,
        url: str,
        title: str,
        published_at: Optional[datetime],
    ) -> str:
        """Generate a unique document ID.

        Uses a hash of URL + normalized title + date for deduplication.
        """
        normalized_title = re.sub(r"\W+", "", title.lower())
        date_str = published_at.strftime("%Y%m%d") if published_at else "unknown"

        content = f"{url}|{normalized_title}|{date_str}"
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:12]

        return f"fed-speech-{hash_value}"

    def _normalize_speaker(
        self,
        name: Optional[str],
        role: Optional[str],
    ) -> Speaker:
        """Normalize speaker information."""
        # Try to resolve from known officials
        if name:
            for key, (full_name, known_role) in self.KNOWN_OFFICIALS.items():
                if key.lower() in name.lower():
                    return Speaker(name=full_name, role=known_role)

        # Normalize role string
        speaker_role = SpeakerRole.GOVERNOR  # Default
        if role:
            role_lower = role.lower().strip()
            for role_key, role_enum in self.ROLE_MAPPING.items():
                if role_key in role_lower:
                    speaker_role = role_enum
                    break

        # Use provided name or unknown
        speaker_name = name or "Unknown Speaker"

        return Speaker(name=speaker_name, role=speaker_role)

    def _normalize_doc_type(self, doc_type: str) -> DocType:
        """Normalize document type to enum."""
        doc_type_lower = doc_type.lower().strip()
        return self.DOC_TYPE_MAPPING.get(doc_type_lower, DocType.SPEECH)

    def _extract_features(self, parsed: ParsedContent) -> Features:
        """Extract features from parsed content."""
        clean_text = parsed.clean_text

        # Word count
        word_count = len(clean_text.split())

        # Topic detection
        topics = self._detect_topics(clean_text)

        return Features(
            word_count=word_count,
            language="en",
            has_qa=parsed.has_qa,
            topics=topics,
        )

    def _detect_topics(self, text: str) -> TopicFlags:
        """Detect topic mentions in text."""
        text_lower = text.lower()

        # Topic keyword groups from spec
        topic_keywords = {
            "inflation": ["inflation", "prices", "cpi", "pce", "price stability"],
            "labor_market": [
                "labor market",
                "employment",
                "unemployment",
                "wages",
                "jobs",
                "workforce",
            ],
            "rates": [
                "rate",
                "fed funds",
                "federal funds",
                "hike",
                "cut",
                "tighten",
                "ease",
                "monetary policy",
            ],
            "balance_sheet": [
                "balance sheet",
                "qe",
                "qt",
                "quantitative easing",
                "quantitative tightening",
                "runoff",
                "assets",
            ],
            "growth": [
                "growth",
                "gdp",
                "demand",
                "recession",
                "economic activity",
                "expansion",
            ],
            "financial_stability": [
                "financial stability",
                "banking",
                "liquidity",
                "stress",
                "systemic risk",
                "financial system",
            ],
        }

        flags = {}
        for topic, keywords in topic_keywords.items():
            flags[topic] = any(kw in text_lower for kw in keywords)

        return TopicFlags(**flags)

    def _calculate_importance(
        self,
        speaker: Speaker,
        doc_type: DocType,
        features: Features,
    ) -> Importance:
        """Calculate rule-based importance score.

        Rules from spec:
        - Base tier by role: Chair/Vice Chair = high, Governor = medium
        - Testimony: +1 tier
        - Has Q&A: +1 tier
        - Mentions rates AND (inflation OR labor market): +1 tier
        - Word count < 300: -1 tier
        """
        reasons = []

        # Base tier by role
        if speaker.role in (SpeakerRole.CHAIR, SpeakerRole.VICE_CHAIR):
            tier_value = 2  # high
            reasons.append(f"Speaker is {speaker.role.value}")
        else:
            tier_value = 1  # medium
            reasons.append(f"Speaker is {speaker.role.value}")

        # Testimony adjustment
        if doc_type == DocType.TESTIMONY:
            tier_value += 1
            reasons.append("Document is testimony")

        # Q&A adjustment
        if features.has_qa:
            tier_value += 1
            reasons.append("Contains Q&A section")

        # Topic-based adjustment
        topics = features.topics
        if topics.rates and (topics.inflation or topics.labor_market):
            tier_value += 1
            reasons.append("Discusses rates with inflation or labor market context")

        # Low word count adjustment
        if features.word_count < 300:
            tier_value -= 1
            reasons.append("Short document (< 300 words)")

        # Clamp tier value and map to enum
        tier_value = max(0, min(3, tier_value))
        tier_mapping = {
            0: ImportanceTier.LOW,
            1: ImportanceTier.LOW,
            2: ImportanceTier.MEDIUM,
            3: ImportanceTier.HIGH,
        }
        tier = tier_mapping.get(tier_value, ImportanceTier.MEDIUM)

        # Normalize score (0-1)
        score = min(1.0, max(0.0, tier_value / 3.0))

        return Importance(
            tier=tier,
            score=round(score, 2),
            reasons=reasons,
        )

