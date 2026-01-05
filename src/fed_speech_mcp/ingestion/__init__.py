"""Ingestion service for Fed speeches."""

from .discovery import FedDiscovery, DiscoveredDocument
from .fetcher import FedFetcher, FetchedContent

__all__ = [
    "FedDiscovery",
    "DiscoveredDocument",
    "FedFetcher",
    "FetchedContent",
]

