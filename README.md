# Fed Speech MCP

An MCP (Model Context Protocol) server that retrieves, parses, and analyzes speeches and testimonies from major Federal Reserve officers.

---

## Features

- 📡 **RSS Feed Discovery** - Automatically discovers new speeches from Fed RSS feeds
- 🔍 **Index Page Scanning** - Backfill capability by scanning yearly index pages
- 📝 **Smart Parsing** - Extracts metadata, speaker info, and clean text from Fed HTML pages
- 📊 **Feature Extraction** - Detects topics (inflation, rates, labor market, etc.)
- ⚖️ **Importance Scoring** - Rule-based scoring for market relevance
- 💾 **JSON Storage** - Persistent storage with deduplication
- 🔌 **MCP Interface** - Full MCP compatibility for AI assistants

## Covered Content

### Speakers
- Chair of the Federal Reserve
- Vice Chair of the Federal Reserve
- Federal Reserve Governors

### Content Types
- Speeches
- Congressional Testimony
- Prepared Remarks

---

## Installation

### Prerequisites
- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager

**Install uv** (if you don't have it):
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Install the Project

```bash
cd fed-speech-mcp

# Create virtual environment and install
uv sync
```

That's it! The virtual environment is created and all dependencies are installed.

---

## 🚀 Quick Start: Test Locally in 5 Minutes

Want to see the MCP tools in action before connecting to an AI? Follow these steps:

### Step 1: Install

```bash
cd fed-speech-mcp
uv sync
```

### Step 2: Fetch Speeches from Fed Website

```bash
uv run python scripts/test_local.py refresh --limit 5
```

You'll see output like:

```
🔄 REFRESHING SPEECHES FROM FED WEBSITE
==================================================
📡 Discovering documents via RSS feeds...
   Found 20 document(s)

[1/5] Processing: Governor Bowman's Speech on Banking...
   ✅ Fetched 45231 bytes
   ✅ Parsed: Michelle W. Bowman - speech
   ✅ Normalized: fed-speech-a1b2c3d4e5f6
   ✅ Saved (NEW)
...
✅ REFRESH COMPLETE
   Discovered: 5
   New: 5
   Total in storage: 5
```

### Step 3: Explore the Data

**View latest speeches:**
```bash
uv run python scripts/test_local.py latest --limit 3
```

Output:
```
📰 LATEST SPEECHES
==================================================
Found 3 speech(es):

1. Speech on Monetary Policy and the Economic Outlook
   📅 2024-12-15
   👤 Jerome H. Powell (Chair)
   📄 speech | 2500 words
   ⭐ high (0.85)
   🏷️  Topics: inflation, rates, labor
   🔗 https://federalreserve.gov/...
   🆔 fed-speech-abc123
```

**Search by keyword:**
```bash
uv run python scripts/test_local.py search --query "inflation"
```

**Filter by speaker:**
```bash
uv run python scripts/test_local.py speaker --name "Powell"
uv run python scripts/test_local.py speaker --role "Chair"
```

**Get full speech content:**
```bash
uv run python scripts/test_local.py get --doc-id fed-speech-abc123
```

**View statistics:**
```bash
uv run python scripts/test_local.py stats
```

### Step 4: Run All Tests

```bash
uv run python scripts/test_local.py all
```

This runs a complete test suite: refresh → stats → latest → search → filter → get.

### Available Test Commands

| Command | Description | Example |
|---------|-------------|---------|
| `refresh` | Fetch new speeches | `--limit 5`, `--include-index` |
| `latest` | Show latest speeches | `--limit 10`, `--since 2024-01-01` |
| `search` | Search by keyword | `--query "inflation"` |
| `speaker` | Filter by speaker | `--name "Powell"`, `--role "Chair"` |
| `type` | Filter by doc type | `--doc-type testimony` |
| `get` | Get full speech | `--doc-id fed-speech-xxx` |
| `stats` | Show statistics | (no options) |
| `all` | Run all tests | (no options) |

---

## Using with AI Assistants

### Platform Compatibility Overview

| Platform | MCP Support | Setup Method |
|----------|-------------|--------------|
| **Claude Desktop** | ✅ Native | Direct MCP integration |
| **Cursor IDE** | ✅ Native | Direct MCP integration |
| **ChatGPT** | ⚠️ Via API | HTTP API wrapper + Custom GPT |
| **Google Gemini** | ⚠️ Via API | HTTP API wrapper + Google AI Studio |
| **Other AI Tools** | ⚠️ Via API | HTTP API wrapper |

---

## Step-by-Step: Claude Desktop

Claude Desktop has native MCP support. This is the easiest setup.

### Step 1: Install the Package

```bash
cd fed-speech-mcp
uv sync
```

### Step 2: Locate Claude Desktop Config

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### Step 3: Add MCP Server Configuration

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fed-speech": {
      "command": "uv",
      "args": ["run", "fed-speech-mcp"],
      "cwd": "/path/to/fed-speech-mcp"
    }
  }
}
```

> **Note**: Replace `/path/to/fed-speech-mcp` with your actual installation path.

### Step 4: Restart Claude Desktop

Close and reopen Claude Desktop. You should see the Fed Speech tools available.

### Step 5: Start Using

Ask Claude things like:
- *"Refresh the Fed speeches and show me the latest ones"*
- *"What did Chair Powell say about inflation recently?"*
- *"Show me all testimony from 2024"*

---

## Step-by-Step: Cursor IDE

Cursor IDE also supports MCP natively.

### Step 1: Install the Package

```bash
cd fed-speech-mcp
uv sync
```

### Step 2: Open Cursor Settings

1. Open Cursor IDE
2. Go to **Settings** (⌘+, on macOS, Ctrl+, on Windows)
3. Search for "MCP" or navigate to **Features → MCP Servers**

### Step 3: Add MCP Server

Click "Add MCP Server" and configure:

```json
{
  "name": "fed-speech",
  "command": "uv",
  "args": ["run", "fed-speech-mcp"],
  "cwd": "/path/to/fed-speech-mcp"
}
```

### Step 4: Enable and Use

Toggle the server on. You can now use Fed Speech tools in Cursor's AI chat.

---

## Step-by-Step: ChatGPT (Custom GPT)

ChatGPT doesn't support MCP natively, but you can use the HTTP API wrapper.

### Step 1: Install the Package

```bash
cd fed-speech-mcp
uv sync
```

### Step 2: Start the HTTP API Server

```bash
uv run fed-speech-http
```

The server runs at `http://localhost:8000` by default.

### Step 3: Expose to Internet (Required for ChatGPT)

Use a tunneling service like ngrok:

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8000
```

Copy the public URL (e.g., `https://abc123.ngrok.io`).

### Step 4: Create a Custom GPT

1. Go to [ChatGPT](https://chat.openai.com)
2. Click your profile → **My GPTs** → **Create a GPT**
3. In the **Configure** tab:
   - **Name**: "Fed Speech Analyst"
   - **Description**: "Analyzes Federal Reserve speeches and testimonies"
   - **Instructions**: 
     ```
     You are a Federal Reserve speech analyst. Use the available actions to:
     1. Fetch latest speeches with get_latest_speeches
     2. Search speeches by speaker, type, or keywords
     3. Analyze speech content for market-relevant insights
     Always refresh speeches first if the user asks about recent content.
     ```

4. Click **Create new action** and import the OpenAPI schema:

```yaml
openapi: 3.0.0
info:
  title: Fed Speech API
  version: 1.0.0
servers:
  - url: https://your-ngrok-url.ngrok.io
paths:
  /speeches/latest:
    get:
      operationId: getLatestSpeeches
      summary: Get latest Fed speeches
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            default: 10
        - name: since_date
          in: query
          schema:
            type: string
      responses:
        '200':
          description: List of speeches
  /speeches/search:
    get:
      operationId: searchSpeeches
      summary: Search speeches by keyword
      parameters:
        - name: query
          in: query
          required: true
          schema:
            type: string
        - name: limit
          in: query
          schema:
            type: integer
            default: 10
      responses:
        '200':
          description: Search results
  /speeches/{doc_id}:
    get:
      operationId: getSpeech
      summary: Get a specific speech
      parameters:
        - name: doc_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Speech details
  /speeches/refresh:
    post:
      operationId: refreshSpeeches
      summary: Fetch new speeches from Fed website
      responses:
        '200':
          description: Refresh result
```

### Step 5: Save and Use

Save your Custom GPT. Now you can ask it questions about Fed speeches!

---

## Step-by-Step: Google Gemini

Google Gemini can use the HTTP API via Google AI Studio or API.

### Step 1: Start the HTTP API Server

```bash
cd fed-speech-mcp
uv sync
uv run fed-speech-http
```

### Step 2: Expose to Internet

```bash
ngrok http 8000
```

### Step 3: Use with Google AI Studio

1. Go to [Google AI Studio](https://aistudio.google.com)
2. Create a new prompt or chat
3. In your system instructions, include:

```
You have access to a Fed Speech API at https://your-ngrok-url.ngrok.io

Available endpoints:
- GET /speeches/latest?limit=10 - Get latest speeches
- GET /speeches/search?query=inflation - Search speeches
- GET /speeches/{doc_id} - Get specific speech
- POST /speeches/refresh - Fetch new speeches
- GET /speeches/by-speaker?name=Powell - Filter by speaker
- GET /speeches/by-type?doc_type=testimony - Filter by type

When users ask about Fed speeches, use these endpoints to fetch data.
Format responses clearly with speaker names, dates, and key points.
```

### Step 4: Use Function Calling (Advanced)

For programmatic use with Gemini API:

```python
import google.generativeai as genai
import requests

# Configure Gemini
genai.configure(api_key="YOUR_API_KEY")

# Define tools for Gemini
tools = [
    {
        "function_declarations": [
            {
                "name": "get_latest_speeches",
                "description": "Get the latest Federal Reserve speeches",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Max speeches to return"}
                    }
                }
            },
            {
                "name": "search_speeches",
                "description": "Search Fed speeches by keyword",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            }
        ]
    }
]

model = genai.GenerativeModel('gemini-pro', tools=tools)

# Handle function calls
def handle_function_call(fn_name, args):
    base_url = "http://localhost:8000"
    if fn_name == "get_latest_speeches":
        resp = requests.get(f"{base_url}/speeches/latest", params=args)
    elif fn_name == "search_speeches":
        resp = requests.get(f"{base_url}/speeches/search", params=args)
    return resp.json()

# Chat with function calling
chat = model.start_chat()
response = chat.send_message("What are the latest Fed speeches about inflation?")

# Process function calls in response
for part in response.parts:
    if hasattr(part, 'function_call'):
        fn = part.function_call
        result = handle_function_call(fn.name, dict(fn.args))
        # Send result back to model
        response = chat.send_message(str(result))
```

---

## HTTP API Reference

When using the HTTP API wrapper, these endpoints are available:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/speeches/latest` | GET | Get latest speeches |
| `/speeches/search` | GET | Search by keyword |
| `/speeches/{doc_id}` | GET | Get specific speech |
| `/speeches/by-speaker` | GET | Filter by speaker |
| `/speeches/by-type` | GET | Filter by doc type |
| `/speeches/refresh` | POST | Fetch new speeches |
| `/speeches/stats` | GET | Get statistics |

### Query Parameters

- `limit` - Max results (default: 10, max: 50)
- `since_date` - ISO 8601 date filter
- `start_date` / `end_date` - Date range
- `name` - Speaker name (partial match)
- `role` - "Chair", "Vice Chair", or "Governor"
- `doc_type` - "speech", "testimony", or "prepared_remarks"
- `query` - Search keywords

---

## Running the MCP Server Directly

For native MCP clients:

```bash
# Run the MCP server
uv run fed-speech-mcp

# Run the HTTP API server
uv run fed-speech-http
```

---

## Available Tools

### `get_latest_speeches`
Get the latest Federal Reserve speeches, sorted by publication date.

**Parameters:**
- `limit` (optional): Maximum number of speeches (default: 10, max: 50)
- `since_date` (optional): Only return speeches after this date (ISO 8601)

### `get_speeches_by_speaker`
Filter speeches by speaker name and/or role.

**Parameters:**
- `name` (optional): Speaker name (partial match, e.g., "Powell")
- `role` (optional): "Chair", "Vice Chair", or "Governor"
- `start_date` (optional): Start date filter
- `end_date` (optional): End date filter

### `get_speeches_by_type`
Get speeches by document type.

**Parameters:**
- `doc_type` (required): "speech", "testimony", or "prepared_remarks"
- `start_date` (optional): Start date filter
- `end_date` (optional): End date filter

### `get_speech`
Get full content and metadata for a specific speech.

**Parameters:**
- `doc_id` (required): The unique document identifier

### `refresh_speeches`
Fetch new speeches from the Federal Reserve website.

**Parameters:**
- `include_index` (optional): Also scan index pages (slower but thorough)
- `years` (optional): Years to scan for index pages

### `search_speeches`
Search speeches by keyword.

**Parameters:**
- `query` (required): Search query
- `limit` (optional): Maximum results (default: 10)

### `get_speech_stats`
Get statistics about stored speeches.

## Output Format

Each speech document contains:

```json
{
  "doc_id": "fed-speech-abc123def456",
  "source": {
    "publisher": "Board of Governors of the Federal Reserve System",
    "collection": "speeches",
    "url": "https://www.federalreserve.gov/...",
    "retrieved_at": "2024-01-15T10:30:00Z"
  },
  "published_at": "2024-01-15T00:00:00Z",
  "title": "Speech Title",
  "speaker": {
    "name": "Jerome H. Powell",
    "role": "Chair",
    "organization": "Board of Governors of the Federal Reserve System"
  },
  "doc_type": "speech",
  "event": {
    "name": "Economic Club of New York",
    "location": "New York, NY"
  },
  "text": {
    "raw": "...",
    "clean": "..."
  },
  "features": {
    "word_count": 2500,
    "language": "en",
    "has_qa": false,
    "topics": {
      "inflation": true,
      "labor_market": true,
      "rates": true,
      "balance_sheet": false,
      "growth": true,
      "financial_stability": false
    }
  },
  "importance": {
    "tier": "high",
    "score": 0.85,
    "reasons": [
      "Speaker is Chair (Jerome H. Powell)",
      "Discusses rates in context of inflation"
    ]
  }
}
```

## Importance Scoring

The importance score is calculated using these rules:

| Factor | Adjustment |
|--------|------------|
| Chair or Vice Chair speaker | Base: High |
| Governor speaker | Base: Medium |
| Testimony | +1 tier |
| Contains Q&A | +1 tier |
| Discusses rates + (inflation or labor market) | +1 tier |
| Word count < 300 | -1 tier |

## Topic Detection

Topics are detected by keyword matching:

- **Inflation**: inflation, prices, CPI, PCE, price stability
- **Labor Market**: employment, unemployment, wages, jobs
- **Rates**: interest rate, fed funds, hike, cut, monetary policy
- **Balance Sheet**: QE, QT, runoff, asset purchases
- **Growth**: GDP, demand, recession, economic activity
- **Financial Stability**: banking, liquidity, stress, systemic risk

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FED_SPEECH_DATA_DIR` | Data storage directory | `./data` |
| `FED_SPEECH_HTTP_TIMEOUT` | HTTP request timeout (seconds) | `30` |
| `FED_SPEECH_MAX_RETRIES` | Max retry attempts | `3` |
| `FED_SPEECH_HTTP_PORT` | HTTP API server port | `8000` |

## Data Storage

```
data/
├── speeches/           # Processed JSON documents
│   ├── fed-speech-xxx.json
│   └── ...
└── raw/               # Raw HTML content (for traceability)
    ├── 20240115_abc123.html
    └── ...
```

## Development

### Running Unit Tests

```bash
# Install with dev dependencies
uv sync --dev

# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_models.py

# Run with coverage
uv run pytest --cov=fed_speech_mcp
```

### Running Local Integration Tests

```bash
# Test all MCP functionality end-to-end
uv run python scripts/test_local.py all

# Test specific functionality
uv run python scripts/test_local.py refresh --limit 3
uv run python scripts/test_local.py search --query "rates"
```

### Project Structure

```
fed-speech-mcp/
├── src/fed_speech_mcp/
│   ├── __init__.py
│   ├── server.py          # MCP server entry point
│   ├── http_server.py     # HTTP API wrapper
│   ├── config.py          # Configuration
│   ├── models/            # Pydantic data models
│   ├── ingestion/         # RSS/index discovery & fetching
│   ├── parsing/           # HTML parsing & normalization
│   ├── features/          # Feature extraction & scoring
│   └── storage/           # JSON storage layer
├── data/                  # Data directory
├── pyproject.toml
└── README.md
```

## License

MIT

## Acknowledgments

Data sourced from the [Federal Reserve Board](https://www.federalreserve.gov/).
