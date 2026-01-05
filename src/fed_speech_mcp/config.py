"""Configuration for Fed Speech MCP."""

import os
from pathlib import Path


class Config:
    """Configuration settings for the Fed Speech MCP server."""

    # Base paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    SPEECHES_DIR = DATA_DIR / "speeches"
    RAW_DIR = DATA_DIR / "raw"

    # HTTP settings
    HTTP_TIMEOUT = 30.0
    MAX_RETRIES = 3
    USER_AGENT = "FedSpeechMCP/1.0 (Research; Academic)"

    # Discovery settings
    POLL_INTERVAL_SECONDS = 3600  # 1 hour
    DEFAULT_BACKFILL_YEARS = 2

    # RSS Feed URLs
    RSS_FEEDS = {
        "speeches": "https://www.federalreserve.gov/feeds/speeches.xml",
        "testimony": "https://www.federalreserve.gov/feeds/testimony.xml",
    }

    # Index page URLs
    INDEX_URLS = {
        "speeches": "https://www.federalreserve.gov/newsevents/speeches.htm",
        "testimony": "https://www.federalreserve.gov/newsevents/testimony.htm",
    }

    # Server settings
    SERVER_NAME = "fed-speech-mcp"
    SERVER_VERSION = "1.0.0"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config = cls()

        # Override paths from environment
        if data_dir := os.environ.get("FED_SPEECH_DATA_DIR"):
            config.DATA_DIR = Path(data_dir)
            config.SPEECHES_DIR = config.DATA_DIR / "speeches"
            config.RAW_DIR = config.DATA_DIR / "raw"

        # Override HTTP settings
        if timeout := os.environ.get("FED_SPEECH_HTTP_TIMEOUT"):
            config.HTTP_TIMEOUT = float(timeout)

        if retries := os.environ.get("FED_SPEECH_MAX_RETRIES"):
            config.MAX_RETRIES = int(retries)

        return config


# Default configuration instance
config = Config.from_env()

