# Autonomos — AI-Powered Text-to-SQL Analytics Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14.2+-black.svg?style=flat&logo=next.js&logoColor=white)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?style=flat&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3+-3178C6.svg?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC.svg?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Recharts](https://img.shields.io/badge/Recharts-2.12-22c55e.svg?style=flat)](https://recharts.org)

Autonomos is an enterprise AI-powered Text-to-SQL analytics platform built from the ground up with a schema-first query pipeline, strict read-only execution safeguards, dynamic CSV dataset ingestion, independent document RAG intelligence, and automatic charting.

---

## 🌟 Key Architecture & Capabilities

### 1. 🧠 Schema-First Text-to-SQL Engine
- **Strict Schema Grounding**: Introspects live database tables, columns, data types, and foreign key relationships before generating any query.
- **Zero Hallucination Rules**: Never selects default or hallucinated tables. Never queries `audit_logs` unless explicitly requested.
- **Multi-Provider Support**:
  - **Google Gemini API** (`gemini-1.5-flash` / `gemini-2.0-flash`)
  - **OpenAI API** (`gpt-4o-mini` / `gpt-4o`)
  - **Schema-Grounded Deterministic Engine**: Built-in zero-cost offline engine that functions without external API keys.
- **Dynamic Ambiguity Detection**: Flags questions referring to missing entities and prompts for clarification.

### 2. 🛡️ SQL Safety & Validation Sandboxing
- **Strict Read-Only Enforcement**: Executes only single `SELECT` or `WITH ... SELECT` queries.
- **Destructive Mutation Blocker**: Blocks `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, `REPLACE`, `GRANT`, `PRAGMA`.
- **Injection Protection**: Disallows multi-statement semicolon chaining.
- **Table Verification**: Validates all referenced tables against active database tables.
- **Automatic Limit Safeguard**: Automatically caps unbounded queries to `MAX_QUERY_LIMIT` (default 1,000).

### 3. 📁 Dynamic CSV Dataset Management
- **Universal CSV Ingestion**: Upload any CSV dataset with automatic encoding detection.
- **Intelligent Type Inference**: Automatically infers `INTEGER`, `REAL`, `DATE`, `DATETIME`, and `TEXT` column types.
- **Zero-Stale Schema Cache**: Invalidates and refreshes schema metadata immediately upon upload.

### 4. 📊 Grounded Insights & Recharts Visualization
- **Natural Language Summaries**: Generates plain-English answers strictly from returned database rows.
- **Smart Chart Recommendation**: Evaluates data shape and cardinality to render:
  - **Bar Charts**: Categorical comparisons and metrics.
  - **Line Charts**: Time-series and date trends.
  - **Pie Charts**: Small category proportions.
  - **Data Table**: Paginated, sortable tabular data.

### 5. 📚 Independent RAG Document Intelligence
- **Strictly Decoupled**: Document uploading and indexing never interfere with SQL table selection.
- **Lexical BM25 / TF-IDF Retrieval**: Splits documents into passages and ranks relevant excerpts.
- **Grounded Citations**: Returns synthesis with source filenames, chunk IDs, and relevance scores.

---

## 🏛️ Benchmark Enterprise Dataset

The platform includes a built-in benchmark relational schema:
- **`customers`** (12 rows): `id`, `name`, `email`, `country`, `signup_date`
- **`products`** (8 rows): `id`, `name`, `category`, `price`, `stock`
- **`orders`** (30 rows): `id`, `customer_id`, `order_date`, `status`, `total_amount`
- **`order_items`** (30 rows): `id`, `order_id`, `product_id`, `quantity`, `unit_price`
- **`audit_logs`** (10 rows): `id`, `action`, `user_id`, `timestamp`, `details`

### Verified Benchmark Questions
1. `How many customers are in the database?` → **12**
2. `Show the first 10 products.` → **8 rows**
3. `Show all orders.` → **30 rows**
4. `Count orders by status.` → **completed: 20, shipped: 5, pending: 3, cancelled: 2**
5. `Which product generated the highest revenue?` → **Developer Workstation ($41,600.00)**
6. `Show monthly revenue.` → **Chronological monthly aggregation (Jan - Oct 2024)**
7. `Show audit logs.` → **audit_logs queried strictly when requested**
8. `Ask about a nonexistent table.` → **Clear error / clarification requested**

---

## 🚀 Quickstart & Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1. Backend Setup
```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Run backend API server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
API docs available at: `http://localhost:8000/docs`  
Health check: `http://localhost:8000/health`

### 2. Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 🧪 Automated Testing

### Run Backend Pytest Suite
```bash
python -m pytest backend/tests -v
```
All 24 automated tests verify benchmark questions, schema inspection, CSV uploads, SQL safety, and RAG independence.

### Run Frontend Contract Tests & Build
```bash
cd frontend
npm test
npm run build
```

---

## 🚢 Deployment Guide

### Backend: Render.com
1. Create a **Web Service** on [Render](https://render.com).
2. Root directory: `.`
3. Build command: `pip install -r backend/requirements.txt`
4. Start command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
5. Health check path: `/health`
6. Environment Variables:
   - `PYTHON_VERSION`: `3.11.9`
   - `GEMINI_API_KEY`: *(Optional)*
   - `OPENAI_API_KEY`: *(Optional)*
   - `DATABASE_URL`: `sqlite:///autonomos.db` or PostgreSQL connection string

### Frontend: Vercel
1. Import repository to [Vercel](https://vercel.com).
2. Framework preset: **Next.js**
3. Root directory: `frontend`
4. Environment Variables:
   - `NEXT_PUBLIC_API_URL`: Your Render backend URL (e.g. `https://autonomos-text2sql-api.onrender.com`)

### Database: SQLite vs PostgreSQL
- **SQLite (Default)**: Zero configuration, fast local file-based storage.
- **PostgreSQL**: Set `DATABASE_URL=postgresql://user:password@host:5432/dbname`. SQLAlchemy handles pooling and dialect abstraction automatically.

---

## 📄 License
MIT License.
