#!/usr/bin/env python3
"""
Local testing script for Fed Speech MCP.

This script allows you to test all MCP tools locally without needing
to connect to Claude or another AI assistant.

Usage:
    python scripts/test_local.py [command] [options]

Commands:
    refresh         Fetch new speeches from the Fed website
    latest          Show latest speeches
    search          Search speeches by keyword
    speaker         Get speeches by speaker
    type            Get speeches by document type
    get             Get a specific speech by ID
    stats           Show storage statistics
    all             Run all tests

Examples:
    python scripts/test_local.py refresh
    python scripts/test_local.py latest --limit 5
    python scripts/test_local.py search --query "inflation"
    python scripts/test_local.py speaker --name "Powell"
    python scripts/test_local.py type --doc-type testimony
    python scripts/test_local.py get --doc-id fed-speech-abc123
    python scripts/test_local.py stats
    python scripts/test_local.py all
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fed_speech_mcp.config import config
from fed_speech_mcp.ingestion import FedDiscovery, FedFetcher
from fed_speech_mcp.models import DocType, SpeakerRole
from fed_speech_mcp.parsing import FedHTMLParser, SpeechNormalizer
from fed_speech_mcp.storage import JSONStore


class LocalTester:
    """Local tester for Fed Speech MCP tools."""

    def __init__(self, data_dir: Path = None):
        """Initialize the tester."""
        self.data_dir = data_dir or config.DATA_DIR
        self.speeches_dir = self.data_dir / "speeches"
        self.raw_dir = self.data_dir / "raw"

        # Initialize components
        self.store = JSONStore(self.speeches_dir, self.raw_dir)
        self.discovery = FedDiscovery()
        self.fetcher = FedFetcher(raw_storage_path=self.raw_dir)
        self.parser = FedHTMLParser()
        self.normalizer = SpeechNormalizer()

    async def refresh_speeches(self, include_index: bool = False, limit: int = None):
        """Fetch new speeches from the Fed website."""
        print("=" * 60)
        print("🔄 REFRESHING SPEECHES FROM FED WEBSITE")
        print("=" * 60)
        print(f"Include index pages: {include_index}")
        print()

        try:
            # Discover new documents
            print("📡 Discovering documents via RSS feeds...")
            discovered = await self.discovery.discover_all(include_index=include_index)

            if limit:
                discovered = discovered[:limit]

            print(f"   Found {len(discovered)} document(s)")
            print()

            new_count = 0
            errors = []

            for i, doc in enumerate(discovered, 1):
                print(f"[{i}/{len(discovered)}] Processing: {doc.title[:50]}...")

                try:
                    # Fetch content
                    fetched = await self.fetcher.fetch(doc.url)
                    print(f"   ✅ Fetched {len(fetched.content)} bytes")

                    # Parse content
                    parsed = self.parser.parse(fetched.content, doc.url)
                    print(f"   ✅ Parsed: {parsed.speaker_name or 'Unknown'} - {parsed.doc_type}")

                    # Override with discovered metadata
                    if doc.published_at and not parsed.published_at:
                        parsed.published_at = doc.published_at
                    if doc.speaker_name and not parsed.speaker_name:
                        parsed.speaker_name = doc.speaker_name

                    # Normalize
                    speech = self.normalizer.normalize(parsed, doc.url, fetched.fetched_at)
                    print(f"   ✅ Normalized: {speech.doc_id}")

                    # Save
                    if self.store.save(speech):
                        new_count += 1
                        print(f"   ✅ Saved (NEW)")
                    else:
                        print(f"   ⏭️  Already exists")

                except Exception as e:
                    errors.append(f"{doc.url}: {e}")
                    print(f"   ❌ Error: {e}")

                print()

            print("=" * 60)
            print(f"✅ REFRESH COMPLETE")
            print(f"   Discovered: {len(discovered)}")
            print(f"   New: {new_count}")
            print(f"   Errors: {len(errors)}")
            print(f"   Total in storage: {self.store.count()}")
            print("=" * 60)

        except Exception as e:
            print(f"❌ Refresh failed: {e}")
            raise

    async def get_latest_speeches(self, limit: int = 10, since_date: str = None):
        """Get latest speeches."""
        print("=" * 60)
        print("📰 LATEST SPEECHES")
        print("=" * 60)

        since_dt = None
        if since_date:
            since_dt = datetime.fromisoformat(since_date)
            print(f"Filter: since {since_date}")

        speeches = self.store.get_latest(limit=limit, since_date=since_dt)

        if not speeches:
            print("No speeches found. Run 'refresh' first to fetch content.")
            return

        print(f"Found {len(speeches)} speech(es):\n")

        for i, speech in enumerate(speeches, 1):
            self._print_speech_summary(i, speech)

    async def search_speeches(self, query: str, limit: int = 10):
        """Search speeches by keyword."""
        print("=" * 60)
        print(f"🔍 SEARCH: '{query}'")
        print("=" * 60)

        speeches = self.store.search(query, limit=limit)

        if not speeches:
            print(f"No speeches found matching '{query}'.")
            return

        print(f"Found {len(speeches)} result(s):\n")

        for i, speech in enumerate(speeches, 1):
            self._print_speech_summary(i, speech)

    async def get_by_speaker(self, name: str = None, role: str = None):
        """Get speeches by speaker."""
        print("=" * 60)
        print(f"👤 SPEECHES BY SPEAKER")
        print("=" * 60)

        speaker_role = None
        if role:
            role_map = {
                "chair": SpeakerRole.CHAIR,
                "vice chair": SpeakerRole.VICE_CHAIR,
                "governor": SpeakerRole.GOVERNOR,
            }
            speaker_role = role_map.get(role.lower())

        if name:
            print(f"Filter: name contains '{name}'")
        if speaker_role:
            print(f"Filter: role = {speaker_role.value}")

        speeches = self.store.get_by_speaker(name=name, role=speaker_role)

        if not speeches:
            print("No speeches found matching criteria.")
            return

        print(f"\nFound {len(speeches)} speech(es):\n")

        for i, speech in enumerate(speeches, 1):
            self._print_speech_summary(i, speech)

    async def get_by_type(self, doc_type: str):
        """Get speeches by document type."""
        print("=" * 60)
        print(f"📄 SPEECHES BY TYPE: {doc_type}")
        print("=" * 60)

        type_map = {
            "speech": DocType.SPEECH,
            "testimony": DocType.TESTIMONY,
            "prepared_remarks": DocType.PREPARED_REMARKS,
        }
        dtype = type_map.get(doc_type.lower())

        if not dtype:
            print(f"Invalid doc_type: {doc_type}")
            print("Valid types: speech, testimony, prepared_remarks")
            return

        speeches = self.store.get_by_type(doc_type=dtype)

        if not speeches:
            print(f"No {doc_type} documents found.")
            return

        print(f"Found {len(speeches)} document(s):\n")

        for i, speech in enumerate(speeches, 1):
            self._print_speech_summary(i, speech)

    async def get_speech(self, doc_id: str):
        """Get a specific speech by ID."""
        print("=" * 60)
        print(f"📖 SPEECH DETAILS: {doc_id}")
        print("=" * 60)

        speech = self.store.get(doc_id)

        if not speech:
            print(f"Speech not found: {doc_id}")
            print("\nAvailable speeches:")
            for s in self.store.get_latest(limit=5):
                print(f"  - {s.doc_id}")
            return

        self._print_speech_full(speech)

    async def get_stats(self):
        """Get storage statistics."""
        print("=" * 60)
        print("📊 STORAGE STATISTICS")
        print("=" * 60)

        speeches = self.store.list_all()
        total = len(speeches)

        if total == 0:
            print("No speeches in storage.")
            print("Run 'refresh' to fetch content from the Fed website.")
            return

        by_role = {}
        by_type = {}
        by_tier = {}

        for s in speeches:
            role = s.speaker.role.value
            by_role[role] = by_role.get(role, 0) + 1

            dtype = s.doc_type.value
            by_type[dtype] = by_type.get(dtype, 0) + 1

            tier = s.importance.tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        oldest = min(s.published_at for s in speeches)
        newest = max(s.published_at for s in speeches)

        print(f"\nTotal speeches: {total}")
        print(f"Date range: {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}")

        print("\nBy Speaker Role:")
        for k, v in sorted(by_role.items()):
            print(f"  {k}: {v}")

        print("\nBy Document Type:")
        for k, v in sorted(by_type.items()):
            print(f"  {k}: {v}")

        print("\nBy Importance Tier:")
        for k, v in sorted(by_tier.items()):
            print(f"  {k}: {v}")

    async def run_all_tests(self):
        """Run all tests in sequence."""
        print("\n" + "=" * 60)
        print("🧪 RUNNING ALL TESTS")
        print("=" * 60 + "\n")

        # 1. Refresh (limited)
        print("Test 1: Refresh speeches (limited to 3)")
        print("-" * 40)
        await self.refresh_speeches(include_index=False, limit=3)
        print()

        # 2. Stats
        print("\nTest 2: Get statistics")
        print("-" * 40)
        await self.get_stats()
        print()

        # 3. Latest
        print("\nTest 3: Get latest speeches")
        print("-" * 40)
        await self.get_latest_speeches(limit=3)
        print()

        # 4. Search
        print("\nTest 4: Search for 'inflation'")
        print("-" * 40)
        await self.search_speeches("inflation", limit=3)
        print()

        # 5. By speaker
        print("\nTest 5: Get speeches by Chair")
        print("-" * 40)
        await self.get_by_speaker(role="chair")
        print()

        # 6. Get specific speech
        speeches = self.store.get_latest(limit=1)
        if speeches:
            print("\nTest 6: Get specific speech details")
            print("-" * 40)
            await self.get_speech(speeches[0].doc_id)
        print()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETE")
        print("=" * 60)

    def _print_speech_summary(self, num: int, speech):
        """Print a speech summary."""
        topics = []
        if speech.features.topics.inflation:
            topics.append("inflation")
        if speech.features.topics.rates:
            topics.append("rates")
        if speech.features.topics.labor_market:
            topics.append("labor")

        print(f"{num}. {speech.title[:60]}{'...' if len(speech.title) > 60 else ''}")
        print(f"   📅 {speech.published_at.strftime('%Y-%m-%d')}")
        print(f"   👤 {speech.speaker.name} ({speech.speaker.role.value})")
        print(f"   📄 {speech.doc_type.value} | {speech.features.word_count} words")
        print(f"   ⭐ {speech.importance.tier.value} ({speech.importance.score})")
        if topics:
            print(f"   🏷️  Topics: {', '.join(topics)}")
        print(f"   🔗 {speech.source.url}")
        print(f"   🆔 {speech.doc_id}")
        print()

    def _print_speech_full(self, speech):
        """Print full speech details."""
        print(f"\nTitle: {speech.title}")
        print(f"ID: {speech.doc_id}")
        print(f"\n--- Metadata ---")
        print(f"Speaker: {speech.speaker.name}")
        print(f"Role: {speech.speaker.role.value}")
        print(f"Date: {speech.published_at.strftime('%Y-%m-%d')}")
        print(f"Type: {speech.doc_type.value}")
        print(f"Event: {speech.event.name or 'N/A'}")
        print(f"Location: {speech.event.location or 'N/A'}")
        print(f"URL: {speech.source.url}")

        print(f"\n--- Analysis ---")
        print(f"Word Count: {speech.features.word_count}")
        print(f"Has Q&A: {'Yes' if speech.features.has_qa else 'No'}")
        print(f"Importance: {speech.importance.tier.value} ({speech.importance.score})")
        print(f"Reasons:")
        for reason in speech.importance.reasons:
            print(f"  - {reason}")

        print(f"\n--- Topics ---")
        topics = speech.features.topics
        print(f"Inflation: {'✓' if topics.inflation else '✗'}")
        print(f"Labor Market: {'✓' if topics.labor_market else '✗'}")
        print(f"Rates: {'✓' if topics.rates else '✗'}")
        print(f"Balance Sheet: {'✓' if topics.balance_sheet else '✗'}")
        print(f"Growth: {'✓' if topics.growth else '✗'}")
        print(f"Financial Stability: {'✓' if topics.financial_stability else '✗'}")

        print(f"\n--- Content Preview ---")
        preview = speech.text.clean[:500]
        print(preview + ("..." if len(speech.text.clean) > 500 else ""))

    async def cleanup(self):
        """Clean up resources."""
        await self.discovery.close()
        await self.fetcher.close()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Fed Speech MCP tools locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # refresh
    refresh_parser = subparsers.add_parser("refresh", help="Fetch new speeches")
    refresh_parser.add_argument("--include-index", action="store_true", help="Also scan index pages")
    refresh_parser.add_argument("--limit", type=int, help="Limit number of documents to process")

    # latest
    latest_parser = subparsers.add_parser("latest", help="Show latest speeches")
    latest_parser.add_argument("--limit", type=int, default=10, help="Number of speeches")
    latest_parser.add_argument("--since", type=str, help="Since date (ISO format)")

    # search
    search_parser = subparsers.add_parser("search", help="Search speeches")
    search_parser.add_argument("--query", "-q", required=True, help="Search query")
    search_parser.add_argument("--limit", type=int, default=10, help="Max results")

    # speaker
    speaker_parser = subparsers.add_parser("speaker", help="Get speeches by speaker")
    speaker_parser.add_argument("--name", "-n", help="Speaker name")
    speaker_parser.add_argument("--role", "-r", help="Speaker role (Chair, Vice Chair, Governor)")

    # type
    type_parser = subparsers.add_parser("type", help="Get speeches by type")
    type_parser.add_argument("--doc-type", "-t", required=True, help="Document type")

    # get
    get_parser = subparsers.add_parser("get", help="Get specific speech")
    get_parser.add_argument("--doc-id", "-i", required=True, help="Document ID")

    # stats
    subparsers.add_parser("stats", help="Show statistics")

    # all
    subparsers.add_parser("all", help="Run all tests")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    tester = LocalTester()

    try:
        if args.command == "refresh":
            await tester.refresh_speeches(
                include_index=args.include_index,
                limit=args.limit,
            )
        elif args.command == "latest":
            await tester.get_latest_speeches(limit=args.limit, since_date=args.since)
        elif args.command == "search":
            await tester.search_speeches(args.query, limit=args.limit)
        elif args.command == "speaker":
            await tester.get_by_speaker(name=args.name, role=args.role)
        elif args.command == "type":
            await tester.get_by_type(args.doc_type)
        elif args.command == "get":
            await tester.get_speech(args.doc_id)
        elif args.command == "stats":
            await tester.get_stats()
        elif args.command == "all":
            await tester.run_all_tests()
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

