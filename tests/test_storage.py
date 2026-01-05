"""Tests for JSON storage."""

import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from fed_speech_mcp.storage import JSONStore
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


class TestJSONStore:
    """Tests for JSONStore."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def store(self, temp_dir):
        """Create a JSONStore for testing."""
        return JSONStore(temp_dir / "speeches", temp_dir / "raw")

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

    def test_save_and_get(self, store, sample_speech):
        """Test saving and retrieving a speech."""
        assert store.save(sample_speech) is True

        retrieved = store.get(sample_speech.doc_id)
        assert retrieved is not None
        assert retrieved.doc_id == sample_speech.doc_id
        assert retrieved.title == sample_speech.title

    def test_save_duplicate(self, store, sample_speech):
        """Test saving a duplicate returns False."""
        assert store.save(sample_speech) is True
        assert store.save(sample_speech) is False

    def test_get_nonexistent(self, store):
        """Test getting a nonexistent speech returns None."""
        assert store.get("nonexistent-id") is None

    def test_count(self, store, sample_speech):
        """Test counting speeches."""
        assert store.count() == 0
        store.save(sample_speech)
        assert store.count() == 1

    def test_get_latest(self, store):
        """Test getting latest speeches."""
        # Create speeches with different dates
        for i in range(5):
            speech = Speech(
                doc_id=f"fed-speech-test{i}",
                source=Source(
                    collection="speeches",
                    url=f"https://federalreserve.gov/test{i}",
                    retrieved_at=datetime(2024, 1, 15),
                ),
                published_at=datetime(2024, 1, 10 + i),
                title=f"Test Speech {i}",
                speaker=Speaker(name="Test", role=SpeakerRole.GOVERNOR),
                doc_type=DocType.SPEECH,
                text=TextContent(raw="...", clean="..."),
                features=Features(word_count=100, topics=TopicFlags()),
                importance=Importance(
                    tier=ImportanceTier.MEDIUM, score=0.5, reasons=[]
                ),
            )
            store.save(speech)

        latest = store.get_latest(limit=3)
        assert len(latest) == 3
        # Should be sorted newest first
        assert latest[0].published_at > latest[1].published_at

    def test_get_by_speaker(self, store):
        """Test filtering by speaker."""
        # Create speeches with different speakers
        speakers = [
            ("Powell", SpeakerRole.CHAIR),
            ("Bowman", SpeakerRole.GOVERNOR),
            ("Powell", SpeakerRole.CHAIR),
        ]

        for i, (name, role) in enumerate(speakers):
            speech = Speech(
                doc_id=f"fed-speech-{i}",
                source=Source(
                    collection="speeches",
                    url=f"https://federalreserve.gov/{i}",
                    retrieved_at=datetime(2024, 1, 15),
                ),
                published_at=datetime(2024, 1, 15),
                title=f"Speech {i}",
                speaker=Speaker(name=name, role=role),
                doc_type=DocType.SPEECH,
                text=TextContent(raw="...", clean="..."),
                features=Features(word_count=100, topics=TopicFlags()),
                importance=Importance(
                    tier=ImportanceTier.MEDIUM, score=0.5, reasons=[]
                ),
            )
            store.save(speech)

        # Filter by name
        powell_speeches = store.get_by_speaker(name="Powell")
        assert len(powell_speeches) == 2

        # Filter by role
        chair_speeches = store.get_by_speaker(role=SpeakerRole.CHAIR)
        assert len(chair_speeches) == 2

    def test_get_by_type(self, store):
        """Test filtering by document type."""
        types = [DocType.SPEECH, DocType.TESTIMONY, DocType.SPEECH]

        for i, dtype in enumerate(types):
            speech = Speech(
                doc_id=f"fed-speech-{i}",
                source=Source(
                    collection="speeches",
                    url=f"https://federalreserve.gov/{i}",
                    retrieved_at=datetime(2024, 1, 15),
                ),
                published_at=datetime(2024, 1, 15),
                title=f"Speech {i}",
                speaker=Speaker(name="Test", role=SpeakerRole.GOVERNOR),
                doc_type=dtype,
                text=TextContent(raw="...", clean="..."),
                features=Features(word_count=100, topics=TopicFlags()),
                importance=Importance(
                    tier=ImportanceTier.MEDIUM, score=0.5, reasons=[]
                ),
            )
            store.save(speech)

        speeches = store.get_by_type(DocType.SPEECH)
        assert len(speeches) == 2

        testimonies = store.get_by_type(DocType.TESTIMONY)
        assert len(testimonies) == 1

    def test_search(self, store):
        """Test searching speeches."""
        speeches_data = [
            ("Speech on Inflation", "Inflation remains elevated above our target."),
            ("Testimony on Rates", "Interest rates will remain higher for longer."),
            ("Speech on Economy", "Economic growth continues to be strong."),
        ]

        for i, (title, text) in enumerate(speeches_data):
            speech = Speech(
                doc_id=f"fed-speech-{i}",
                source=Source(
                    collection="speeches",
                    url=f"https://federalreserve.gov/{i}",
                    retrieved_at=datetime(2024, 1, 15),
                ),
                published_at=datetime(2024, 1, 15),
                title=title,
                speaker=Speaker(name="Test", role=SpeakerRole.GOVERNOR),
                doc_type=DocType.SPEECH,
                text=TextContent(raw=text, clean=text),
                features=Features(word_count=100, topics=TopicFlags()),
                importance=Importance(
                    tier=ImportanceTier.MEDIUM, score=0.5, reasons=[]
                ),
            )
            store.save(speech)

        # Search by title
        results = store.search("inflation")
        assert len(results) == 1
        assert "Inflation" in results[0].title

        # Search by content
        results = store.search("rates")
        assert len(results) == 1

    def test_delete(self, store, sample_speech):
        """Test deleting a speech."""
        store.save(sample_speech)
        assert store.count() == 1

        assert store.delete(sample_speech.doc_id) is True
        assert store.count() == 0
        assert store.get(sample_speech.doc_id) is None

    def test_delete_nonexistent(self, store):
        """Test deleting a nonexistent speech returns False."""
        assert store.delete("nonexistent") is False

    def test_clear(self, store, sample_speech):
        """Test clearing all speeches."""
        store.save(sample_speech)
        assert store.count() == 1

        deleted = store.clear()
        assert deleted == 1
        assert store.count() == 0

    def test_persistence(self, temp_dir, sample_speech):
        """Test that speeches persist across store instances."""
        # Save with first instance
        store1 = JSONStore(temp_dir / "speeches")
        store1.save(sample_speech)

        # Load with new instance
        store2 = JSONStore(temp_dir / "speeches")
        retrieved = store2.get(sample_speech.doc_id)

        assert retrieved is not None
        assert retrieved.doc_id == sample_speech.doc_id

