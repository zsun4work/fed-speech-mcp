"""JSON storage for Fed speeches."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models import Speech, DocType, SpeakerRole


class JSONStore:
    """JSON file-based storage for Fed speeches.

    Features:
    - Persist structured JSON documents
    - Retain raw source content for traceability
    - Deduplicate using doc_id
    - Support querying by various criteria
    """

    def __init__(
        self,
        storage_path: Path,
        raw_path: Optional[Path] = None,
    ):
        """Initialize the JSON store.

        Args:
            storage_path: Path to store processed JSON documents.
            raw_path: Optional path to store raw content.
        """
        self._storage_path = Path(storage_path)
        self._raw_path = Path(raw_path) if raw_path else None
        self._index: dict[str, Speech] = {}
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure storage is initialized."""
        if self._initialized:
            return

        self._storage_path.mkdir(parents=True, exist_ok=True)
        if self._raw_path:
            self._raw_path.mkdir(parents=True, exist_ok=True)

        # Load existing documents into index
        self._load_index()
        self._initialized = True

    def _load_index(self) -> None:
        """Load all documents into memory index."""
        for filepath in self._storage_path.glob("*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                speech = Speech.model_validate(data)
                self._index[speech.doc_id] = speech
            except Exception as e:
                print(f"Warning: Failed to load {filepath}: {e}")

    def save(self, speech: Speech) -> bool:
        """Save a speech document.

        Args:
            speech: The speech to save.

        Returns:
            True if saved (new or updated), False if duplicate.
        """
        self._ensure_initialized()

        # Check for existing document
        existing = self._index.get(speech.doc_id)
        if existing:
            # Compare content hash to detect true duplicates
            if (
                existing.text.clean == speech.text.clean
                and existing.title == speech.title
            ):
                return False  # True duplicate

        # Save to file
        filepath = self._storage_path / f"{speech.doc_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(speech.model_dump(mode="json"), f, indent=2, default=str)

        # Update index
        self._index[speech.doc_id] = speech

        return True

    def get(self, doc_id: str) -> Optional[Speech]:
        """Get a speech by document ID.

        Args:
            doc_id: The document ID.

        Returns:
            The speech if found, None otherwise.
        """
        self._ensure_initialized()
        return self._index.get(doc_id)

    def get_latest(
        self,
        limit: int = 10,
        since_date: Optional[datetime] = None,
    ) -> list[Speech]:
        """Get latest speeches.

        Args:
            limit: Maximum number of speeches to return.
            since_date: Optional filter for speeches since this date.

        Returns:
            List of speeches sorted by published_at descending.
        """
        self._ensure_initialized()

        speeches = list(self._index.values())

        # Filter by date if specified
        if since_date:
            speeches = [s for s in speeches if s.published_at >= since_date]

        # Sort by published_at descending
        speeches.sort(key=lambda s: s.published_at, reverse=True)

        return speeches[:limit]

    def get_by_speaker(
        self,
        name: Optional[str] = None,
        role: Optional[SpeakerRole] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[Speech]:
        """Get speeches by speaker.

        Args:
            name: Speaker name (partial match).
            role: Speaker role.
            start_date: Start date filter.
            end_date: End date filter.

        Returns:
            List of matching speeches sorted by published_at descending.
        """
        self._ensure_initialized()

        speeches = list(self._index.values())

        # Filter by speaker name
        if name:
            name_lower = name.lower()
            speeches = [
                s for s in speeches if name_lower in s.speaker.name.lower()
            ]

        # Filter by role
        if role:
            speeches = [s for s in speeches if s.speaker.role == role]

        # Filter by date range
        if start_date:
            speeches = [s for s in speeches if s.published_at >= start_date]
        if end_date:
            speeches = [s for s in speeches if s.published_at <= end_date]

        # Sort by published_at descending
        speeches.sort(key=lambda s: s.published_at, reverse=True)

        return speeches

    def get_by_type(
        self,
        doc_type: DocType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[Speech]:
        """Get speeches by document type.

        Args:
            doc_type: Document type to filter by.
            start_date: Start date filter.
            end_date: End date filter.

        Returns:
            List of matching speeches sorted by published_at descending.
        """
        self._ensure_initialized()

        speeches = [s for s in self._index.values() if s.doc_type == doc_type]

        # Filter by date range
        if start_date:
            speeches = [s for s in speeches if s.published_at >= start_date]
        if end_date:
            speeches = [s for s in speeches if s.published_at <= end_date]

        # Sort by published_at descending
        speeches.sort(key=lambda s: s.published_at, reverse=True)

        return speeches

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[Speech]:
        """Search speeches by text content.

        Simple keyword search in title and clean text.

        Args:
            query: Search query.
            limit: Maximum results.

        Returns:
            List of matching speeches.
        """
        self._ensure_initialized()

        query_lower = query.lower()
        query_words = query_lower.split()

        results = []
        for speech in self._index.values():
            text_lower = speech.text.clean.lower()
            title_lower = speech.title.lower()

            # Check if all query words appear in title or text
            if all(
                word in text_lower or word in title_lower for word in query_words
            ):
                results.append(speech)

        # Sort by published_at descending
        results.sort(key=lambda s: s.published_at, reverse=True)

        return results[:limit]

    def list_all(self) -> list[Speech]:
        """List all speeches in storage.

        Returns:
            List of all speeches sorted by published_at descending.
        """
        self._ensure_initialized()

        speeches = list(self._index.values())
        speeches.sort(key=lambda s: s.published_at, reverse=True)

        return speeches

    def count(self) -> int:
        """Get total number of stored speeches."""
        self._ensure_initialized()
        return len(self._index)

    def delete(self, doc_id: str) -> bool:
        """Delete a speech by document ID.

        Args:
            doc_id: The document ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        self._ensure_initialized()

        if doc_id not in self._index:
            return False

        # Remove file
        filepath = self._storage_path / f"{doc_id}.json"
        if filepath.exists():
            filepath.unlink()

        # Remove from index
        del self._index[doc_id]

        return True

    def clear(self) -> int:
        """Clear all stored speeches.

        Returns:
            Number of speeches deleted.
        """
        self._ensure_initialized()

        count = len(self._index)

        # Remove all files
        for filepath in self._storage_path.glob("*.json"):
            filepath.unlink()

        # Clear index
        self._index.clear()

        return count

    def export_all(self, output_path: Path) -> int:
        """Export all speeches to a single JSON file.

        Args:
            output_path: Path to output file.

        Returns:
            Number of speeches exported.
        """
        self._ensure_initialized()

        speeches = self.list_all()
        data = [s.model_dump(mode="json") for s in speeches]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return len(speeches)

    def backup(self, backup_path: Path) -> None:
        """Create a backup of the storage directory.

        Args:
            backup_path: Path to backup directory.
        """
        self._ensure_initialized()

        if backup_path.exists():
            shutil.rmtree(backup_path)

        shutil.copytree(self._storage_path, backup_path)

