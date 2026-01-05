"""Tests for feature extraction and scoring."""

import pytest

from fed_speech_mcp.features import FeatureExtractor, ImportanceScorer
from fed_speech_mcp.models import (
    DocType,
    Features,
    ImportanceTier,
    Speaker,
    SpeakerRole,
    TopicFlags,
)


class TestFeatureExtractor:
    """Tests for FeatureExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create a FeatureExtractor."""
        return FeatureExtractor()

    def test_word_count(self, extractor):
        """Test word count extraction."""
        text = "This is a simple test sentence with ten words total."
        features = extractor.extract(text)
        assert features.word_count == 10

    def test_topic_detection_inflation(self, extractor):
        """Test inflation topic detection."""
        text = "The inflation rate continues to be elevated. PCE remains above target."
        features = extractor.extract(text)
        assert features.topics.inflation is True

    def test_topic_detection_rates(self, extractor):
        """Test rates topic detection."""
        text = "The federal funds rate will remain elevated. Monetary policy is restrictive."
        features = extractor.extract(text)
        assert features.topics.rates is True

    def test_topic_detection_labor(self, extractor):
        """Test labor market topic detection."""
        text = "The labor market remains tight. Unemployment is low and wages are rising."
        features = extractor.extract(text)
        assert features.topics.labor_market is True

    def test_topic_detection_multiple(self, extractor):
        """Test detecting multiple topics."""
        text = """
        Inflation remains above our 2% target while the labor market 
        continues to show strength. We will maintain restrictive monetary policy
        and keep interest rates elevated.
        """
        features = extractor.extract(text)
        assert features.topics.inflation is True
        assert features.topics.labor_market is True
        assert features.topics.rates is True

    def test_qa_detection(self, extractor):
        """Test Q&A section detection."""
        text = "Thank you for the speech. Now let's open it up for Q&A. Q: What about rates?"
        features = extractor.extract(text)
        assert features.has_qa is True

    def test_no_qa_detection(self, extractor):
        """Test no Q&A detection when not present."""
        text = "This is a prepared speech without any questions."
        features = extractor.extract(text)
        assert features.has_qa is False

    def test_language_default(self, extractor):
        """Test default language is English."""
        features = extractor.extract("Any text")
        assert features.language == "en"


class TestImportanceScorer:
    """Tests for ImportanceScorer."""

    @pytest.fixture
    def scorer(self):
        """Create an ImportanceScorer."""
        return ImportanceScorer()

    def test_chair_base_tier(self, scorer):
        """Test Chair gets high base tier."""
        speaker = Speaker(name="Jerome Powell", role=SpeakerRole.CHAIR)
        features = Features(word_count=1000, topics=TopicFlags())

        importance = scorer.score(speaker, DocType.SPEECH, features)
        assert importance.tier == ImportanceTier.HIGH

    def test_governor_base_tier(self, scorer):
        """Test Governor gets medium base tier."""
        speaker = Speaker(name="Michelle Bowman", role=SpeakerRole.GOVERNOR)
        features = Features(word_count=1000, topics=TopicFlags())

        importance = scorer.score(speaker, DocType.SPEECH, features)
        assert importance.tier == ImportanceTier.MEDIUM

    def test_testimony_boost(self, scorer):
        """Test testimony increases importance."""
        speaker = Speaker(name="Michelle Bowman", role=SpeakerRole.GOVERNOR)
        features = Features(word_count=1000, topics=TopicFlags())

        speech_importance = scorer.score(speaker, DocType.SPEECH, features)
        testimony_importance = scorer.score(speaker, DocType.TESTIMONY, features)

        assert testimony_importance.score > speech_importance.score

    def test_qa_boost(self, scorer):
        """Test Q&A presence increases importance."""
        speaker = Speaker(name="Michelle Bowman", role=SpeakerRole.GOVERNOR)
        features_no_qa = Features(word_count=1000, has_qa=False, topics=TopicFlags())
        features_qa = Features(word_count=1000, has_qa=True, topics=TopicFlags())

        importance_no_qa = scorer.score(speaker, DocType.SPEECH, features_no_qa)
        importance_qa = scorer.score(speaker, DocType.SPEECH, features_qa)

        assert importance_qa.score > importance_no_qa.score

    def test_topic_boost(self, scorer):
        """Test rates + inflation/labor topics increase importance."""
        speaker = Speaker(name="Michelle Bowman", role=SpeakerRole.GOVERNOR)

        features_no_topics = Features(
            word_count=1000,
            topics=TopicFlags(),
        )
        features_with_topics = Features(
            word_count=1000,
            topics=TopicFlags(rates=True, inflation=True),
        )

        importance_no = scorer.score(speaker, DocType.SPEECH, features_no_topics)
        importance_with = scorer.score(speaker, DocType.SPEECH, features_with_topics)

        assert importance_with.score > importance_no.score

    def test_short_document_penalty(self, scorer):
        """Test short documents get reduced importance."""
        speaker = Speaker(name="Jerome Powell", role=SpeakerRole.CHAIR)
        features_short = Features(word_count=100, topics=TopicFlags())
        features_normal = Features(word_count=1000, topics=TopicFlags())

        importance_short = scorer.score(speaker, DocType.SPEECH, features_short)
        importance_normal = scorer.score(speaker, DocType.SPEECH, features_normal)

        assert importance_short.score < importance_normal.score

    def test_reasons_populated(self, scorer):
        """Test that reasons are populated."""
        speaker = Speaker(name="Jerome Powell", role=SpeakerRole.CHAIR)
        features = Features(
            word_count=1000,
            has_qa=True,
            topics=TopicFlags(rates=True, inflation=True),
        )

        importance = scorer.score(speaker, DocType.TESTIMONY, features)

        assert len(importance.reasons) >= 3
        assert any("Chair" in r for r in importance.reasons)

    def test_score_bounds(self, scorer):
        """Test score is always between 0 and 1."""
        speaker = Speaker(name="Test", role=SpeakerRole.GOVERNOR)
        features = Features(word_count=50, topics=TopicFlags())

        importance = scorer.score(speaker, DocType.SPEECH, features)
        assert 0 <= importance.score <= 1

