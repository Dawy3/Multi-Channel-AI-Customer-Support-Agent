# RAG System
> An intelligent, production-grade Retrieval-Augmented Generation (RAG) powered by multiple LLM providers, dual vector databases, and deployed on AWS with full observability.

---

##  Overview

This system ingests PDF and text documents (with OCR providers available for images / scanned documents), indexes them into a vector database, and exposes a conversational Q&A API. Retrieval is **hybrid** — it combines semantic vector search with lexical full-text search and fuses the two rankings — so answers stay grounded even when the user's wording doesn't match the document's wording.

---

##  Key Features

| Feature | Details |
|---|---|
| **Hybrid Retrieval** | Semantic (vector) **+** lexical (PostgreSQL full-text) search, fused with Reciprocal Rank Fusion (RRF) |
| **Multi-LLM Support** | OpenAI GPT + Cohere — switchable via environment config |
| **Dual Vector DB** | Qdrant (local/embedded) or PgVector (PostgreSQL) — provider-agnostic interface |
| **Conversational Memory** | Multi-turn chat history carried per request and capped via `CHAT_HISTORY_LIMIT` |
| **Multilingual** | Prompt templates in English 🇬🇧, Arabic 🇸🇦 and Spanish 🇪🇸 with auto language detection |
| **OCR Support** | Pluggable OCR providers (Google Gemini, Mistral) for extracting text from images / scanned docs |
| **Full Observability** | Prometheus metrics (incl. p50 / p95 / p99 latency) + Grafana dashboards |
| **AWS Deployment** | CI/CD via GitHub Actions (`deploy-main.yml`) to AWS |
| **Database Migrations** | Alembic-managed PostgreSQL schema with full version history |
| **Async Throughout** | Full async FastAPI + SQLAlchemy + asyncpg stack for high concurrency |

---

##  Application Workflow

The system runs in two phases: an **ingestion** pipeline that turns raw files into a searchable index, and a **retrieval** pipeline that answers questions against that index.

### 1. Ingestion (build the knowledge base)

```
Upload ──> Process ──> Index
```

1. **Upload** (`POST /api/v1/data/upload/{project_id}`) — the file is validated (type/size), given a unique name, written to disk, and recorded as an `asset` row. Each `project_id` is an isolated namespace.
2. **Process** (`POST /api/v1/data/process/{project_id}`) — the file is loaded (PDF via PyMuPDF, TXT via TextLoader; images via an OCR provider), split into overlapping text **chunks**, and the chunks are stored in PostgreSQL.
3. **Index** (`POST /api/v1/nlp/index/push/{project_id}`) — chunks are embedded (OpenAI / Cohere) and written to the vector collection in batches. On PgVector, an HNSW vector index is built once the collection passes a size threshold, and a `tsvector` column + GIN index are maintained for full-text search.

### 2. Retrieval (answer a question)

```
Query ──> Hybrid Search (semantic + lexical) ──> RRF fusion ──> Prompt build ──> LLM ──> Answer
```

1. **Hybrid search** — the query is embedded and run as a **vector** similarity search, *and* the raw query is run as a **full-text** search (`plainto_tsquery` / `ts_rank`) over the same collection.
2. **RRF fusion** — the two ranked lists are merged with **Reciprocal Rank Fusion** (`score = Σ 1 / (k + rank)`, `k = 60`), matching documents across lists by `chunk_id`. This favours chunks that rank well in *both* signals.
3. **Prompt assembly** — the top fused chunks become the document context; a system prompt + the recent chat history (capped by `CHAT_HISTORY_LIMIT`) + a footer carrying the question are assembled.
4. **Generation** — the LLM produces the answer, which is appended to the chat history and returned along with the retrieved documents.

> `POST /api/v1/nlp/index/search` exposes pure semantic search and `POST /api/v1/nlp/index/hybrid_search` exposes the fused retrieval directly, so you can inspect what the RAG step retrieves before generation.

---

##  Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) — async REST API framework
- [SQLAlchemy 2.0](https://www.sqlalchemy.org/) + [asyncpg](https://github.com/MagicStack/asyncpg) — async PostgreSQL ORM
- [Alembic](https://alembic.sqlalchemy.org/) — database migrations
- [LangChain](https://python.langchain.com/) — text splitting utilities

**AI / ML**
- [OpenAI API](https://platform.openai.com/) — GPT generation + embeddings
- [Cohere API](https://cohere.com/) — generation + embeddings with RAG-native document support
- OCR providers: [Google Gemini](https://ai.google.dev/) and [Mistral](https://mistral.ai/) — optional image / scanned-document text extraction

**Retrieval**
- Semantic search — vector similarity (cosine) over embeddings
- Lexical search — PostgreSQL full-text (`tsvector` + GIN index, `ts_rank`)
- Fusion — Reciprocal Rank Fusion (RRF) to blend both rankings

**Vector Databases**
- [Qdrant](https://qdrant.tech/) — lightweight embedded vector store
- [PgVector](https://github.com/pgvector/pgvector) — PostgreSQL vector extension with HNSW indexing

**Infrastructure**
- [Docker Compose](https://docs.docker.com/compose/) — full local environment
- [Nginx](https://nginx.org/) — reverse proxy
- [Prometheus](https://prometheus.io/) + [Grafana](https://grafana.com/) — metrics & dashboards
- [GitHub Actions](https://github.com/features/actions) — CI/CD pipeline

---

##  Quick Start

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- API keys for at least one LLM provider (OpenAI or Cohere)

### 1. Clone & Configure

```bash
git clone https://github.com/Dawy3/Production-ready-RAG-system
cd Production-ready-RAG-system
```

```bash
# App environment
cp src/.env.example src/.env
# Edit src/.env with your API keys (see Environment Variables below)
```
### 2 Run Alembic Migration
$ alembic upgrade head
### 3. Start Services with Docker

```bash
cd docker

# Copy and configure each env file
cp env/.env.examble_app        env/.env.app
cp env/.env.examble.postgres   env/.env.postgres
cp env/.env.examble.grafana    env/.env.grafana

# Start all services
sudo docker compose up -d
```

Or start only core services (no monitoring):

```bash
docker compose up -d fastapi nginx pgvector qdrant
```

### 4. Run the API (Local Development)

```bash
cd src
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: **http://localhost:8000/docs**

![Swagger UI](assets/images/swagger_ui.png)

---

##  API Reference

### Data Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/data/upload/{project_id}` | Upload a PDF or TXT document (images via OCR providers) |
| `POST` | `/api/v1/data/process/{project_id}` | Chunk document content and store chunks in PostgreSQL |

### NLP / RAG Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/nlp/index/push/{project_id}` | Embed chunks and push to the vector DB |
| `GET` | `/api/v1/nlp/index/info/{project_id}` | Get vector collection metadata |
| `POST` | `/api/v1/nlp/index/search/{project_id}` | Semantic (vector) similarity search |
| `POST` | `/api/v1/nlp/index/hybrid_search/{project_id}` | Hybrid search — vector + full-text, RRF-fused |
| `POST` | `/api/v1/nlp/index/answer/{project_id}` | Full RAG answer generation (hybrid retrieval + LLM) |

### RAG DEMO 

```bash
```
![RAG Demo](assets/images/rag_demo.gif)

---


---

##  Monitoring

Access the observability stack after running Docker Compose:

| Service | URL | Default Credentials |
|---|---|---|
| **API Docs** | http://localhost:8000/docs | — |
| **Grafana** | http://localhost:3000 | admin / see `.env.grafana` |
| **Prometheus** | http://localhost:9090 | — |
| **Qdrant UI** | http://localhost:6333/dashboard | — |

The stack also runs **node-exporter** (host metrics) and **postgres-exporter** (DB metrics), both scraped by Prometheus.

### Metrics

The FastAPI app exposes Prometheus metrics via a custom middleware (scrape path configured in `docker/prometheus/prometheus.yml`). Request latency is recorded as a histogram, so latency **percentiles** are computed at query time in Grafana, e.g. P95:

```promql
histogram_quantile(0.95, sum(rate(http_requests_duration_seconds_bucket[$__rate_interval])) by (le))
```

Swap `0.95` for `0.50` or `0.99` to get P50 / P99.

### Recommended Grafana Dashboards

- [FastAPI Observability](https://grafana.com/grafana/dashboards/18739) — request rates, latency, error rates
- [Node Exporter Full](https://grafana.com/grafana/dashboards/1860) — system metrics
- [PostgreSQL Exporter](https://grafana.com/grafana/dashboards/12485) — DB performance
- [Qdrant](https://grafana.com/grafana/dashboards/23033) — vector DB stats


---

##  Deployment

The project includes GitHub Actions workflows for automated deployment:

- **`develop-deploy.yml`** — triggered on pushes to the `develop` branch
- **`main-deploy.yml`** — triggered on pushes to `main` (production)

---

##  Database Migrations

Migrations are managed with Alembic. The schema includes three tables: `projects`, `assets`, and `chunk_data`.

```bash
cd src/db_models/db_schema/minirag

# Apply all migrations
alembic upgrade head

# Create a new migration (after model changes)
alembic revision --autogenerate -m "describe change"

# Rollback one step
alembic downgrade -1
```

---

## 📁 Project Structure

```
├── src/
│   ├── main.py                    # FastAPI app entry point
│   ├── controllers/               # Business logic layer
│   │   ├── nlp_controller.py      # RAG pipeline: hybrid search + RRF + answer
│   │   ├── process_controller.py  # Document loading & chunking
│   │   └── data_controller.py     # File validation & storage
│   ├── stores/
│   │   ├── llm/                   # OpenAI + Cohere providers + prompt templates (en/ar/es)
│   │   ├── ocr/                   # OCR providers (Gemini, Mistral)
│   │   └── vectorDB/             # Qdrant + PgVector providers (vector + full-text search)
│   ├── models/
│   │   ├── db_schemes/            # SQLAlchemy models + Alembic migrations
│   │   └── enums/                 # Response signals, processing types
│   ├── routes/                    # FastAPI route definitions (base / data / nlp)
│   └── utils/
│       └── metrics.py             # Prometheus middleware
└── docker/
    ├── docker-compose.yml
    ├── nginx/                     # reverse proxy config
    └── prometheus/               # scrape config
```

---


## 📄 License


This project is licensed under the terms in the [LICENSE](./LICENSE) file.
