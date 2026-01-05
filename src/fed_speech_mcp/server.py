"""MCP Server for Federal Reserve speeches."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .config import config
from .ingestion import FedDiscovery, FedFetcher
from .models import DocType, SpeakerRole, Speech
from .parsing import FedHTMLParser, SpeechNormalizer
from .storage import JSONStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FedSpeechMCP:
    """Fed Speech MCP Server implementation."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize the Fed Speech MCP server.

        Args:
            data_dir: Optional override for data directory.
        """
        self.data_dir = data_dir or config.DATA_DIR
        self.speeches_dir = self.data_dir / "speeches"
        self.raw_dir = self.data_dir / "raw"

        # Initialize components
        self.store = JSONStore(self.speeches_dir, self.raw_dir)
        self.discovery = FedDiscovery()
        self.fetcher = FedFetcher(raw_storage_path=self.raw_dir)
        self.parser = FedHTMLParser()
        self.normalizer = SpeechNormalizer()

        # Create MCP server
        self.server = Server(config.SERVER_NAME)
        self._setup_tools()

    def _setup_tools(self) -> None:
        """Set up MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="get_latest_speeches",
                    description="Get the latest Federal Reserve speeches. Returns speeches sorted by publication date, most recent first.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of speeches to return (default: 10, max: 50)",
                                "default": 10,
                            },
                            "since_date": {
                                "type": "string",
                                "description": "Only return speeches published on or after this date (ISO 8601 format, e.g., '2024-01-01')",
                            },
                        },
                    },
                ),
                Tool(
                    name="get_speeches_by_speaker",
                    description="Get Federal Reserve speeches by a specific speaker. Filter by name, role, and date range.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Speaker name (partial match, e.g., 'Powell' or 'Jerome Powell')",
                            },
                            "role": {
                                "type": "string",
                                "enum": ["Chair", "Vice Chair", "Governor"],
                                "description": "Speaker role filter",
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Start date filter (ISO 8601 format)",
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date filter (ISO 8601 format)",
                            },
                        },
                    },
                ),
                Tool(
                    name="get_speeches_by_type",
                    description="Get Federal Reserve speeches by document type (speech, testimony, or prepared_remarks).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "doc_type": {
                                "type": "string",
                                "enum": ["speech", "testimony", "prepared_remarks"],
                                "description": "Document type to filter by",
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Start date filter (ISO 8601 format)",
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date filter (ISO 8601 format)",
                            },
                        },
                        "required": ["doc_type"],
                    },
                ),
                Tool(
                    name="get_speech",
                    description="Get a specific Federal Reserve speech by its document ID. Returns the full speech content and metadata.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "doc_id": {
                                "type": "string",
                                "description": "The unique document identifier (e.g., 'fed-speech-abc123def456')",
                            },
                        },
                        "required": ["doc_id"],
                    },
                ),
                Tool(
                    name="refresh_speeches",
                    description="Fetch new speeches from the Federal Reserve website. This will check RSS feeds and optionally index pages for new content.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_index": {
                                "type": "boolean",
                                "description": "Whether to also scan index pages (slower but more thorough)",
                                "default": False,
                            },
                            "years": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Years to scan for index pages (only used if include_index is true)",
                            },
                        },
                    },
                ),
                Tool(
                    name="search_speeches",
                    description="Search Federal Reserve speeches by keyword. Searches in title and content.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (keywords to search for)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 10)",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="get_speech_stats",
                    description="Get statistics about stored Federal Reserve speeches.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "get_latest_speeches":
                    return await self._get_latest_speeches(arguments)
                elif name == "get_speeches_by_speaker":
                    return await self._get_speeches_by_speaker(arguments)
                elif name == "get_speeches_by_type":
                    return await self._get_speeches_by_type(arguments)
                elif name == "get_speech":
                    return await self._get_speech(arguments)
                elif name == "refresh_speeches":
                    return await self._refresh_speeches(arguments)
                elif name == "search_speeches":
                    return await self._search_speeches(arguments)
                elif name == "get_speech_stats":
                    return await self._get_speech_stats(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _get_latest_speeches(self, args: dict) -> list[TextContent]:
        """Get latest speeches."""
        limit = min(args.get("limit", 10), 50)
        since_date = None

        if since_str := args.get("since_date"):
            since_date = datetime.fromisoformat(since_str.replace("Z", "+00:00"))

        speeches = self.store.get_latest(limit=limit, since_date=since_date)
        return self._format_speeches_response(speeches)

    async def _get_speeches_by_speaker(self, args: dict) -> list[TextContent]:
        """Get speeches by speaker."""
        name = args.get("name")
        role = None
        start_date = None
        end_date = None

        if role_str := args.get("role"):
            role_map = {
                "Chair": SpeakerRole.CHAIR,
                "Vice Chair": SpeakerRole.VICE_CHAIR,
                "Governor": SpeakerRole.GOVERNOR,
            }
            role = role_map.get(role_str)

        if start_str := args.get("start_date"):
            start_date = datetime.fromisoformat(start_str.replace("Z", "+00:00"))

        if end_str := args.get("end_date"):
            end_date = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

        speeches = self.store.get_by_speaker(
            name=name, role=role, start_date=start_date, end_date=end_date
        )
        return self._format_speeches_response(speeches)

    async def _get_speeches_by_type(self, args: dict) -> list[TextContent]:
        """Get speeches by type."""
        doc_type_str = args.get("doc_type", "speech")
        start_date = None
        end_date = None

        doc_type_map = {
            "speech": DocType.SPEECH,
            "testimony": DocType.TESTIMONY,
            "prepared_remarks": DocType.PREPARED_REMARKS,
        }
        doc_type = doc_type_map.get(doc_type_str, DocType.SPEECH)

        if start_str := args.get("start_date"):
            start_date = datetime.fromisoformat(start_str.replace("Z", "+00:00"))

        if end_str := args.get("end_date"):
            end_date = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

        speeches = self.store.get_by_type(
            doc_type=doc_type, start_date=start_date, end_date=end_date
        )
        return self._format_speeches_response(speeches)

    async def _get_speech(self, args: dict) -> list[TextContent]:
        """Get a specific speech by ID."""
        doc_id = args.get("doc_id", "")

        speech = self.store.get(doc_id)
        if not speech:
            return [TextContent(type="text", text=f"Speech not found: {doc_id}")]

        return self._format_single_speech(speech)

    async def _refresh_speeches(self, args: dict) -> list[TextContent]:
        """Refresh speeches from Fed website."""
        include_index = args.get("include_index", False)
        years = args.get("years")

        try:
            # Discover new documents
            discovered = await self.discovery.discover_all(
                include_index=include_index, years=years
            )

            new_count = 0
            errors = []

            for doc in discovered:
                try:
                    # Fetch content
                    fetched = await self.fetcher.fetch(doc.url)

                    # Parse content
                    parsed = self.parser.parse(fetched.content, doc.url)

                    # Override with discovered metadata if available
                    if doc.published_at and not parsed.published_at:
                        parsed.published_at = doc.published_at
                    if doc.speaker_name and not parsed.speaker_name:
                        parsed.speaker_name = doc.speaker_name

                    # Normalize to Speech object
                    speech = self.normalizer.normalize(
                        parsed, doc.url, fetched.fetched_at
                    )

                    # Save to store
                    if self.store.save(speech):
                        new_count += 1

                except Exception as e:
                    errors.append(f"{doc.url}: {str(e)}")
                    logger.error(f"Error processing {doc.url}: {e}")

            result = f"Refresh complete. Found {len(discovered)} documents, added {new_count} new speeches."
            if errors:
                result += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:5])
                if len(errors) > 5:
                    result += f"\n... and {len(errors) - 5} more errors"

            return [TextContent(type="text", text=result)]

        except Exception as e:
            logger.error(f"Error refreshing speeches: {e}")
            return [TextContent(type="text", text=f"Error refreshing speeches: {str(e)}")]

    async def _search_speeches(self, args: dict) -> list[TextContent]:
        """Search speeches by keyword."""
        query = args.get("query", "")
        limit = min(args.get("limit", 10), 50)

        if not query:
            return [TextContent(type="text", text="Please provide a search query.")]

        speeches = self.store.search(query, limit=limit)
        return self._format_speeches_response(speeches, f"Search results for '{query}'")

    async def _get_speech_stats(self, args: dict) -> list[TextContent]:
        """Get storage statistics."""
        speeches = self.store.list_all()
        total = len(speeches)

        if total == 0:
            return [TextContent(type="text", text="No speeches in storage. Run 'refresh_speeches' to fetch content.")]

        # Calculate stats
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

        stats = f"""Fed Speech Storage Statistics
==============================

Total speeches: {total}
Date range: {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}

By Speaker Role:
{chr(10).join(f'  {k}: {v}' for k, v in sorted(by_role.items()))}

By Document Type:
{chr(10).join(f'  {k}: {v}' for k, v in sorted(by_type.items()))}

By Importance Tier:
{chr(10).join(f'  {k}: {v}' for k, v in sorted(by_tier.items()))}
"""

        return [TextContent(type="text", text=stats)]

    def _format_speeches_response(
        self, speeches: list[Speech], header: str = ""
    ) -> list[TextContent]:
        """Format a list of speeches as response."""
        if not speeches:
            return [TextContent(type="text", text="No speeches found matching the criteria.")]

        lines = []
        if header:
            lines.append(header)
            lines.append("=" * len(header))
            lines.append("")

        lines.append(f"Found {len(speeches)} speech(es):\n")

        for speech in speeches:
            lines.append(f"📄 {speech.title}")
            lines.append(f"   ID: {speech.doc_id}")
            lines.append(f"   Speaker: {speech.speaker.name} ({speech.speaker.role.value})")
            lines.append(f"   Date: {speech.published_at.strftime('%Y-%m-%d')}")
            lines.append(f"   Type: {speech.doc_type.value}")
            lines.append(f"   Importance: {speech.importance.tier.value} ({speech.importance.score})")
            lines.append(f"   Words: {speech.features.word_count}")
            lines.append(f"   URL: {speech.source.url}")
            lines.append("")

        return [TextContent(type="text", text="\n".join(lines))]

    def _format_single_speech(self, speech: Speech) -> list[TextContent]:
        """Format a single speech with full content."""
        topics = []
        if speech.features.topics.inflation:
            topics.append("inflation")
        if speech.features.topics.labor_market:
            topics.append("labor market")
        if speech.features.topics.rates:
            topics.append("rates")
        if speech.features.topics.balance_sheet:
            topics.append("balance sheet")
        if speech.features.topics.growth:
            topics.append("growth")
        if speech.features.topics.financial_stability:
            topics.append("financial stability")

        content = f"""# {speech.title}

## Metadata
- **Document ID:** {speech.doc_id}
- **Speaker:** {speech.speaker.name} ({speech.speaker.role.value})
- **Date:** {speech.published_at.strftime('%Y-%m-%d')}
- **Type:** {speech.doc_type.value}
- **Event:** {speech.event.name or 'N/A'}
- **Location:** {speech.event.location or 'N/A'}
- **URL:** {speech.source.url}

## Analysis
- **Word Count:** {speech.features.word_count}
- **Has Q&A:** {'Yes' if speech.features.has_qa else 'No'}
- **Topics:** {', '.join(topics) if topics else 'None detected'}
- **Importance:** {speech.importance.tier.value} (score: {speech.importance.score})
- **Importance Factors:**
{chr(10).join('  - ' + r for r in speech.importance.reasons)}

## Content

{speech.text.clean}
"""

        return [TextContent(type="text", text=content)]

    async def run(self) -> None:
        """Run the MCP server."""
        logger.info(f"Starting {config.SERVER_NAME} v{config.SERVER_VERSION}")
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Stored speeches: {self.store.count()}")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.discovery.close()
        await self.fetcher.close()


def main():
    """Main entry point."""
    mcp = FedSpeechMCP()

    try:
        asyncio.run(mcp.run())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        asyncio.run(mcp.cleanup())


if __name__ == "__main__":
    main()

