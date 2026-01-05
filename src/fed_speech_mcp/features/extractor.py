"""Feature extraction for Fed speeches."""

from ..models import Features, TopicFlags


class FeatureExtractor:
    """Extract deterministic features from speech text.

    Features computed:
    - Word count
    - Language (default: en)
    - Presence of Q&A section (boolean)
    - Topic mention flags
    """

    # Topic keyword groups from V1 spec
    TOPIC_KEYWORDS = {
        "inflation": [
            "inflation",
            "prices",
            "cpi",
            "pce",
            "price stability",
            "price level",
            "consumer prices",
            "core inflation",
            "headline inflation",
            "disinflation",
            "deflationary",
        ],
        "labor_market": [
            "labor market",
            "employment",
            "unemployment",
            "wages",
            "jobs",
            "workforce",
            "payrolls",
            "job gains",
            "labor force",
            "participation rate",
            "wage growth",
            "labor supply",
            "hiring",
        ],
        "rates": [
            "interest rate",
            "fed funds",
            "federal funds",
            "policy rate",
            "rate hike",
            "rate cut",
            "tighten",
            "tightening",
            "ease",
            "easing",
            "monetary policy",
            "stance",
            "restrictive",
            "accommodative",
            "rate decision",
            "benchmark rate",
        ],
        "balance_sheet": [
            "balance sheet",
            "qe",
            "qt",
            "quantitative easing",
            "quantitative tightening",
            "runoff",
            "asset purchases",
            "securities holdings",
            "treasuries",
            "mortgage-backed",
            "mbs",
            "reserves",
            "repo",
            "reverse repo",
        ],
        "growth": [
            "growth",
            "gdp",
            "demand",
            "recession",
            "economic activity",
            "expansion",
            "output",
            "productivity",
            "consumer spending",
            "investment",
            "soft landing",
            "hard landing",
            "economic outlook",
        ],
        "financial_stability": [
            "financial stability",
            "banking",
            "liquidity",
            "stress",
            "systemic risk",
            "financial system",
            "bank failure",
            "contagion",
            "credit risk",
            "market functioning",
            "financial conditions",
            "leverage",
            "capital",
            "supervision",
            "regulation",
        ],
    }

    # Q&A detection patterns
    QA_PATTERNS = [
        r"\bQ\s*&\s*A\b",
        r"\bQuestions?\s+and\s+Answers?\b",
        r"\bQ:\s+",
        r"\bQuestion:\s+",
        r"\bAudience\s+(?:Member|Question)",
        r"\bModerator:\s+",
        r"\bHost:\s+",
    ]

    def extract(self, text: str, has_qa_hint: bool = False) -> Features:
        """Extract features from speech text.

        Args:
            text: The clean speech text.
            has_qa_hint: Optional hint about Q&A presence from parser.

        Returns:
            Features object with computed values.
        """
        # Word count
        word_count = self._count_words(text)

        # Q&A detection
        has_qa = has_qa_hint or self._detect_qa(text)

        # Topic detection
        topics = self._detect_topics(text)

        return Features(
            word_count=word_count,
            language="en",  # V1 only supports English
            has_qa=has_qa,
            topics=topics,
        )

    def _count_words(self, text: str) -> int:
        """Count words in text."""
        # Split on whitespace and filter empty strings
        words = [w for w in text.split() if w.strip()]
        return len(words)

    def _detect_qa(self, text: str) -> bool:
        """Detect if text contains Q&A section."""
        import re

        text_lower = text.lower()
        for pattern in self.QA_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        # Also check for common Q&A indicators
        qa_indicators = [
            "let me take a few questions",
            "happy to take questions",
            "open it up for questions",
            "first question",
        ]
        return any(indicator in text_lower for indicator in qa_indicators)

    def _detect_topics(self, text: str) -> TopicFlags:
        """Detect topic mentions using keyword matching."""
        text_lower = text.lower()

        flags = {}
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            # Check if any keyword appears in the text
            flags[topic] = any(kw in text_lower for kw in keywords)

        return TopicFlags(**flags)

    def update_features(self, features: Features, new_text: str) -> Features:
        """Update features with new text analysis.

        Useful for re-analyzing text with updated extraction logic.

        Args:
            features: Existing features object.
            new_text: Text to analyze.

        Returns:
            Updated Features object.
        """
        new_features = self.extract(new_text, features.has_qa)
        return new_features

