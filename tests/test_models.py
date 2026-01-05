"""Tests for data models."""

import pytest
from datetime import datetime

from fed_speech_mcp.models import (
    Speech,
    Speaker,
    SpeakerRole,
    DocType,
    Source,
    Event,
    TextContent,
    Features,
    TopicFlags,
    Importance,
    ImportanceTier,
)


class TestSpeakerModel:
    """Tests for Speaker model."""

    def test_speaker_creation(self):
        """Test creating a Speaker."""
        speaker = Speaker(
            name="Jerome H. Powell",
            role=SpeakerRole.CHAIR,
        )
        assert speaker.name == "Jerome H. Powell"
        assert speaker.role == SpeakerRole.CHAIR
        assert "Federal Reserve" in speaker.organization

    def test_speaker_roles(self):
        """Test all speaker roles."""
        for role in SpeakerRole:
            speaker = Speaker(name="Test", role=role)
            assert speaker.role == role


class TestTopicFlags:
    """Tests for TopicFlags model."""

    def test_default_flags(self):
        """Test default topic flags are False."""
        flags = TopicFlags()
        assert flags.inflation is False
        assert flags.labor_market is False
        assert flags.rates is False
        assert flags.balance_sheet is False
        assert flags.growth is False
        assert flags.financial_stability is False

    def test_setting_flags(self):
        """Test setting topic flags."""
        flags = TopicFlags(inflation=True, rates=True)
        assert flags.inflation is True
        assert flags.rates is True
        assert flags.labor_market is False


class TestImportance:
    """Tests for Importance model."""

    def test_importance_creation(self):
        """Test creating Importance."""
        importance = Importance(
            tier=ImportanceTier.HIGH,
            score=0.85,
            reasons=["Speaker is Chair", "Discusses rates"],
        )
        assert importance.tier == ImportanceTier.HIGH
        assert importance.score == 0.85
        assert len(importance.reasons) == 2

    def test_score_bounds(self):
        """Test score is bounded between 0 and 1."""
        with pytest.raises(ValueError):
            Importance(tier=ImportanceTier.HIGH, score=1.5, reasons=[])

        with pytest.raises(ValueError):
            Importance(tier=ImportanceTier.HIGH, score=-0.1, reasons=[])


class TestSpeech:
    """Tests for Speech model."""

    @pytest.fixture
    def sample_speech(self):
        """Create a sample speech for testing."""
        return Speech(
            doc_id="fed-speech-test123",
            source=Source(
                collection="speeches",
                url="https://federalreserve.gov/test",
                retrieved_at=datetime(2024, 1, 15, 10, 30),
            ),
            published_at=datetime(2024, 1, 15),
            title="Test Speech on Monetary Policy",
            speaker=Speaker(name="Jerome H. Powell", role=SpeakerRole.CHAIR),
            doc_type=DocType.SPEECH,
            event=Event(name="Economic Club", location="New York"),
            text=TextContent(raw="Raw text...", clean="Clean text..."),
            features=Features(
                word_count=1500,
                language="en",
                has_qa=False,
                topics=TopicFlags(inflation=True, rates=True),
            ),
            importance=Importance(
                tier=ImportanceTier.HIGH,
                score=0.85,
                reasons=["Speaker is Chair"],
            ),
        )

    def test_speech_creation(self, sample_speech):
        """Test creating a Speech."""
        assert sample_speech.doc_id == "fed-speech-test123"
        assert sample_speech.speaker.name == "Jerome H. Powell"
        assert sample_speech.doc_type == DocType.SPEECH
        assert sample_speech.features.word_count == 1500

    def test_speech_json_serialization(self, sample_speech):
        """Test serializing Speech to JSON."""
        data = sample_speech.model_dump(mode="json")
        assert data["doc_id"] == "fed-speech-test123"
        assert data["speaker"]["name"] == "Jerome H. Powell"
        assert data["speaker"]["role"] == "Chair"
        assert data["doc_type"] == "speech"

    def test_speech_json_deserialization(self, sample_speech):
        """Test deserializing Speech from JSON."""
        data = sample_speech.model_dump(mode="json")
        restored = Speech.model_validate(data)
        assert restored.doc_id == sample_speech.doc_id
        assert restored.speaker.name == sample_speech.speaker.name

