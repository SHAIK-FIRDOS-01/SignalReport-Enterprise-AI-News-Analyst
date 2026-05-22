<div align="center">

# 📰 SignalReport
### Enterprise AI News Analyst

*An autonomous RAG pipeline that transforms high-volume global news into structured, actionable semantic intelligence — scaled via a decoupled microservices architecture to offload high-compute LLM operations and network-heavy ingestion.*

---

[![Llama 3.3](https://img.shields.io/badge/LLM-Llama_3.3-0467DF?style=for-the-badge&logo=meta)](https://llama.meta.com/)
[![Groq](https://img.shields.io/badge/Inference-Groq-orange?style=for-the-badge)](https://groq.com/)
[![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react)](https://react.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC?style=for-the-badge&logo=tailwind-css)](https://tailwindcss.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

</div>

---

## 🚀 Key Features

| Feature | Description |
|---|---|
| **Decoupled Microservices** | Offloads CPU-intensive LLM inference and external API fetching from the core application into high-throughput microservices |
| **Autonomous RAG Pipeline** | Dynamically queries, embeds, and processes global news using Llama 3.3 via Groq for rapid semantic analysis |
| **Async Ingestion** | `asyncio` loop with exponential backoff and custom fail-safes, maximizing pipeline durability during high-concurrency API stress |
| **Real-Time NLP Engine** | Streamlined sentiment calculation and structured entity extraction — filters irrelevant noise by **30%** |
| **Strict Schema Enforcement** | Native Pydantic v2 validation guarantees **100% data consistency** for automated glossary generation and downstream APIs |
| **Enterprise Storage** | PostgreSQL data layer for optimal relational integrity, multi-tenant index tracking, and vector-ready compatibility |
| **Glassmorphic Dashboard** | Premium React interface with Framer Motion micro-interactions, dynamic terminology tooltips, and contextual Q&A |

---

## 🛠️ Technology Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                         SignalReport                            │
├───────────────────┬─────────────────────┬───────────────────────┤
│  AI & Ingestion   │   Core Platform     │      Frontend         │
│   (Microservice)  │  & Business Logic   │     Dashboard         │
├───────────────────┼─────────────────────┼───────────────────────┤
│  FastAPI          │  Django 6.0         │  React 19             │
│  Llama 3.3        │  Django REST        │  Tailwind CSS v4      │
│  Groq             │  Framework          │  Framer Motion        │
│  GNews API        │                     │                       │
│  Pydantic v2      │                     │                       │
├───────────────────┴─────────────────────┴───────────────────────┤
│                     Data Layer                                  │
│              PostgreSQL (Relational Tracking & Analytics)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
SignalReport/
├── services/
│   └── ai_ingestion/        # FastAPI microservice
│                            # GNews processing, Groq LLM calls, NLP extraction
├── backend/                 # Core Django application
│                            # Auth, business logic, configs, dashboard APIs
└── frontend/                # React dashboard
                             # Glassmorphic intelligence interface
```

---

## 🏁 Getting Started

### Prerequisites

- Python `3.12+`
- Node.js `(Latest LTS)`
- PostgreSQL `(Running instance)`
- `GROQ_API_KEY`
- `GNEWS_API_KEY`

---

### Installation & Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/SHAIK-FIRDOS-01/SignalReport.git
cd SignalReport
```

#### 2. Configure the Storage Layer

Ensure your PostgreSQL instance is running, then create a database named `signalreport`. Add a `.env` file inside `/backend` with your database credentials.

#### 3. Start the FastAPI Ingestion Microservice

```bash
cd services/ai_ingestion
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables: GROQ_API_KEY and GNEWS_API_KEY
uvicorn main:app --port 8001 --reload
```

#### 4. Initialize the Django Backend

```bash
cd ../../backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

#### 5. Launch the Frontend

```bash
cd ../frontend
npm install
npm run dev
```

---

<div align="center">

Built by **Shaik Firdos**

</div>
