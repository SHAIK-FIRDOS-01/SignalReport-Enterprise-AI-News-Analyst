# 📰 SignalReport | Enterprise AI News Analyst

[![Llama 3.3](https://img.shields.io/badge/LLM-Llama_3.3-0467DF?style=for-the-badge&logo=meta)](https://llama.meta.com/)
[![Groq](https://img.shields.io/badge/Inference-Groq-orange?style=for-the-badge)](https://groq.com/)
[![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react)](https://react.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC?style=for-the-badge&logo=tailwind-css)](https://tailwindcss.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

📰 SignalReport | Enterprise AI News Analyst
An autonomous RAG pipeline designed to transform high-volume global news into structured, actionable semantic intelligence. Now scaled using a decoupled microservices architecture to offload high-compute LLM operations and network-heavy ingestion.

🚀 Key Features
Decoupled Microservices Architecture: Offloads CPU-intensive LLM inference and external API fetching from the core application framework into high-throughput microservices.

Autonomous RAG Pipeline: Dynamically queries, embeds, and processes global news using Llama 3.3 via Groq Inference for rapid semantic analysis.

Asynchronous Ingestion via GNews API: Built-in asyncio loop with exponential backoff and custom fail-safes, maximizing pipeline durability during high-concurrency API stress.

Real-Time NLP Engine: Streamlined sentiment calculation and structured entity extraction, filtering irrelevant noise down by 30%.

Strict Schema Enforcement: Native Pydantic structural validation guarantees 100% data consistency for automated glossary generation and down-stream consuming APIs.

Enterprise Storage Foundation: Migrated data layer to PostgreSQL for optimal relational integrity, multi-tenant index tracking, and vector-ready compatibility.

Glassmorphic Intelligence Digest: Premium responsive React interface featuring smooth Framer Motion micro-interactions, dynamic terminology tooltips, and interactive contextual Q&A.

🛠️ Technology Stack
AI & Ingestion Engine (Microservice): FastAPI, Llama 3.3, Groq, GNews API, Pydantic v2

Core Web Platform & Business Logic: Django 6.0, Django REST Framework (DRF)

Frontend Dashboard: React 19, Tailwind CSS v4, Framer Motion

Data Layer: PostgreSQL (Relational Tracking & Analytics)

📂 Project Structure
/services/ai_ingestion: FastAPI microservice responsible for GNews processing, Groq LLM calls, and NLP extraction.

/backend: Core Django application managing user authentication, business logic, system configurations, and dashboard API endpoints.

/frontend: High-fidelity glassmorphic intelligence dashboard.

🚀 Getting Started
Prerequisites
Python 3.12+

Node.js (Latest LTS)

PostgreSQL (Running instance)

Groq API Key

GNews API Key

Installation & Setup
Clone the Repository

Bash
git clone https://github.com/SHAIK-FIRDOS-01/SignalReport.git

cd SignalReport


2. Configure the Storage Layer**

Ensure your PostgreSQL instance is running and create a database named signalreport. Create a configuration file (.env) in your /backend directory containing your database credentials.

3. Start the FastAPI Ingestion Microservice**

bash
cd services/ai_ingestion
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
Ensure GROQ_API_KEY and GNEWS_API_KEY are configured in your environment variables
uvicorn main:app --port 8001 --reload
   
5. Initialize the Django Backend Server

Bash
cd ../../backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver


5. Launch the User Interface**

bash
cd ../frontend
npm install
npm run dev
   
Built by Shaik Firdos
