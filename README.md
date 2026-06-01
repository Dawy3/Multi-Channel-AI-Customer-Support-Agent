# RAG System
> An intelligent, production-grade Retrieval-Augmented Generation (RAG) powered by multiple LLM providers, dual vector databases, and deployed on AWS with full observability.

---

##  Overview

This system ingests PDF, text, and image documents (images are processed with OCR) and exposes a conversational Q&A API. 

---

##  Key Features

| Feature | Details |
|---|---|
| **Multi-LLM Support** | OpenAI GPT + Cohere + LLama — switchable via environment config |
| **Dual Vector DB** | Qdrant (local/embedded) or PgVector (PostgreSQL) — provider-agnostic interface |
| **Bilingual** | Prompt templates in English 🇬🇧 and Arabic 🇸🇦 with auto language detection |
| **OCR Support** | Image ingestion with OCR (Tesseract locally or AWS Textract in cloud deployments) to extract text from PNG/JPG/TIFF |
| **Production Observability** | Prometheus metrics + Grafana dashboards for request counts, latency, DB stats |
| **AWS Deployment** | CI/CD via GitHub Actions with separate `develop` and `main` pipelines |
| **Database Migrations** | Alembic-managed PostgreSQL schema with full version history |
| **Async Throughout** | Full async FastAPI + SQLAlchemy + asyncpg stack for high concurrency |

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
- OCR: Tesseract (local) and AWS Textract (cloud) — optional image ingestion and text extraction

**Vector Databases**
- [Qdrant](https://qdrant.tech/) — lightweight embedded vector store
- [PgVector](https://github.com/pgvector/pgvector) — PostgreSQL vector extension with HNSW indexing

**Infrastructure**
- [Docker Compose](https://docs.docker.com/compose/) — full local environment
- [Nginx](https://nginx.org/) — reverse proxy
- [Prometheus](https://prometheus.io/) + [Grafana](https://grafana.com/) — monitoring
- [GitHub Actions](https://github.com/features/actions) — CI/CD pipelines

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
| `POST` | `/app/v2/data/upload/{project_id}` | Upload a PDF, TXT, or image document (PNG/JPG/TIFF) |
| `POST` | `/app/v2/data/process/{project_id}` | Chunk, OCR (if image), and store document content |

### NLP / RAG Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/app/v2/nlp/index/push/{project_id}` | Embed chunks and push to vector DB |
| `GET` | `/app/v2/nlp/index/info/{project_id}` | Get vector collection metadata |
| `POST` | `/app/v2/nlp/index/search/{project_id}` | Semantic similarity search |
| `POST` | `/app/v2/nlp/index/answer/{project_id}` | Full RAG answer generation |

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
│   ├── contoroller/               # Business logic layer
│   │   ├── nlp_contoroller.py     # RAG pipeline orchestration
│   │   ├── process_contoroller.py # Document chunking
│   │   └── data_contoroller.py    # File validation & storage
│   ├── stores/
│   │   ├── LLM/                   # OpenAI + Cohere providers
│   │   │   └── OCR/               # OCR helpers (Tesseract / Textract)
│   │   └── vectorDB/              # Qdrant + PgVector providers
│   ├── models/
│   │   ├── db_schemes/            # SQLAlchemy models + Alembic
│   │   └── enums/                 # Response signals, processing types
│   ├── Routers/                   # FastAPI route definitions
│   └── utils/
│       └── metrics.py             # Prometheus middleware
└── docker/
    ├── docker-compose.yml
    ├── nginx/
    └── Prometheus/
```

---


## 📄 License


This project is licensed under the terms in the [LICENSE](./LICENSE) file.
