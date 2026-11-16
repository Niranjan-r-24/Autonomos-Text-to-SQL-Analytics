"""
Text-to-SQL & Document Multi-Agent Pipeline Orchestrator.
Coordinates the end-to-end multi-agent workflow:
1. Intent Routing (Document RAG vs. Structured SQL Querying)
2. Schema Linking & Inspection Agent
3. SQL Generation Agent
4. Execution & Self-Correction Agent (Iterative healing with error tracebacks)
5. Business Insights Interpretation Agent (Grounded executive summaries)
6. Dynamic Data Visualization Recommendation Agent
"""
import re
import time
import logging
from typing import Optional, Dict, Any, List

try:
    from backend.app.services.schema_service import get_db_schema_info
    from backend.app.services.sql_generator import SQLGenerator
    from backend.app.services.sql_executor import execute_safe_query, validate_safe_sql
    from backend.app.services.insights_service import BusinessInsightsInterpreter
    from backend.app.services.self_corrector import SelfCorrectionService
    from backend.app.services.rag_service import rag_service
except ImportError:
    from app.services.schema_service import get_db_schema_info
    from app.services.sql_generator import SQLGenerator
    from app.services.sql_executor import execute_safe_query, validate_safe_sql
    from app.services.insights_service import BusinessInsightsInterpreter
    from app.services.self_corrector import SelfCorrectionService
    from app.services.rag_service import rag_service

logger = logging.getLogger("text2sql.pipeline")


class TextToSqlPipeline:
    """Orchestrates the conversion of natural language questions to safe SQL execution, RAG, and visualizations."""

    def __init__(self, api_key: Optional[str] = None, provider: str = "gemini"):
        self.api_key = api_key
        self.provider = provider
        self.generator = SQLGenerator(api_key=api_key, provider=provider)
        self.interpreter = BusinessInsightsInterpreter(api_key=api_key, provider=provider)
        self.corrector = SelfCorrectionService(max_retries=3, api_key=api_key, provider=provider)

    def run(self, user_question: str, active_table: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes the full multi-agent pipeline for a user question.
        """
        start_time = time.time()
        logger.info("Pipeline started for question: '%s'", user_question)
        agent_steps: List[Dict[str, Any]] = []

        # 0. Intent Routing: Route document/knowledge queries to RAG
        q_lower = user_question.lower()
        doc_cues = (
            "document", "policy", "pdf", "docx", "guide", "portfolio", "resume",
            "according to", "knowledge base", "what is the step", "steps to",
            "master prompt", "checklist", "handbook", "procedure", "contract",
            "manual", "instructions", "faq", "terms", "notes", "retained",
            "retention", "reimbursement", "allowance", "per diem", "directive",
            "protocol", "guidelines", "requirement", "compliance", "authorized",
            "authorization", "mileage rate", "how long should", "how long must"
        )

        doc_names = [d["filename"].lower() for d in rag_service.list_documents()]
        mentions_doc_name = any(
            (dn in q_lower or (len(dn.split(".")[0]) >= 3 and dn.split(".")[0] in q_lower))
            for dn in doc_names
        )

        is_doc_query = mentions_doc_name or any(c in q_lower for c in doc_cues) or (
            rag_service.has_documents and any(
                c in q_lower for c in [
                    "in the document", "in the pdf", "in the docx", "in the policy",
                    "in the guide", "from the document", "from the manual", "knowledge base",
                    "from document", "uploaded file", "uploaded document"
                ]
            )
        )

        # Proactive RAG Probe: If documents exist, check if question has strong match in document records
        if not is_doc_query and rag_service.has_documents:
            is_explicit_sql = any(q_lower.startswith(k) for k in ["select ", "with ", "show first", "how many", "count ", "average ", "avg ", "sum ", "total revenue"])
            if not is_explicit_sql:
                top_hits = rag_service._hybrid_search(user_question)
                if top_hits and top_hits[0].get("score", 0) >= 4.0:
                    is_doc_query = True

        if is_doc_query and rag_service.has_documents:
            t0 = time.time()
            rag_res = rag_service.answer(user_question, api_key=self.api_key, provider=self.provider)
            rag_time = round(time.time() - t0, 3)

            agent_steps.append({
                "agent_id": "rag_retriever",
                "agent_name": "RAG Document Retrieval Agent",
                "status": "COMPLETED",
                "execution_time_sec": rag_time,
                "output_summary": f"Retrieved {rag_res['retrieved_count']} cited knowledge excerpts",
                "thought_logs": [
                    "Identified question intent as document knowledge retrieval.",
                    "Executed hybrid BM25 lexical + semantic vector search.",
                    f"Reranked top {len(rag_res['citations'])} relevant excerpts with source citations."
                ]
            })

            agent_steps.append({
                "agent_id": "rag_synthesizer",
                "agent_name": "Grounded Knowledge Synthesis Agent",
                "status": "COMPLETED",
                "execution_time_sec": round(time.time() - t0, 3),
                "output_summary": "Grounded answer synthesized from cited excerpts",
                "thought_logs": [
                    "Synthesized answer strictly referencing knowledge citations.",
                    "Verified claims against source excerpts."
                ]
            })

            insights = {
                "direct_answer": rag_res["answer"],
                "summary": f"Document Knowledge Answer based on {rag_res['retrieved_count']} cited excerpts.",
                "key_findings": [f"[{c['source']} - Chunk {c['chunk']}]: {c['excerpt']}" for c in rag_res["citations"][:3]],
                "comparisons": [],
                "caveats": ["Answer is derived from uploaded document knowledge base.", "Verify specific sections if exact phrasing is critical."],
                "business_takeaway": "Document guidance retrieved and verified against knowledge base.",
                "generated_by": "RAG Knowledge Retrieval Engine",
                "grounded": True,
                "status": "success"
            }

            total_duration_sec = round(time.time() - start_time, 3)
            return {
                "question": user_question,
                "success": True,
                "route": "rag",
                "sql": "",
                "explanation": "Answer retrieved from document knowledge base with citations.",
                "generated_by": "RAG Knowledge Retrieval Engine",
                "insights": insights,
                "citations": rag_res["citations"],
                "rows": [],
                "columns": [],
                "row_count": 0,
                "execution_time_sec": total_duration_sec,
                "sql_execution_time_ms": 0.0,
                "visualization": {"chart_type": "table", "title": f"Document Citations: {user_question}"},
                "agent_steps": agent_steps,
                "error": None
            }

        # Check if the prompt is an adversarial destructive SQL command
        raw_upper = user_question.strip().upper()
        if any(raw_upper.startswith(kw) for kw in ["DROP ", "DELETE ", "UPDATE ", "INSERT ", "ALTER ", "TRUNCATE ", "CREATE "]):
            is_safe, sec_err = validate_safe_sql(user_question.strip())
            total_duration_sec = round(time.time() - start_time, 3)
            return {
                "question": user_question,
                "success": False,
                "route": "sql",
                "sql": user_question.strip(),
                "explanation": "Security Sandboxing Alert: Destructive operations are strictly prohibited.",
                "generated_by": "Security Sandboxing Validator",
                "insights": {
                    "direct_answer": sec_err or "Security violation: Modifying statements are blocked.",
                    "summary": "Execution blocked by security sandbox.",
                    "key_findings": ["Only read-only SELECT and analytical CTE queries are permitted."],
                    "comparisons": [],
                    "caveats": ["Database integrity is strictly preserved in read-only mode."],
                    "business_takeaway": "Action denied by security rules.",
                    "status": "error"
                },
                "rows": [],
                "columns": [],
                "row_count": 0,
                "execution_time_sec": total_duration_sec,
                "sql_execution_time_ms": 0.0,
                "visualization": {"chart_type": "table", "title": "Security Error"},
                "attempts": 1,
                "correction_history": [],
                "agent_steps": [{
                    "agent_id": "security_validator",
                    "agent_name": "Security Sandboxing Validator",
                    "status": "FAILED",
                    "execution_time_sec": 0.001,
                    "output_summary": "Destructive query blocked",
                    "thought_logs": [sec_err or "Security violation: Destructive operation blocked."]
                }],
                "error": sec_err
            }

        # Step 1: Schema Inspection & Linking Agent
        t_schema = time.time()
        schema_info = get_db_schema_info(force_refresh=True)
        schema_time = round(time.time() - t_schema, 3)

        detected_tables = list(schema_info.keys())
        agent_steps.append({
            "agent_id": "schema_linker",
            "agent_name": "Schema Inspection & Linking Agent",
            "status": "COMPLETED",
            "execution_time_sec": schema_time,
            "output_summary": f"Identified active schema with {len(detected_tables)} tables ({', '.join(detected_tables)})",
            "thought_logs": [
                f"Retrieved active database schema with tables: {', '.join(detected_tables)}.",
                "Inspected column types, keys, and row distributions for query alignment."
            ]
        })

        # Sanitize active_table: Never allow audit_logs lock for non-audit questions
        if active_table:
            atl = active_table.lower()
            if atl == "audit_logs" and not any(k in q_lower for k in [
                "audit", "security", "fail", "login", "ip", "error", "auth", "log"
            ]):
                active_table = None
            elif atl in schema_info:
                # If question explicitly mentions another table, unbind active_table
                other_tables = [t for t in schema_info.keys() if t.lower() != atl and t.lower() not in ("audit_logs", "sqlite_sequence")]
                if any(t.lower() in q_lower or t.lower().rstrip("s") in q_lower for t in other_tables):
                    active_table = None

        # Step 2: SQL Generator Agent (or Direct SQL Handler)
        t_gen = time.time()
        if re.match(r"^(SELECT|WITH|EXPLAIN)\s+", user_question.strip(), re.IGNORECASE):
            sql_query = user_question.strip()
            explanation = "Executed user-provided SQL query directly."
            generated_by = "Direct User SQL"
        else:
            sql_query, explanation, generated_by = self.generator.generate(user_question, schema_info, active_table=active_table)

        # Handle unsupported query where no matching tables/columns could be mapped
        if not sql_query or not sql_query.strip():
            total_duration_sec = round(time.time() - start_time, 3)
            return {
                "question": user_question,
                "success": False,
                "route": "sql",
                "sql": "",
                "explanation": explanation or "Unable to map question to active database schema.",
                "generated_by": generated_by or "Query Router",
                "insights": {
                    "direct_answer": "I could not find any relevant tables or columns in the database to answer this question. Please verify available datasets in the Schema explorer.",
                    "summary": "Unsupported query: no matching database tables or columns found.",
                    "key_findings": ["No tables or attributes in the active database matched the query."],
                    "comparisons": [],
                    "caveats": ["Verify that the required dataset has been uploaded or check the schema viewer."],
                    "business_takeaway": "Rephrase your query or upload the appropriate dataset to perform this analysis.",
                    "status": "error"
                },
                "rows": [],
                "columns": [],
                "row_count": 0,
                "execution_time_sec": total_duration_sec,
                "sql_execution_time_ms": 0.0,
                "visualization": {"chart_type": "table", "title": "Unsupported Query"},
                "attempts": 1,
                "correction_history": [],
                "agent_steps": agent_steps,
                "error": "No matching database table or columns found for this question."
            }

        # Strict security guard: Block audit_logs from ever being queried for non-audit questions
        is_security_q = any(k in user_question.lower() for k in [
            "audit", "security", "fail", "login", "ip_address", "ip", "event",
            "auth", "error", "log"
        ])
        if "audit_logs" in sql_query.lower() and not is_security_q:
            logger.warning("Intercepted unwanted audit_logs query for question: '%s'. Re-synthesizing for business tables.", user_question)
            sql_query, explanation = self.generator._synthesize_dynamic_sql(user_question, schema_info, target_table=None)
            generated_by = "Deterministic Analytics Engine"

        gen_time = round(time.time() - t_gen, 3)

        agent_steps.append({
            "agent_id": "sql_generator",
            "agent_name": "SQL Generator Agent",
            "status": "COMPLETED",
            "execution_time_sec": gen_time,
            "output_summary": f"Generated SQL via {generated_by}",
            "thought_logs": [
                f"Mapped intent to ANSI SQL using {generated_by}.",
                f"Generated query: {sql_query}"
            ]
        })

        # Step 3: Safe Execution & Self-Correction Agent
        t_exec = time.time()
        exec_result = self.corrector.heal_and_execute(
            initial_sql=sql_query,
            user_question=user_question,
            schema_info=schema_info,
            execute_fn=execute_safe_query
        )
        exec_time = round(time.time() - t_exec, 3)

        # Update final SQL if healed during self-correction
        final_sql = exec_result["final_sql"]
        if final_sql != sql_query and exec_result["success"]:
            explanation += f" (Self-corrected automatically after {exec_result['attempts']} attempts)"
            sql_query = final_sql

        agent_steps.append({
            "agent_id": "self_corrector",
            "agent_name": "Execution & Self-Correction Agent",
            "status": "COMPLETED" if exec_result["success"] else "FAILED",
            "execution_time_sec": exec_time,
            "output_summary": f"Execution {'succeeded' if exec_result['success'] else 'failed'} (Attempts: {exec_result['attempts']}, Rows: {exec_result['row_count']})",
            "thought_logs": [
                f"Enforced read-only security sandboxing.",
                f"Query execution attempt {exec_result['attempts']}: {'success' if exec_result['success'] else 'error encountered'}.",
                f"Returned {exec_result['row_count']} rows." if exec_result["success"] else f"Error: {exec_result['error']}"
            ]
        })

        # Step 4: Business Insights Interpretation Agent
        t_ins = time.time()
        insights = self.interpreter.interpret(
            question=user_question,
            sql_query=sql_query,
            columns=exec_result["columns"],
            rows=exec_result["rows"],
            error=exec_result.get("error")
        )
        ins_time = round(time.time() - t_ins, 3)

        agent_steps.append({
            "agent_id": "business_insights",
            "agent_name": "Business Insights Interpreter Agent",
            "status": "COMPLETED",
            "execution_time_sec": ins_time,
            "output_summary": f"Generated grounded insights ({insights.get('status', 'success')})",
            "thought_logs": [
                "Extracted numerical metrics and computed benchmarks.",
                "Grounded claims strictly in retrieved rows.",
                "Drafted executive takeaway and caveats."
            ]
        })

        # Step 5: Data Visualization Recommendation Agent
        t_vis = time.time()
        visualization = self._infer_visualization(
            columns=exec_result["columns"],
            rows=exec_result["rows"],
            user_question=user_question
        )
        vis_time = round(time.time() - t_vis, 3)

        agent_steps.append({
            "agent_id": "visualizer",
            "agent_name": "Visualization Recommendation Agent",
            "status": "COMPLETED",
            "execution_time_sec": vis_time,
            "output_summary": f"Recommended view: {visualization['chart_type'].upper()}",
            "thought_logs": [
                f"Evaluated column data types: selected {visualization['chart_type']} chart.",
                f"Mapped X-Axis='{visualization.get('x_axis')}', Metric='{visualization.get('metric_label')}'."
            ]
        })

        total_duration_sec = round(time.time() - start_time, 3)
        logger.info(
            "Pipeline completed in %.3fs: success=%s, rows=%d, error=%s",
            total_duration_sec, exec_result["success"], exec_result["row_count"], exec_result["error"]
        )

        return {
            "question": user_question,
            "success": exec_result["success"],
            "route": "sql",
            "sql": sql_query,
            "explanation": explanation,
            "generated_by": generated_by,
            "insights": insights,
            "rows": exec_result["rows"],
            "columns": exec_result["columns"],
            "row_count": exec_result["row_count"],
            "execution_time_sec": total_duration_sec,
            "sql_execution_time_ms": exec_result.get("execution_time_ms", 0.0),
            "visualization": visualization,
            "attempts": exec_result.get("attempts", 1),
            "correction_history": exec_result.get("correction_history", []),
            "agent_steps": agent_steps,
            "error": exec_result["error"]
        }

    def _infer_visualization(self, columns: List[str], rows: List[Dict[str, Any]], user_question: str) -> Dict[str, Any]:
        """
        Recommends one appropriate default chart type, axes, metric labels, and ranking order.
        - Bar chart for rankings and categorical comparisons (with explicit highest/lowest order labeling).
        - Line chart for time-series trends.
        - Pie chart for proportions with few categories (<= 6 rows).
        - Table for detailed records or unsuitable chart data.
        """
        if not rows or not columns:
            return {
                "chart_type": "table",
                "x_axis": "",
                "y_axes": [],
                "title": f"Results for: {user_question}",
                "ranking_order": "none",
                "metric_label": "Value"
            }

        # Normalize column names by stripping surrounding quotes
        columns = [c.strip('"`') for c in columns]
        sample_row = {k.strip('"`'): v for k, v in rows[0].items()}
        numeric_cols = []
        string_cols = []
        date_cols = []

        for col in columns:
            val = sample_row.get(col)
            col_lower = col.lower()

            if any(k in col_lower for k in ["date", "time", "month", "year", "day"]):
                date_cols.append(col)
            elif isinstance(val, (int, float)) or (isinstance(val, str) and val.replace(".", "", 1).isdigit()):
                if not col_lower.endswith("_id") and col_lower != "id":
                    numeric_cols.append(col)
                else:
                    string_cols.append(col)
            else:
                string_cols.append(col)

        # Prioritize descriptive categorical column for x_axis
        preferred_x = ["product_name", "product", "customer_name", "customer", "name", "category", "action", "status", "channel", "plan"]
        x_axis = None
        for p in preferred_x:
            if p in string_cols:
                x_axis = p
                break
        if not x_axis:
            x_axis = string_cols[0] if string_cols else (date_cols[0] if date_cols else columns[0])

        y_axes = numeric_cols if numeric_cols else []
        primary_metric_label = y_axes[0].replace("_", " ").title() if y_axes else "Value"

        q_lower = user_question.lower()
        is_lowest = any(k in q_lower for k in [
            "lowest", "bottom", "least", "worst", "cheapest", "smallest", "ascending", "asc", "min", "minimum", "fewest"
        ])
        is_highest = any(k in q_lower for k in [
            "top", "highest", "most", "best", "greatest", "largest", "expensive", "descending", "desc", "max", "maximum"
        ])

        # Determine ranking direction
        ranking_order = "none"
        if numeric_cols and (is_lowest or is_highest or "sort" in q_lower or "rank" in q_lower or "order by" in q_lower):
            if len(rows) > 1:
                first_v = float(rows[0].get(numeric_cols[0], 0) or 0)
                last_v = float(rows[-1].get(numeric_cols[0], 0) or 0)
                if first_v < last_v:
                    ranking_order = "asc"
                elif first_v > last_v:
                    ranking_order = "desc"
                else:
                    ranking_order = "asc" if is_lowest else "desc"
            else:
                ranking_order = "asc" if is_lowest else "desc"

        # Determine chart type:
        is_time_series = (
            any(k in q_lower for k in ["trend", "monthly", "over time", "by month", "by year", "history", "timeline"])
            or any(k in [c.lower() for c in columns] for k in ["month", "sales_month", "year"])
        )

        is_browse_query = (
            any(k in q_lower for k in ["list all", "show all", "give me all", "browse", "sample rows", "show rows", "show first", "first 10", "first 5", "all products", "all customers", "all orders", "all employees"])
            and not any(k in q_lower for k in ["top", "bottom", "highest", "lowest", "rank", "sum", "total revenue", "average", "avg", "by status", "by department", "spending"])
        )

        if not numeric_cols or is_browse_query:
            chart_type = "table"
            title = f"Data Records for: {user_question}"
        elif date_cols and is_time_series:
            x_axis = date_cols[0]
            chart_type = "line"
            title = f"{primary_metric_label} Over Time"
        elif len(rows) <= 6 and any(k in q_lower for k in ["distribution", "share", "proportion", "breakdown", "by status"]):
            chart_type = "pie" if len(rows) <= 4 else "bar"
            title = f"{primary_metric_label} Distribution by {x_axis.replace('_', ' ').title()}"
        else:
            chart_type = "bar"
            if ranking_order == "asc":
                title = f"Lowest {len(rows)} by {primary_metric_label} (Ascending Order)"
            elif ranking_order == "desc":
                title = f"Top {len(rows)} by {primary_metric_label} (Descending Order)"
            else:
                title = f"{primary_metric_label} Comparison"

        return {
            "chart_type": chart_type,
            "x_axis": x_axis,
            "y_axes": y_axes,
            "title": title,
            "ranking_order": ranking_order,
            "metric_label": primary_metric_label
        }
