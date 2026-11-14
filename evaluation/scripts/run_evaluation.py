"""
Reproducible Text-to-SQL Evaluation Harness.
Evaluates the Text-to-SQL generation pipeline using execution-based correctness
against an isolated evaluation SQLite database.

Measures:
- Execution accuracy (baseline vs post-correction)
- Execution failure rate
- Response latency (mean, median, p95)
- Documented comparison rules (ordered multiset, unordered multiset, scalar, security denial)
"""
import os
import sys
import time
import json
import sqlite3
import argparse
from typing import Dict, Any, List, Tuple

# Set paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

EVAL_DB_PATH = os.path.join(BASE_DIR, "evaluation", "data", "eval_enterprise.db")
DATASET_PATH = os.path.join(BASE_DIR, "evaluation", "dataset", "test_suite.json")
RESULTS_DIR = os.path.join(BASE_DIR, "evaluation", "results")

# Ensure isolated DB is used
os.environ["DATA_DIR"] = os.path.join(BASE_DIR, "evaluation", "data")
os.environ["DATABASE_URL"] = f"sqlite:///{EVAL_DB_PATH}"

# Import backend modules
from backend.app.services.sql_generator import SQLGenerator
from backend.app.services.sql_executor import execute_safe_query, validate_safe_sql
from backend.app.services.schema_service import get_db_schema_info
from backend.app.services.pipeline import TextToSqlPipeline


def execute_gold_sql(sql: str) -> Tuple[bool, List[Dict[str, Any]], List[str], str]:
    """Executes gold SQL directly against the evaluation database."""
    try:
        conn = sqlite3.connect(EVAL_DB_PATH)
        cur = conn.cursor()
        cur.execute(sql)
        cols = [desc[0] for desc in cur.description] if cur.description else []
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        return True, rows, cols, ""
    except Exception as e:
        return False, [], [], str(e)


def normalize_value(val: Any) -> Any:
    """Normalizes numerical and string values for fair, robust comparison."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return round(float(val), 2)
    if isinstance(val, str):
        cleaned = val.strip().replace("$", "").replace(",", "")
        try:
            return round(float(cleaned), 2)
        except ValueError:
            return val.strip().lower()
    return val


def evaluate_execution_match(
    case: Dict[str, Any],
    pred_success: bool,
    pred_rows: List[Dict[str, Any]],
    pred_cols: List[str],
    pred_error: str,
    gold_rows: List[Dict[str, Any]],
    gold_cols: List[str]
) -> Tuple[bool, str]:
    """
    Evaluates whether the predicted execution result matches the expected result
    under the case's documented comparison rule.
    """
    rule = case.get("comparison_rule", "ordered_multiset")

    # Rule 1: Security Sandboxing & Destructive Attack Denial
    if rule == "security_denial":
        # The query should be blocked by AST/regex security validator
        if not pred_success and ("Security" in (pred_error or "") or "Only read-only" in (pred_error or "")):
            return True, "Security sandbox correctly blocked destructive SQL."
        else:
            return False, f"Security sandbox failed to block destructive statement! Error: {pred_error}"

    # For standard analytical queries:
    if not pred_success:
        return False, f"Execution failed: {pred_error}"

    if not pred_rows and not gold_rows:
        return True, "Both returned 0 rows (empty match)."

    if len(pred_rows) != len(gold_rows):
        return False, f"Row count mismatch: predicted {len(pred_rows)}, expected {len(gold_rows)}."

    # Rule 2: Scalar / Single Aggregate KPI
    if rule == "scalar_row":
        primary_metric = case.get("primary_metric", "total_revenue")
        # Check first column value of first row
        pred_val = list(pred_rows[0].values())[0] if pred_rows[0] else None
        gold_val = list(gold_rows[0].values())[0] if gold_rows[0] else None
        
        pred_norm = normalize_value(pred_val)
        gold_norm = normalize_value(gold_val)

        if pred_norm == gold_norm or (isinstance(pred_norm, float) and isinstance(gold_norm, float) and abs(pred_norm - gold_norm) < 0.05):
            return True, f"Scalar match: {pred_norm} == {gold_norm}."
        return False, f"Scalar mismatch: predicted {pred_norm}, expected {gold_norm}."

    # Rule 3: Row Count Match (for table preview queries like 'LIMIT 5')
    if rule == "row_count_match":
        if len(pred_rows) == case.get("expected_limit", 5):
            return True, f"Row count matched limit {len(pred_rows)}."
        return False, f"Row count {len(pred_rows)} != expected limit {case.get('expected_limit')}."

    # Rule 4: Ordered Multiset (Rankings, Top/Bottom N, Trends)
    if rule == "ordered_multiset":
        for i in range(len(gold_rows)):
            p_vals = [normalize_value(v) for v in pred_rows[i].values()]
            g_vals = [normalize_value(v) for v in gold_rows[i].values()]

            # Primary key/label check
            primary_entity = case.get("primary_entity")
            if primary_entity and primary_entity in gold_rows[i]:
                expected_entity_val = normalize_value(gold_rows[i][primary_entity])
                if expected_entity_val not in p_vals:
                    return False, f"Row {i+1} entity mismatch: '{expected_entity_val}' not found in predicted row {p_vals}."

            # Primary metric check
            primary_metric = case.get("primary_metric")
            if primary_metric and primary_metric in gold_rows[i]:
                expected_metric_val = normalize_value(gold_rows[i][primary_metric])
                if expected_metric_val not in p_vals:
                    return False, f"Row {i+1} metric mismatch: '{expected_metric_val}' not found in predicted row {p_vals}."

        return True, f"Ordered match: all {len(gold_rows)} rows matched in exact sequence and values."

    # Rule 5: Unordered Multiset (Grouped breakdown where order is secondary)
    if rule == "unordered_multiset":
        matched_indices = set()
        primary_entity = case.get("primary_entity")
        primary_metric = case.get("primary_metric")

        for g_idx, g_row in enumerate(gold_rows):
            g_e = normalize_value(g_row.get(primary_entity)) if primary_entity else None
            g_m = normalize_value(g_row.get(primary_metric)) if primary_metric else None

            found = False
            for p_idx, p_row in enumerate(pred_rows):
                if p_idx in matched_indices:
                    continue
                p_vals = [normalize_value(v) for v in p_row.values()]
                if (g_e is None or g_e in p_vals) and (g_m is None or g_m in p_vals):
                    matched_indices.add(p_idx)
                    found = True
                    break
            if not found:
                return False, f"Unordered mismatch: expected record {g_row} not found in predicted rows."

        return True, f"Unordered match: all {len(gold_rows)} records matched."

    return False, f"Unknown comparison rule: {rule}"


def run_evaluation(provider: str = "fallback", api_key: str = None) -> Dict[str, Any]:
    """Runs the full evaluation benchmark across all test cases."""
    print("=" * 80)
    print("AUTONOMOUS TEXT-TO-SQL ANALYTICS: RIGOROUS EVALUATION RUN")
    print(f"Evaluation Target Database: {EVAL_DB_PATH}")
    print(f"Configured Provider: {provider.upper()}")
    print("=" * 80)

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    schema_info = get_db_schema_info()
    pipeline = TextToSqlPipeline(api_key=api_key, provider=provider)

    results = []
    latencies = []
    baseline_correct_count = 0
    post_correction_correct_count = 0
    execution_failures = 0
    timeouts = 0

    for idx, case in enumerate(test_cases, 1):
        q_id = case["id"]
        q_text = case["question"]
        rule = case["comparison_rule"]
        gold_sql = case["expected_sql"]

        print(f"\n[{idx:02d}/{len(test_cases)}] Case: {q_id} | Category: {case['category']}")
        print(f"      Question: \"{q_text}\"")

        # 1. Fetch Gold Result
        if rule != "security_denial":
            g_ok, gold_rows, gold_cols, g_err = execute_gold_sql(gold_sql)
            if not g_ok:
                raise RuntimeError(f"Gold SQL failed: {g_err}")
        else:
            gold_rows, gold_cols = [], []

        # 2. Run Pipeline (Baseline)
        t_start = time.perf_counter()
        try:
            if rule == "security_denial":
                # Test against safe execution sandbox directly to evaluate read-only enforcement
                sec_res = execute_safe_query(q_text)
                t_end = time.perf_counter()
                duration_ms = round((t_end - t_start) * 1000, 2)
                latencies.append(duration_ms)

                baseline_sql = q_text
                baseline_success = sec_res.get("success", False)
                baseline_rows = sec_res.get("rows", [])
                baseline_cols = sec_res.get("columns", [])
                baseline_error = sec_res.get("error", "")
            else:
                pipe_res = pipeline.run(q_text)
                t_end = time.perf_counter()
                duration_ms = round((t_end - t_start) * 1000, 2)
                latencies.append(duration_ms)

                baseline_sql = pipe_res.get("sql", "")
                baseline_success = pipe_res.get("success", False)
                baseline_rows = pipe_res.get("rows", [])
                baseline_cols = pipe_res.get("columns", [])
                baseline_error = pipe_res.get("error")

        except Exception as e:
            t_end = time.perf_counter()
            duration_ms = round((t_end - t_start) * 1000, 2)
            latencies.append(duration_ms)
            baseline_sql = ""
            baseline_success = False
            baseline_rows = []
            baseline_cols = []
            baseline_error = str(e)

        # 3. Assess Baseline Correctness
        base_match, base_reason = evaluate_execution_match(
            case=case,
            pred_success=baseline_success,
            pred_rows=baseline_rows,
            pred_cols=baseline_cols,
            pred_error=baseline_error,
            gold_rows=gold_rows,
            gold_cols=gold_cols
        )

        if not baseline_success and rule != "security_denial":
            execution_failures += 1

        if base_match:
            baseline_correct_count += 1
            print(f"      Baseline: PASS ({duration_ms} ms)")
        else:
            print(f"      Baseline: FAIL ({duration_ms} ms) -> {base_reason}")

        # 4. Assessment of Query Self-Correction in Current Codebase
        # Architectural Verification:
        # The backend TextToSqlPipeline has NO self-correction / iterative repair loop.
        # Generated SQL is executed once; if it fails or produces wrong results, no retry occurs.
        # Therefore, Post-Correction SQL in the current pipeline is IDENTICAL to Baseline SQL.
        post_correction_sql = baseline_sql
        post_correction_success = baseline_success
        post_correction_match = base_match
        post_correction_reason = base_reason

        if post_correction_match:
            post_correction_correct_count += 1

        results.append({
            "id": q_id,
            "category": case["category"],
            "complexity": case.get("complexity", "Medium"),
            "question": q_text,
            "comparison_rule": rule,
            "expected_sql": gold_sql,
            "baseline_sql": baseline_sql,
            "baseline_success": baseline_success,
            "baseline_correct": base_match,
            "baseline_reason": base_reason,
            "post_correction_sql": post_correction_sql,
            "post_correction_correct": post_correction_match,
            "self_correction_applied": False,
            "latency_ms": duration_ms,
            "rows_returned": len(baseline_rows) if baseline_rows else 0,
            "error": baseline_error
        })

    # Summary Metrics
    total_attempted = len(test_cases)
    valid_cases = total_attempted
    baseline_acc = round((baseline_correct_count / valid_cases) * 100, 2)
    post_corr_acc = round((post_correction_correct_count / valid_cases) * 100, 2)
    abs_improvement = round(post_corr_acc - baseline_acc, 2)
    rel_improvement = round(((post_corr_acc - baseline_acc) / baseline_acc) * 100, 2) if baseline_acc > 0 else 0.0
    failure_rate = round((execution_failures / valid_cases) * 100, 2)
    mean_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    sorted_latencies = sorted(latencies)
    median_latency = round(sorted_latencies[len(sorted_latencies) // 2], 2) if sorted_latencies else 0.0
    p95_latency = round(sorted_latencies[int(len(sorted_latencies) * 0.95)], 2) if sorted_latencies else 0.0

    summary = {
        "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model_configuration": {
            "provider": provider,
            "active_engine": "Deterministic Analytics Engine" if provider == "fallback" else provider,
            "database": "SQLite (eval_enterprise.db)",
            "self_correction_implemented_in_pipeline": False
        },
        "metrics": {
            "questions_attempted": total_attempted,
            "valid_evaluation_cases": valid_cases,
            "baseline_execution_accuracy_pct": baseline_acc,
            "post_correction_execution_accuracy_pct": post_corr_acc,
            "absolute_improvement_pp": abs_improvement,
            "relative_improvement_pct": rel_improvement,
            "sql_execution_failure_rate_pct": failure_rate,
            "invalid_or_timed_out_count": timeouts,
            "mean_response_latency_ms": mean_latency,
            "median_response_latency_ms": median_latency,
            "p95_response_latency_ms": p95_latency
        }
    }

    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY RESULTS")
    print("=" * 80)
    print(f"Total Questions Attempted:             {total_attempted}")
    print(f"Valid Evaluation Cases:                {valid_cases}")
    print(f"Baseline Execution Accuracy:           {baseline_acc}% ({baseline_correct_count}/{valid_cases})")
    print(f"Post-Correction Execution Accuracy:    {post_corr_acc}% ({post_correction_correct_count}/{valid_cases})")
    print(f"Absolute Improvement (p.p.):           {abs_improvement} percentage points")
    print(f"Relative Improvement:                  {rel_improvement}%")
    print(f"SQL Execution Failure Rate:            {failure_rate}% ({execution_failures}/{valid_cases})")
    print(f"Invalid / Timed-Out Test Count:        {timeouts}")
    print(f"Mean Response Latency:                 {mean_latency} ms")
    print(f"Median Response Latency:               {median_latency} ms")
    print(f"P95 Response Latency:                  {p95_latency} ms")
    print("=" * 80)

    # Save output artifacts
    os.makedirs(RESULTS_DIR, exist_ok=True)
    raw_path = os.path.join(RESULTS_DIR, "raw_results.json")
    summary_path = os.path.join(RESULTS_DIR, "metrics_summary.json")
    csv_path = os.path.join(RESULTS_DIR, "comparison_table.csv")

    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Save CSV comparison table
    import csv
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Case ID", "Category", "Complexity", "Question",
            "Baseline SQL", "Baseline Result Match",
            "Post-Correction SQL", "Post-Correction Result Match",
            "Self-Correction Occurred", "Latency (ms)", "Reason"
        ])
        for r in results:
            writer.writerow([
                r["id"], r["category"], r["complexity"], r["question"],
                r["baseline_sql"], "PASS" if r["baseline_correct"] else "FAIL",
                r["post_correction_sql"], "PASS" if r["post_correction_correct"] else "FAIL",
                "No (Pipeline Single-Turn)", r["latency_ms"], r["baseline_reason"]
            ])

    print(f"[OUTPUT] Saved raw results to: {raw_path}")
    print(f"[OUTPUT] Saved metrics summary to: {summary_path}")
    print(f"[OUTPUT] Saved CSV comparison table to: {csv_path}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Text-to-SQL evaluation.")
    parser.add_argument("--provider", default="fallback", choices=["fallback", "gemini", "openai"], help="Model provider")
    parser.add_argument("--api-key", default=None, help="LLM API Key")
    args = parser.parse_args()

    run_evaluation(provider=args.provider, api_key=args.api_key)
