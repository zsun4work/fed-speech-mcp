"""HTTP API wrapper for Fed Speech MCP.

This module provides a REST API interface to the Fed Speech functionality,
enabling integration with AI platforms that don't support MCP natively
(e.g., ChatGPT Custom GPTs, Google Gemini).

Usage:
    python -m fed_speech_mcp.http_server

The server runs on port 8000 by default (configurable via FED_SPEECH_HTTP_PORT).
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import config
from .ingestion import FedDiscovery, FedFetcher
from .models import DocType, SpeakerRole
from .parsing import FedHTMLParser, SpeechNormalizer
from .storage import JSONStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Response models
class SpeechSummary(BaseModel):
    """Summary of a speech for list responses."""

    doc_id: str
    title: str
    speaker_name: str
    speaker_role: str
    published_at: str
    doc_type: str
    importance_tier: str
    importance_score: float
    word_count: int
    url: str


class RefreshResponse(BaseModel):
    """Response for refresh operation."""

    discovered: int
    added: int
    errors: list[str]
    message: str


class StatsResponse(BaseModel):
    """Response for stats operation."""

    total: int
    date_range: dict
    by_role: dict
    by_type: dict
    by_importance: dict


# Global state
class AppState:
    """Application state container."""

    store: Optional[JSONStore] = None
    discovery: Optional[FedDiscovery] = None
    fetcher: Optional[FedFetcher] = None
    parser: Optional[FedHTMLParser] = None
    normalizer: Optional[SpeechNormalizer] = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    data_dir = Path(os.environ.get("FED_SPEECH_DATA_DIR", config.DATA_DIR))
    speeches_dir = data_dir / "speeches"
    raw_dir = data_dir / "raw"

    state.store = JSONStore(speeches_dir, raw_dir)
    state.discovery = FedDiscovery()
    state.fetcher = FedFetcher(raw_storage_path=raw_dir)
    state.parser = FedHTMLParser()
    state.normalizer = SpeechNormalizer()

    logger.info(f"Fed Speech HTTP API started. Data dir: {data_dir}")
    logger.info(f"Stored speeches: {state.store.count()}")

    yield

    # Shutdown
    if state.discovery:
        await state.discovery.close()
    if state.fetcher:
        await state.fetcher.close()


# Create FastAPI app
app = FastAPI(
    title="Fed Speech API",
    description="REST API for Federal Reserve speeches and testimonies",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware for browser-based access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def speech_to_summary(speech) -> SpeechSummary:
    """Convert a Speech object to a summary."""
    return SpeechSummary(
        doc_id=speech.doc_id,
        title=speech.title,
        speaker_name=speech.speaker.name,
        speaker_role=speech.speaker.role.value,
        published_at=speech.published_at.isoformat(),
        doc_type=speech.doc_type.value,
        importance_tier=speech.importance.tier.value,
        importance_score=speech.importance.score,
        word_count=speech.features.word_count,
        url=speech.source.url,
    )


@app.get("/")
async def root():
    """API root - health check and info."""
    return {
        "name": "Fed Speech API",
        "version": "1.0.0",
        "status": "running",
        "speeches_count": state.store.count() if state.store else 0,
    }


@app.get("/speeches/latest", response_model=list[SpeechSummary])
async def get_latest_speeches(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of speeches"),
    since_date: Optional[str] = Query(None, description="ISO 8601 date filter"),
):
    """Get the latest Federal Reserve speeches."""
    since_dt = None
    if since_date:
        try:
            since_dt = datetime.fromisoformat(since_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(400, f"Invalid date format: {since_date}")

    speeches = state.store.get_latest(limit=limit, since_date=since_dt)
    return [speech_to_summary(s) for s in speeches]


@app.get("/speeches/search", response_model=list[SpeechSummary])
async def search_speeches(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
):
    """Search speeches by keyword."""
    if not query.strip():
        raise HTTPException(400, "Query cannot be empty")

    speeches = state.store.search(query, limit=limit)
    return [speech_to_summary(s) for s in speeches]


@app.get("/speeches/by-speaker", response_model=list[SpeechSummary])
async def get_speeches_by_speaker(
    name: Optional[str] = Query(None, description="Speaker name (partial match)"),
    role: Optional[str] = Query(None, description="Speaker role"),
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
):
    """Get speeches filtered by speaker."""
    speaker_role = None
    if role:
        role_map = {
            "chair": SpeakerRole.CHAIR,
            "vice chair": SpeakerRole.VICE_CHAIR,
            "governor": SpeakerRole.GOVERNOR,
        }
        speaker_role = role_map.get(role.lower())
        if not speaker_role:
            raise HTTPException(400, f"Invalid role: {role}")

    start_dt = None
    end_dt = None
    try:
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(400, f"Invalid date format: {e}")

    speeches = state.store.get_by_speaker(
        name=name, role=speaker_role, start_date=start_dt, end_date=end_dt
    )
    return [speech_to_summary(s) for s in speeches]


@app.get("/speeches/by-type", response_model=list[SpeechSummary])
async def get_speeches_by_type(
    doc_type: str = Query(..., description="Document type"),
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
):
    """Get speeches filtered by document type."""
    type_map = {
        "speech": DocType.SPEECH,
        "testimony": DocType.TESTIMONY,
        "prepared_remarks": DocType.PREPARED_REMARKS,
    }
    dtype = type_map.get(doc_type.lower())
    if not dtype:
        raise HTTPException(400, f"Invalid doc_type: {doc_type}")

    start_dt = None
    end_dt = None
    try:
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(400, f"Invalid date format: {e}")

    speeches = state.store.get_by_type(doc_type=dtype, start_date=start_dt, end_date=end_dt)
    return [speech_to_summary(s) for s in speeches]


@app.get("/speeches/{doc_id}")
async def get_speech(doc_id: str):
    """Get a specific speech by document ID."""
    speech = state.store.get(doc_id)
    if not speech:
        raise HTTPException(404, f"Speech not found: {doc_id}")

    # Return full speech data
    return speech.model_dump(mode="json")


@app.post("/speeches/refresh", response_model=RefreshResponse)
async def refresh_speeches(
    include_index: bool = Query(False, description="Also scan index pages"),
    years: Optional[str] = Query(None, description="Comma-separated years for index scan"),
):
    """Fetch new speeches from the Federal Reserve website."""
    scan_years = None
    if years:
        try:
            scan_years = [int(y.strip()) for y in years.split(",")]
        except ValueError:
            raise HTTPException(400, f"Invalid years format: {years}")

    try:
        # Discover new documents
        discovered = await state.discovery.discover_all(
            include_index=include_index, years=scan_years
        )

        new_count = 0
        errors = []

        for doc in discovered:
            try:
                # Fetch content
                fetched = await state.fetcher.fetch(doc.url)

                # Parse content
                parsed = state.parser.parse(fetched.content, doc.url)

                # Override with discovered metadata if available
                if doc.published_at and not parsed.published_at:
                    parsed.published_at = doc.published_at
                if doc.speaker_name and not parsed.speaker_name:
                    parsed.speaker_name = doc.speaker_name

                # Normalize to Speech object
                speech = state.normalizer.normalize(
                    parsed, doc.url, fetched.fetched_at
                )

                # Save to store
                if state.store.save(speech):
                    new_count += 1

            except Exception as e:
                errors.append(f"{doc.url}: {str(e)}")
                logger.error(f"Error processing {doc.url}: {e}")

        return RefreshResponse(
            discovered=len(discovered),
            added=new_count,
            errors=errors[:10],  # Limit error list
            message=f"Refresh complete. Found {len(discovered)} documents, added {new_count} new speeches.",
        )

    except Exception as e:
        logger.error(f"Error refreshing speeches: {e}")
        raise HTTPException(500, f"Refresh failed: {str(e)}")


@app.get("/speeches/stats", response_model=StatsResponse)
async def get_speech_stats():
    """Get statistics about stored speeches."""
    speeches = state.store.list_all()
    total = len(speeches)

    if total == 0:
        return StatsResponse(
            total=0,
            date_range={},
            by_role={},
            by_type={},
            by_importance={},
        )

    by_role = {}
    by_type = {}
    by_importance = {}

    for s in speeches:
        role = s.speaker.role.value
        by_role[role] = by_role.get(role, 0) + 1

        dtype = s.doc_type.value
        by_type[dtype] = by_type.get(dtype, 0) + 1

        tier = s.importance.tier.value
        by_importance[tier] = by_importance.get(tier, 0) + 1

    oldest = min(s.published_at for s in speeches)
    newest = max(s.published_at for s in speeches)

    return StatsResponse(
        total=total,
        date_range={
            "oldest": oldest.isoformat(),
            "newest": newest.isoformat(),
        },
        by_role=by_role,
        by_type=by_type,
        by_importance=by_importance,
    )


def main():
    """Run the HTTP API server."""
    import uvicorn

    port = int(os.environ.get("FED_SPEECH_HTTP_PORT", "8000"))
    host = os.environ.get("FED_SPEECH_HTTP_HOST", "0.0.0.0")

    logger.info(f"Starting Fed Speech HTTP API on {host}:{port}")

    uvicorn.run(
        "fed_speech_mcp.http_server:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()

