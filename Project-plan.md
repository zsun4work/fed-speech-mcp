# Fed Major Officer Speech MCP – V1 Project Design

## 1. Goal and Non-Goals

**Goal**
Build a minimal MCP-compatible system that reliably retrieves speeches and testimonies from major Federal Reserve officers, parses them into clean structured JSON, and exposes them for downstream AI-based market analysis.

**Non-goals (V1)**

* No sentiment prediction or market forecasting
* No deep semantic modeling or embeddings
* No attempt to cover all regional Fed banks
* No real-time streaming guarantees (near-real-time is acceptable)

---

## 2. Scope (V1)

**Covered speakers**

* Chair of the Federal Reserve
* Vice Chair of the Federal Reserve
* Federal Reserve Governors

**Covered content types**

* Speeches
* Testimony
* Prepared remarks

**Excluded (for now)**

* Regional Fed Presidents
* Media interviews
* FOMC meeting minutes and policy statements
* Academic or research papers

---

## 3. Data Sources

### 3.1 Primary Source (Authoritative)

**Federal Reserve Board – official website**
Publisher: Board of Governors of the Federal Reserve System
Domain: [https://www.federalreserve.gov](https://www.federalreserve.gov)

Covered collections:

* Board of Governors speeches
* Congressional testimony
* Official press conference transcripts (when explicitly labeled)

Reasons for selection:

* Official and authoritative source
* Consistent publishing standards
* High market relevance
* Stable URLs and long-term availability

---

### 3.2 Discovery Mechanisms

**RSS Feeds (preferred for latest updates)**

* Federal Reserve speeches and testimony RSS feeds

**Index Pages (backfill and validation)**

* Year-based speech index pages on federalreserve.gov
* Testimony archive pages

**Direct Page Crawl (fallback)**

* Used when RSS or index coverage is incomplete

All ingested documents must be directly published by federalreserve.gov. No third-party mirrors are used in V1.

---

## 4. High-Level Architecture

**Core components**

* Ingestion service
* Parsing and normalization service
* Feature extraction service
* JSON storage
* MCP interface

**Data flow**

1. Discover new speech URLs
2. Fetch raw document content
3. Parse and normalize metadata and text
4. Extract deterministic features
5. Emit structured JSON
6. Serve JSON through MCP tools

---

## 5. Ingestion Design

**Discovery**

* Poll official Fed RSS feeds on a fixed interval
* Periodically scan yearly index pages for missed content
* Deduplicate URLs before fetching

**Fetch**

* Download HTML or PDF content
* Store raw response for traceability
* Retry transient failures with backoff

---

## 6. Parsing and Normalization

**Metadata extraction**

* Title
* Publication date
* Speaker name
* Speaker role
* Speech type
* Event name (if available)
* Location (if available)

**Normalization rules**

* Dates normalized to ISO 8601 (date only if time unavailable)
* Speaker roles mapped to a controlled vocabulary: Chair, Vice Chair, Governor
* Speech types mapped to: speech, testimony, prepared_remarks

**Text processing**

* Remove navigation, footers, and boilerplate
* Preserve paragraph structure
* Produce both raw_text and clean_text

---

## 7. Feature Extraction (V1)

Deterministic features only.

**Computed features**

* Word count
* Language (default: en)
* Presence of Q&A section (boolean)
* Topic mention flags

**Topic keyword groups**

* Inflation: inflation, prices, CPI, PCE
* Labor market: labor market, employment, unemployment, wages
* Rates: rate, fed funds, hike, cut, tighten, ease
* Balance sheet: balance sheet, QE, QT, runoff
* Growth: growth, GDP, demand, recession
* Financial stability: financial stability, banking, liquidity, stress

---

## 8. Importance Scoring (Rule-Based)

**Purpose**
Provide a transparent, explainable importance signal for market relevance.

**Base tier by role**

* Chair or Vice Chair: high
* Governor: medium

**Adjustments**

* Testimony: +1 tier
* Has Q&A: +1 tier
* Mentions rates AND (inflation OR labor market): +1 tier
* Word count < 300: -1 tier

**Output**

* importance.tier: high | medium | low
* importance.score: normalized numeric score (0–1)
* importance.reasons: list of explanatory strings

---

## 9. Output Format

Each document is emitted as a single structured JSON object containing:

* doc_id
* source (publisher, collection, url, retrieved_at)
* published_at
* title
* speaker (name, role, organization)
* doc_type
* event (name, location)
* text (raw, clean)
* features (word_count, language, has_qa, topic flags)
* importance (tier, score, reasons)

JSON must be deterministic, stable, and backward compatible.

---

## 10. MCP Interface (V1)

**Exposed MCP tools**

* get_latest_speeches(limit, since_date)
* get_speeches_by_speaker(name, role, start_date, end_date)
* get_speeches_by_type(doc_type, start_date, end_date)
* get_speech(doc_id)

All responses return structured JSON only.

---

## 11. Storage

* Persist structured JSON documents
* Retain raw source content for traceability
* Deduplicate using canonical URL plus normalized title and date hash

---

## 12. Quality and Safety

* Validate required fields before emitting JSON
* Log parsing failures with source URL
* Reject documents without confirmed speaker identity
* Monitor ingestion lag and parse success rate

---

## 13. Extension Points (Post-V1)

* Add regional Fed Presidents
* Add embeddings and semantic search
* Add market-impact modeling
* Add alerting and notifications
* Add cross-speech trend and topic analysis

---

END OF DOCUMENT
