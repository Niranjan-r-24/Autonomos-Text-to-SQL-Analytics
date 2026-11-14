# Autonomous Text-to-SQL Analytics: Reproducible Evaluation Suite

This evaluation suite provides genuine, reproducible, execution-based metrics for the **Autonomous Text-to-SQL Analytics** platform.

All measurements are obtained through **execution-based correctness** (comparing actual result sets produced against verified gold-standard SQL executions on an isolated evaluation database), not superficial string matching.

---

## 📊 Summary of Verified Results

- **Evaluation Date**: 2026-10-24
- **Active Engine Evaluated**: Deterministic Offline Analytics Engine (Zero-Key Configuration)
- **Target Database**: Isolated SQLite Snapshot (`evaluation/data/eval_enterprise.db`)
- **Total Questions Attempted**: **35**
- **Valid Evaluation Cases**: **35**
- **Baseline Execution Accuracy**: **88.57%** (31 / 35)
- **Post-Correction Execution Accuracy**: **88.57%** (31 / 35)
- **Improvement via Self-Correction**: **0.0 percentage points** (*automated self-correction is not implemented in the current pipeline*)
- **SQL Execution Failure Rate**: **0.0%** (0 unhandled crashes or driver errors)
- **Security Sandboxing Adherence**: **100.0%** (4 / 4 destructive commands blocked)
- **Mean Response Latency**: **8.77 ms**
- **Median Response Latency**: **9.55 ms**
- **95th Percentile Latency**: **11.01 ms**

---

## 🔬 Key Architectural Findings

### 1. Actual vs. Claimed Pipeline Architecture
- **Natural-Language-to-SQL**: **Implemented**. Supports Google Gemini 1.5 Flash (via direct REST API), OpenAI GPT-4o-mini (via direct REST API), and a high-performance offline deterministic analytics engine.
- **AI-Generated Analytics**: **Implemented**. Uses `BusinessInsightsInterpreter` to generate executive summaries, metric grounding, and bullet findings.
- **Security Sandboxing**: **Implemented**. AST/regex keyword blocklist plus SQLite kernel-level read-only authorizer hook.
- **Query Self-Correction**: **NOT IMPLEMENTED IN BACKEND**.
  - The backend `TextToSqlPipeline` is a single-turn feedforward pipeline (`Generate -> Execute -> Interpret`).
  - No iterative repair loop exists in Python code to catch execution errors or empty results and prompt the generator to correct itself.
  - The frontend has an interactive manual SQL Studio (`SqlViewer.tsx`), which provides human-in-the-loop manual editing, but this is not autonomous agentic self-correction.
- **RAG Component**: **ORPHANED ARTIFACTS / NO PIPELINE**.
  - `backend/rag_store/` contains a Chroma SQLite database and `records.json` with 176 chunks from `AI_Portfolio_Guide.pdf`.
  - However, no Python or TypeScript file imports or queries this vector store. There is no active document retrieval endpoint or pipeline in the codebase.

---

## 🚀 Step-by-Step Reproduction Guide

To independently reproduce the evaluation results on any machine:

### 1. Prerequisites
Ensure Python 3.10+ and project dependencies are installed:
```bash
pip install -r backend/requirements.txt
```

### 2. Setup the Isolated Evaluation Database
Copies the enterprise database snapshot to `evaluation/data/eval_enterprise.db` ensuring zero mutations to production data:
```bash
python evaluation/scripts/setup_eval_db.py
```

### 3. Validate the Evaluation Dataset
Validates all 35 gold-standard queries against the isolated database:
```bash
python evaluation/scripts/build_dataset.py
```

### 4. Run the Evaluation Benchmark
Runs the evaluation harness, measuring execution accuracy, latencies, and comparison rules:
```bash
python evaluation/scripts/run_evaluation.py
```

### 5. (Optional) Run with External LLM Providers
If you have an API key and wish to benchmark Gemini or OpenAI:
```bash
# For Google Gemini
python evaluation/scripts/run_evaluation.py --provider gemini --api-key "YOUR_GEMINI_API_KEY"

# For OpenAI
python evaluation/scripts/run_evaluation.py --provider openai --api-key "YOUR_OPENAI_API_KEY"
```

---

## 📁 Artifacts Generated
- `evaluation/dataset/test_suite.json`: The 35 natural-language questions, gold SQL, primary metrics, and comparison rules.
- `evaluation/data/eval_enterprise.db`: The isolated SQLite test database.
- `evaluation/results/raw_results.json`: Full per-query execution trace, generated SQL, latency, and result match status.
- `evaluation/results/comparison_table.csv`: Tabular baseline vs post-correction results.
- `evaluation/results/metrics_summary.json`: Machine-readable summary metrics.
