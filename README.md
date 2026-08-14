# Enterprise Autonomous Text-to-SQL Analytics Platform 🚀

A production-ready Enterprise Text-to-SQL Analytics Platform built with Next.js 14 (App Router), Tailwind CSS, Framer Motion, Recharts, Python (FastAPI), SQLAlchemy, and a 4-stage Autonomous Multi-Agent AI Pipeline (Schema Linker, SQL Generator, Self-Corrector, and Data Visualizer).

---

## 🌟 Key Features

1. **Dark Obsidian & Glassmorphism Executive UI**:
   - Deep-space background (`#0B0F17`) with glowing neon accents (`#6366F1`, `#10B981`, `#A855F7`).
   - Agent Status Visualizer Sidebar tracking Schema Matcher, SQL Generator, Self-Corrector, and Data Visualizer.
   - Interactive Natural Language Search Canvas with pre-loaded enterprise prompt chips.

2. **Autonomous Multi-Agent Pipeline**:
   - 🧠 **Schema Linking Agent**: Filters schema down to relevant tables & columns matching user intent.
   - ⚙️ **SQL Generator Agent**: Formulates standard ANSI SQL with JOINs, aggregations, and column aliasing.
   - 🩹 **Execution & Self-Correction Agent**: Executes SQL against database, catches error tracebacks, and automatically self-heals up to 3 times.
   - 📊 **Visualization Agent**: Analyzes return column shapes to select optimal chart type (`bar`, `line`, `pie`, `area`, `table`).

3. **Enterprise Sample Schema & Data**:
   - Pre-seeded 4 interconnected database tables: `sales`, `customers`, `products`, `audit_logs`.
   - Supports zero-config SQLite out-of-the-box and PostgreSQL via SQLAlchemy.

4. **Real-time Thought Stream & Exporters**:
   - Real-time step-by-step agent execution timeline.
   - SQL Code viewer with copy-to-clipboard & live SQL edit/re-run mode.
   - One-click **CSV** and **JSON** data export buttons.

---

## 🏗️ Architecture Stack

- **Frontend**: Next.js 14 (App Router), React 18, Tailwind CSS, Lucide Icons, Recharts, Framer Motion.
- **Backend**: Python (FastAPI), Uvicorn, SQLAlchemy, LangChain / Gemini / OpenAI integration.
- **Database**: SQLite (default local zero-config) / PostgreSQL compatibility.

---

## 🚀 Quick Setup & Run Instructions

### 1. Backend Setup (FastAPI)

```bash
# Navigate to project root
cd "Autonomos Text-to-SQL Analytics"

# Install Python dependencies
pip install -r backend/requirements.txt

# Seed the enterprise database (Creates enterprise_analytics.db)
python -m backend.app.db.seed

# Start FastAPI Backend Server (Runs on http://localhost:8000)
uvicorn backend.app.main:app --reload --port 8000
```

### 2. Frontend Setup (Next.js 14)

Open a new terminal window:

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies (if not already installed)
npm install

# Start Next.js Development Server (Runs on http://localhost:3000)
npm run dev
```

Open your browser at [http://localhost:3000](http://localhost:3000) to access the platform!

### Deploy on Render

The repository includes a [`render.yaml`](render.yaml) Blueprint that deploys the FastAPI API and Next.js web application together. In Render, select **New +** → **Blueprint**, connect this GitHub repository, and deploy the detected Blueprint.

The API uses a paid Starter instance because SQLite uploads and the knowledge base are stored on a 1 GB persistent disk. Set `GEMINI_API_KEY` and/or `OPENAI_API_KEY` in the API service's Environment settings if you want server-side keys; the deterministic engine works without either key.

---

## 🔑 LLM API Key Configuration (Optional)

The platform supports **Google Gemini API** (`GEMINI_API_KEY`) and **OpenAI API** (`OPENAI_API_KEY`). 

- Click **"Configure API Key"** in the top navigation header to enter your API key directly in the UI.
- If no key is provided, the platform automatically utilizes its high-precision **Deterministic Analytics Engine** for instant out-of-the-box query execution!

---

## 📁 Repository Structure

```
Autonomos Text-to-SQL Analytics/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── schema_linker.py   # Schema Linking Agent
│   │   │   ├── sql_generator.py   # SQL Generator Agent
│   │   │   ├── self_corrector.py  # Execution & Self-Correction Agent (3x auto-heal)
│   │   │   ├── visualizer.py      # Dynamic Visualization Agent
│   │   │   └── pipeline.py        # Multi-Agent Pipeline Coordinator
│   │   ├── db/
│   │   │   ├── database.py        # SQLAlchemy & DB Metadata Inspector
│   │   │   └── seed.py            # Enterprise Sample Data Seeder (Sales, Customers, Products, Logs)
│   │   └── main.py                # FastAPI Web Server
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx         # Root Layout
│   │   │   ├── page.tsx           # Main Analytics Dashboard
│   │   │   └── globals.css        # Glassmorphism & Obsidian Dark Styles
│   │   └── components/
│   │       ├── Header.tsx         # Executive Navbar & API Key Modal
│   │       ├── Sidebar.tsx        # Agent Status Visualizers
│   │       ├── QueryInput.tsx     # Search Bar Canvas & Quick Prompts
│   │       ├── AgentThoughtStream.tsx # Real-time Agent Step Timeline
│   │       ├── SqlViewer.tsx      # SQL Code Box with Copy & Edit
│   │       ├── DataVisualization.tsx  # Dynamic Recharts & Data Table
│   │       └── SchemaViewerModal.tsx  # Enterprise Database Explorer
│   ├── tailwind.config.js
│   └── package.json
└── README.md
```
