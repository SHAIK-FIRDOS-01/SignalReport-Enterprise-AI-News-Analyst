# 🏛️ SignalReport: Enterprise Backend Architecture & Engineering Blueprint

> **System Purpose:** A high-throughput, decoupled, real-time **Tech Intelligence & Signal Radar Platform** that continuously ingests, analyzes, vectorizes, and serves high-signal tech updates (Product Launches, Startup Funding, Research Papers, Upgrades/Degrades, and Developer Buzz) with sub-second hybrid semantic retrieval and contextual AI intelligence.

---

## 📑 Table of Contents
1. [High-Level Architecture & Topology](#1-high-level-architecture--topology)
2. [Why Celery? (Operational Role & Concurrency)](#2-why-celery-operational-role--concurrency)
3. [Why Redis? (The 4 Distinct Roles)](#3-why-redis-the-4-distinct-roles)
4. [Multi-Stream Data Ingestion & Signal Taxonomy](#4-multi-stream-data-ingestion--signal-taxonomy)
5. [Lightweight Hybrid RAG & Vector Engine](#5-lightweight-hybrid-rag--vector-engine)
6. [Enterprise Security & Zero-Trust Defense-in-Depth](#6-enterprise-security--zero-trust-defense-in-depth)
7. [Database Design, Indexing & Scalability](#7-database-design-indexing--scalability)
8. [Monetization & AI Usage Quotas](#8-monetization--ai-usage-quotas)
9. [100% Free-Tier Production Deployment Plan](#9-100-free-tier-production-deployment-plan)

---

## 1. High-Level Architecture & Topology

The backend utilizes a **decoupled microservices architecture** to completely isolate compute-intensive LLM inference, scraping, and vector embeddings from the client-facing transaction and authentication gateway.

```text
                                  [ Browser / Client ]
                                           │
                         (HTTPS / SameSite HttpOnly Cookie)
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        CORE API GATEWAY (Django 5.0 + DRF)                             │
│  - Identity, Sessions & RBAC (Argon2id + JWT HttpOnly)                                 │
│  - Monetization Middleware (Enforces 2 Free AI Calls & Premium Gate)                   │
│  - Business Logic, Knowledge Base CRUD, Hybrid Search Query Router                    │
│  - Response Cache Layer (django-redis) & Rate Limiting (django-ratelimit)              │
│  - Strict Zero-Trust Middleware (CSP, HSTS, Frame Guard)                              │
└───────────────────┬────────────────────────────────────────────────┬───────────────────┘
                    │                                                │
       (Internal Microservice HTTP +                                 │ (ORM Queries +
        X-Internal-Service-Key)                                      │  pgvector L2 Distance)
                    ▼                                                ▼
┌──────────────────────────────────────┐       ┌─────────────────────────────────────────┐
│ FASTAPI HIGH-COMPUTE ENGINE          │       │ PRIMARY DATA STORE                      │
│ - Multi-Stream Ingestion (arXiv,     │       │ (PostgreSQL 17 + pgvector extension)    │
│   HackerNews, GitHub, Funding RSS)   │       │ - kb_node (Articles, JSON metadata)     │
│ - Anti-SSRF Scraping (trafilatura)   │       │ - GIN Index (Full-Text Search Vector)   │
│ - NLP & Sentiment (vaderSentiment)   │       │ - HNSW / IVFFlat Index (pgvector 384D)  │
│ - Groq Llama 3.3 70B Structured JSON │       │ - users & permissions (Argon2 hashes)   │
│ - WebSocket Alert Hub (/ws/alerts)   │       └─────────────────────────────────────────┘
└───────────────────▲──────────────────┘                             ▲
                    │                                                │
         (Pub/Sub Event Listener)                       (Reads/Writes Task Queue)
                    │                                                │
┌───────────────────┴────────────────────────────────────────────────┴───────────────────┐
│                               REDIS 7.x IN-MEMORY STORE                                │
│  1. Celery Message Broker & Result Store                                               │
│  2. Ingestion Distributed Lock (INGESTION_LOCK_KEY)                                    │
│  3. Real-Time Pub/Sub Channel (news_alerts -> WebSocket Broadcast)                     │
│  4. API Response, Query Vector Cache, & Real-Time Token/Call Counters                  │
└───────────────────────────────────────────▲────────────────────────────────────────────┘
                                            │
                                 (Dispatches Scheduled Jobs)
                                            │
┌───────────────────────────────────────────┴────────────────────────────────────────────┐
│                       ASYNC BACKGROUND WORKERS (Celery 5.x)                            │
│  - Celery Beat Scheduler: Periodic cron triggers (every 10 min to 6 hrs)               │
│  - Batch Scraping Worker: Background article text extraction                           │
│  - AI Enrichment Pipeline: LLM categorization, fact extraction, and vectorization       │
│  - Exponential Backoff & Retry handler for external API rate limits                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Why Celery? (Operational Role & Concurrency)

In a web application, user-facing HTTP request-response cycles must execute in **< 150ms**. If scraping, external API network calls, or LLM reasoning are executed synchronously inside a Django view:

1. **Request Timeouts:** Fetching 20 web articles takes 20–60 seconds, triggering HTTP `504 Gateway Timeouts` on proxies (Cloudflare, Nginx, Render).
2. **Thread Starvation:** If multiple users trigger refresh actions, all web server worker threads block waiting for external I/O, crashing the API for all users.
3. **Lack of Scheduling:** Django alone cannot natively run periodic background cron jobs without an external process.

### How Celery Solves This:

* **Asynchronous Task Offloading:** When an ingestion is triggered, Django immediately returns `{"status": "processing"}` to the client in **10ms**, while Celery handles the heavy compute asynchronously.
* **Celery Beat (Autonomous Cron):** Automatically executes scheduled tasks on defined cadences:
  * **Every 10 minutes:** Ingest latest HackerNews and TechCrunch Funding feeds.
  * **Every 1 hour:** Poll GitHub Releases API for major framework version updates.
  * **Every 6 hours:** Ingest newly submitted research papers from arXiv (`cs.AI`, `cs.LG`, `cs.CL`).
* **Rate-Limit Resilience & Retries:** When upstream APIs return `429 Too Many Requests`, Celery workers automatically retry using **exponential backoff with jitter** (`countdown=2 ** retries`).
* **Concurrency Management:** Limits the number of concurrent external scraping threads to prevent the server IP from being rate-limited or blacklisted by news publishers.

---

## 3. Why Redis? (The 4 Distinct Roles)

Redis operates completely in RAM with microsecond latency. In this architecture, it handles **four distinct system responsibilities**:

```text
                                    ┌──────────────────────┐
                                    │      REDIS 7.x       │
                                    └──────────┬───────────┘
                                               │
      ┌────────────────────────┬───────────────┴───────────────┬────────────────────────┐
      ▼                        ▼                               ▼                        ▼
┌──────────────────┐ ┌────────────────────┐          ┌───────────────────┐    ┌───────────────────┐
│ 1. Celery Broker │ │ 2. Distributed Lock│          │ 3. Pub/Sub Engine │    │ 4. Response Cache │
│ Queues background│ │ Prevents race      │          │ Emits live alerts │    │ & Call Quotas     │
│ task payloads    │ │ conditions         │          │ to WebSockets     │    │ Tracks user AI API│
└──────────────────┘ └────────────────────┘          └───────────────────┘    │ usage limits      │
                                                                              └───────────────────┘
```

1. **Celery Message Broker & Result Backend:** Passes serialised JSON task signatures between Django, Celery Beat, and Celery worker processes.
2. **Distributed Ingestion Lock (`INGESTION_LOCK_KEY`):** Prevents race conditions when multiple scheduled tasks or user requests fire at the same moment.
3. **Real-time Pub/Sub Alert Bridge:** Publishes new tech signals to the WebSocket manager for instant client broadcast without polling.
4. **Multi-Tiered Query Caching & Quota Tracking:** Caches common dashboard feed queries and tracks high-speed rate limits and AI usage quotas for the freemium gating system.

---

## 4. Multi-Stream Data Ingestion & Signal Taxonomy

The system transitions from generic news to a structured **Tech Intelligence Radar** categorized into five specific signal types:

### A. Signal Taxonomy

| Signal Type | Description | Key Extracted Metadata |
| --- | --- | --- |
| `LAUNCH` | New products, open-source models, developer tools | Product Name, Creator/Company, URL, Key Feature Set |
| `FUNDING` | Seed to Series D, VC rounds, acquisitions, IPOs | Company, Amount ($M), Round Type, Lead Investors, Valuation |
| `RESEARCH` | Breakthrough arXiv / Hugging Face research papers | Authors, arXiv ID, Benchmark Scores (e.g. MMLU, AIME), Code Link |
| `UPGRADE` | Major software updates, deprecations, outages | Software Name, Version Tag, Breaking Changes, Deprecations |
| `BUZZ` | Community debates, viral tech discussions | Source (HN/Reddit), Upvotes, Comment Count, Sentiment Score |

### B. Ingestion Streams (FastAPI Microservice)

1. **HackerNews Collector (`hn_ingestion.py`):** Ingests `topstories`, `newstories`, and `showstories` via Firebase REST API.
2. **Research Collector (`paper_ingestion.py`):** Ingests top trending papers via **Hugging Face Daily Papers API** and **arXiv API**.
3. **Releases Collector (`github_ingestion.py`):** Ingests latest releases and tags from high-impact open-source repositories.
4. **Funding & Enterprise RSS (`tech_feed_ingestion.py`):** Ingests structured RSS feeds from TechCrunch, VentureBeat, and Crunchbase.

---

## 5. Lightweight Hybrid RAG & Vector Engine

### A. Direct In-Context vs. Vector RAG

* **Single Article Processing:** Modern LLMs (Llama 3.3 on Groq) possess a 128,000-token context window. An entire 3,000-word article is sent directly to Groq in a single pass (`< 0.8s`) for summarization and metadata extraction, requiring **no chunking and no vector database overhead**.
* **Cross-Article Hybrid RAG:** Vector embeddings and full-text search are used exclusively for cross-article discovery, thematic grouping, and multi-article synthesis.

### B. Storage Footprint Calculation

Using compact 384-dimension embeddings (e.g., `BAAI/bge-small-en-v1.5`):

* **10,000 Articles:** $\approx 15.3\text{ MB}$ vector storage
* **Conclusion:** Fits well within free PostgreSQL database tiers (Supabase/Neon 500 MB quota) while leaving **> 400 MB** for text and metadata.

### C. Zero-RAM Embedding Generation

To prevent server memory exhaustion (OOM crashes) on free hosting:

* **FastEmbed (ONNX Runtime):** Quantized ONNX embeddings consuming **< 40 MB RAM** with **< 10ms execution time**.

---

## 6. Enterprise Security & Zero-Trust Defense-in-Depth

| Security Domain | Enterprise Implementation |
| --- | --- |
| **1. Password Hashing** | Argon2id (Winner of Password Hashing Competition, OWASP Top 1 standard). |
| **2. JWT Session Storage** | HttpOnly, Secure, SameSite=Strict cookies. Eliminates token exfiltration via XSS. |
| **3. Inter-Service Auth** | Cryptographic `X-Internal-Service-Key` shared secret header between Django and FastAPI. |
| **4. Anti-SSRF Defense** | IP & scheme validation to block private ranges (`127.0.0.1`, `169.254.169.254`). |
| **5. LLM Prompt Guard** | System/User prompt isolation, strict JSON output schema enforcement, text sanitizing. |

---

## 7. Database Design, Indexing & Scalability

### A. Schema Architecture (`kb_node` Table)

* `title`, `source_url` (`UNIQUE INDEX`), `published_at` (`INDEXED`), `signal_type` (`INDEXED`), `tech_domain` (`INDEXED`)
* `full_text_scraped`: Cleaned article body in Markdown
* `metadata_json`: Structured funding amounts, arXiv IDs, benchmark scores
* `search_vector`: `SearchVectorField` (`GIN INDEXED` for PostgreSQL Full-Text Search)
* `embedding_vector`: `VectorField(dimensions=384)` (`HNSW INDEXED` for pgvector)

### B. Schema Architecture (`users` Table) - *Monetization Tracking*

* `id`, `email`, `password_hash`
* `ai_calls_used`: `INTEGER DEFAULT 0` (Tracks the number of AI requests made by the user).
* `payment_method_active`: `BOOLEAN DEFAULT FALSE` (Flag indicating if the user has added a valid $10 payment method via Stripe).

---

## 8. Monetization & AI Usage Quotas

To ensure platform sustainability and manage strict LLM API constraints, AI features (such as user-triggered synthesis, semantic search, or on-demand summaries) are gated at the Django API Gateway using custom quota middleware.

### A. First-Time Sign-Up (Freemium Gate)

* **Trial Quota:** Upon initial registration, new users are automatically granted a hard cap of exactly **2 free AI calls** to test and evaluate the system.
* **Usage Enforcement:** Each incoming request to an AI-enabled endpoint routes through Redis and decrements the user's available quota in real-time.
* **Hard Stop:** Once `ai_calls_used >= 2`, the API Gateway immediately intercepts the request and returns a `402 Payment Required` HTTP status, completely blocking downstream LLM inference.

### B. Premium Tier ($10 Gate)

* **Payment Integration:** To unlock further AI access, the user must attach a valid payment method (e.g., adding $10 via Stripe integration).
* **State Change:** Upon successful payment capture, a webhook flips the user's `payment_method_active` boolean to `TRUE` in the PostgreSQL database.
* **Unrestricted Access:** The quota middleware bypasses the 2-call block for users with `payment_method_active=TRUE`, allowing standard rate-limited access to the AI services.

---

## 9. 100% Free-Tier Production Deployment Plan

This infrastructure delivers enterprise performance without hosting costs by leveraging high-allowance free tiers:

| Component | Recommended Provider | Free Tier Allocation & Benefits |
| --- | --- | --- |
| **PostgreSQL + pgvector** | Supabase OR Neon.tech | 500 MB storage (Holds 100k+ articles & embeddings) |
| **Redis Cache & Broker** | Upstash Redis | 10,000 commands/day free serverless Redis |
| **FastAPI AI & Scraper** | Hugging Face Spaces | 2 vCPUs, 16 GB RAM Docker Container (100% Free) |
| **Django Core Backend** | Render.com OR Koyeb | 750 free hours/month, native Python/Docker runtime |
| **LLM Inference Engine** | Groq Cloud | Free Developer Tier (Llama 3.3 70B & 8B) |

---
