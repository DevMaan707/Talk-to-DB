import streamlit as st
import pandas as pd
from urllib.parse import quote_plus
from llm_agent import (
    prepare_query,
    execute_sql_query,
    explain_results,
    validate_result_semantics,
    check_access,
    load_schema_context,
    detect_ambiguity,
    build_column_embeddings,
    retrieve_schema_context,
    build_query_evidence,
    resolve_temporal_context,
    score_sql_confidence,
)
from utils import log_query, check_schema_drift, save_feedback

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="Talk to DB (Groq)",
    page_icon="DB",
    layout="wide"
)

# --- Custom CSS for better UI ---
st.markdown("""
<style>
    .stTextInput>div>div>input {
        border-radius: 8px;
        padding: 8px;
    }
    .stButton>button {
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 600;
    }
    .success-box {
        padding: 15px;
        border: 1px solid #4CAF50;
        border-radius: 8px;
        background: #f0fff4;
        margin-bottom: 15px;
    }
    .warning-box {
        padding: 15px;
        border: 1px solid #ff9800;
        border-radius: 8px;
        background: #fff8e1;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- App Header ---
st.title("Talk to Database - Powered by Groq")
st.caption("Query your databases in plain English. No SQL required!")

# --- Role Selection ---
user_role = st.sidebar.selectbox("Your role", ["viewer", "analyst", "admin"])

# --- Session state ---
if "uri_generated" not in st.session_state:
    st.session_state.uri_generated = False
if "db_uri" not in st.session_state:
    st.session_state.db_uri = None
if "mode" not in st.session_state:
    st.session_state.mode = None
if "few_shot_examples" not in st.session_state:
    st.session_state.few_shot_examples = []
if "few_shot_saved" not in st.session_state:
    st.session_state.few_shot_saved = {}
if "ambiguity_questions" not in st.session_state:
    st.session_state.ambiguity_questions = []
if "ambiguity_query" not in st.session_state:
    st.session_state.ambiguity_query = None
if "ambiguity_resolved" not in st.session_state:
    st.session_state.ambiguity_resolved = False
if "ambiguity_resolved_query" not in st.session_state:
    st.session_state.ambiguity_resolved_query = None
if "embedding_store" not in st.session_state:
    st.session_state.embedding_store = None
if "embedding_db_uri" not in st.session_state:
    st.session_state.embedding_db_uri = None
if "confidence_cache" not in st.session_state:
    st.session_state.confidence_cache = {}
if "explanation_cache" not in st.session_state:
    st.session_state.explanation_cache = {}
if "validation_cache" not in st.session_state:
    st.session_state.validation_cache = {}
if "run_requested" not in st.session_state:
    st.session_state.run_requested = False
if "execute_requested" not in st.session_state:
    st.session_state.execute_requested = False
if "pending_execution" not in st.session_state:
    st.session_state.pending_execution = None
if "last_result" not in st.session_state:
    st.session_state.last_result = None

db_uri = None

# --- Step 1: Database Connection ---
if not st.session_state.uri_generated:
    st.subheader("Database Connection")

    st.session_state.mode = st.radio(
        "How would you like to connect?",
        ["Yes, I know the URI", "No, generate it for me"],
        horizontal=True
    )

    # --- Mode 1: User knows URI ---
    if st.session_state.mode.startswith("Yes"):
        db_type = st.selectbox("Database Type", ["PostgreSQL", "MySQL"], key="known_db_type")

        default_uri = (
            "postgresql+psycopg2://user:password@host:5432/dbname"
            if db_type == "PostgreSQL"
            else "mysql+pymysql://user:password@host:3306/dbname"
        )
        db_uri = st.text_input("Enter DB URI", placeholder=default_uri, key="known_uri", type="password")
        st.session_state.db_uri = db_uri

    # --- Mode 2: User does not know URI ---
    else:
        st.markdown("Fill in the details and we'll generate a secure URI for you:")

        db_type = st.selectbox("Database Type", ["PostgreSQL", "MySQL"], key="gen_db_type")

        col1, col2 = st.columns(2)
        with col1:
            host = st.text_input("Host", placeholder="localhost")
            username = st.text_input("Username", placeholder="user")
            dbname = st.text_input("Database Name", placeholder="mydatabase")
        with col2:
            port = st.text_input("Port", placeholder="5432" if db_type == "PostgreSQL" else "3306")
            password = st.text_input("Password", type="password")

        if st.button("Generate URI", use_container_width=True):
            if not (host and port and username and password and dbname):
                st.markdown('<div class="warning-box">Please fill all fields to generate URI.</div>', unsafe_allow_html=True)
            else:
                safe_password = quote_plus(password)
                db_uri = (
                    f"postgresql+psycopg2://{username}:{safe_password}@{host}:{port}/{dbname}"
                    if db_type == "PostgreSQL"
                    else f"mysql+pymysql://{username}:{safe_password}@{host}:{port}/{dbname}"
                )

                st.session_state.db_uri = db_uri
                st.session_state.uri_generated = True

# --- Show Generated URI + Back option ---
if st.session_state.uri_generated and st.session_state.db_uri:
    st.markdown('<div class="success-box">Connection URI Generated!</div>', unsafe_allow_html=True)
    st.code(st.session_state.db_uri, language="text")

    # Show Copy Button only if user selected "I know URI"
    if st.session_state.mode.startswith("Yes"):
        copy_script = f"""
        <button style="margin-top:8px;padding:6px 12px;font-size:14px;border-radius:6px;
        border:none;background-color:#4CAF50;color:white;cursor:pointer;"
        onclick="navigator.clipboard.writeText('{st.session_state.db_uri}').then(() => alert('Copied!'));">
             Copy URI
        </button>
        """
        st.markdown(copy_script, unsafe_allow_html=True)

    # Back Button
    if st.button("Back to Main Menu", use_container_width=True):
        st.session_state.uri_generated = False
        st.session_state.db_uri = None
        st.rerun()

# --- Step 2: Query Section ---
if st.session_state.db_uri:
    st.subheader("Ask Your Database")
    query = st.text_area("Type your question:", placeholder="e.g., Show me all products with stock greater than 50")

    # --- Helper to Display Results ---
    def display_result(question_text, result):
        st.markdown("### Query Results")

        if isinstance(result, tuple) and len(result) == 3:
            sql_query, rows, columns = result

            # Show SQL query
            st.markdown("**Generated SQL Query:**")
            st.code(sql_query, language="sql")

            # Show results table
            if isinstance(rows, list):
                df = pd.DataFrame(rows, columns=columns)
                row_height = 35
                table_height = min(800, max(200, len(df) * row_height))
                st.dataframe(df, use_container_width=True, height=table_height)

                # CSV download
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="results.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info(rows)

            # Expander for Explanation
            with st.expander("Explain Results", expanded=False):
                explanation_key = f"{question_text}|{sql_query}"
                if explanation_key not in st.session_state.explanation_cache:
                    with st.spinner("Analyzing results..."):
                        st.session_state.explanation_cache[explanation_key] = explain_results(
                            question_text,
                            sql_query,
                            rows,
                            columns,
                        )
                explanation = st.session_state.explanation_cache[explanation_key]
                st.markdown("### Explanation")
                st.markdown(
                    f"""
                    <div style="background:rgba(0,0,0,0);padding:15px;border-radius:10px;
                                border:1px solid #ddd;font-size:15px;line-height:1.6;color:white;">
                        {explanation}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        else:
            st.write(result)

    def render_evidence_panel(evidence: dict, expanded: bool = False):
        if not evidence:
            return

        summary = evidence.get("summary", {})
        with st.expander("Why this SQL?", expanded=expanded):
            st.caption(
                f"Grounded on {summary.get('column_count', 0)} columns across "
                f"{summary.get('table_count', 0)} tables."
            )

            if evidence.get("tables"):
                st.markdown("**Tables considered**")
                st.write(", ".join(evidence["tables"]))

            if evidence.get("columns"):
                st.markdown("**Retrieved columns**")
                for item in evidence["columns"]:
                    st.write(f"- {item['ref']} ({item['column_type']}): {item['reason']}")

            if evidence.get("relationships"):
                st.markdown("**Join evidence**")
                for item in evidence["relationships"]:
                    st.write(f"- {item['ref']}: {item['reason']}")

            if evidence.get("temporal"):
                st.markdown("**Temporal bounds used**")
                for item in evidence["temporal"]:
                    st.write(f"- {item['ref']}: {item['min']} to {item['max']}")

    # --- Run Query Button ---
    run_clicked = st.button("Run Query", type="primary", use_container_width=True)
    if run_clicked:
        st.session_state.run_requested = True

    if st.session_state.run_requested:
        if not query:
            st.markdown('<div class="warning-box">Please enter a query.</div>', unsafe_allow_html=True)
            st.session_state.run_requested = False
        else:
            allowed, reason = check_access(query, user_role)
            if not allowed:
                st.error(f"Access denied: {reason}")
                st.session_state.run_requested = False
                st.stop()

            with st.spinner("Generating SQL preview..."):
                try:
                    engine, schema_columns, relationships = load_schema_context(st.session_state.db_uri)
                    drifted, drift_msg = check_schema_drift(schema_columns)
                    if drifted:
                        st.warning(drift_msg)

                    if (st.session_state.embedding_store is None) or (st.session_state.embedding_db_uri != st.session_state.db_uri):
                        embed_store, embed_err = build_column_embeddings(
                            engine,
                            schema_columns,
                            relationships=relationships,
                            persist=True,
                            db_uri=st.session_state.db_uri,
                        )
                        st.session_state.embedding_store = embed_store
                        st.session_state.embedding_db_uri = st.session_state.db_uri
                        if embed_err:
                            st.warning(embed_err)

                    relevant_columns = None
                    relevant_relationships = relationships
                    if st.session_state.embedding_store:
                        schema_context = retrieve_schema_context(
                            query,
                            st.session_state.embedding_store,
                            schema_columns,
                            relationships,
                            top_k=8,
                            related_limit=4,
                        )
                        relevant_columns = schema_context.get("columns") or None
                        relevant_relationships = schema_context.get("relationships") or relationships

                    schema_for_prompt = relevant_columns if relevant_columns else schema_columns
                    # Skip ambiguity detection - let LLM handle it directly
                    # if not (st.session_state.ambiguity_resolved and st.session_state.ambiguity_query == query):
                    #     ambiguity_questions = detect_ambiguity(query, schema_for_prompt)
                    #     if ambiguity_questions:
                    #         st.session_state.run_requested = False
                    #         st.session_state.ambiguity_questions = ambiguity_questions
                    #         st.session_state.ambiguity_query = query
                    #         st.session_state.ambiguity_resolved = False
                    #         st.warning("This question seems ambiguous. Please clarify.")
                    #         for q in ambiguity_questions:
                    #             st.write(q)
                    #         clarification = st.text_input("Clarification", key="ambiguity_clarification")
                    #         if st.button("Use clarification") and clarification:
                    #             st.session_state.ambiguity_resolved = True
                    #             st.session_state.ambiguity_resolved_query = f"{query}. Clarification: {clarification}"
                    #             st.session_state.run_requested = True
                    #             st.rerun()
                    #         st.stop()

                    effective_query = query
                    if st.session_state.ambiguity_resolved and st.session_state.ambiguity_query == query:
                        effective_query = st.session_state.ambiguity_resolved_query

                    temporal_context = resolve_temporal_context(engine, schema_columns)
                    evidence = build_query_evidence(
                        effective_query,
                        schema_columns,
                        relevant_columns=schema_for_prompt,
                        relationships=relevant_relationships,
                        temporal_context=temporal_context,
                    )

                    sql_query = prepare_query(
                        st.session_state.db_uri,
                        effective_query,
                        engine=engine,
                        schema_columns=schema_columns,
                        relationships=relevant_relationships,
                        few_shot_examples=st.session_state.few_shot_examples,
                        relevant_columns=relevant_columns,
                    )

                    st.session_state.pending_execution = {
                        "db_uri": st.session_state.db_uri,
                        "question": effective_query,
                        "sql_query": sql_query,
                        "schema_columns": schema_columns,
                        "schema_for_prompt": schema_for_prompt,
                        "evidence": evidence,
                    }
                    st.session_state.execute_requested = False
                    st.session_state.run_requested = False

                except Exception as e:
                    st.session_state.run_requested = False
                    st.session_state.pending_execution = None
                    st.error(f"Error: {e}")

    pending = st.session_state.pending_execution
    if pending and pending.get("db_uri") == st.session_state.db_uri:
        st.markdown("### Query Preview")
        st.caption("Review the generated SQL before execution.")
        st.code(pending["sql_query"], language="sql")
        render_evidence_panel(pending.get("evidence"), expanded=True)

        preview_col1, preview_col2 = st.columns(2)
        with preview_col1:
            if st.button("Approve and Execute", type="primary", use_container_width=True):
                st.session_state.execute_requested = True
                st.rerun()
        with preview_col2:
            if st.button("Cancel Preview", use_container_width=True):
                st.session_state.pending_execution = None
                st.session_state.execute_requested = False
                st.rerun()

    if st.session_state.execute_requested and st.session_state.pending_execution:
        pending = st.session_state.pending_execution
        with st.spinner("Executing approved SQL..."):
            try:
                engine, _, _ = load_schema_context(pending["db_uri"])
                rows, columns = execute_sql_query(
                    pending["sql_query"],
                    engine,
                    question=pending["question"],
                    schema_columns=pending["schema_columns"],
                )
                result = (pending["sql_query"], rows, columns)
                log_query(pending["db_uri"], pending["question"], result)
                st.session_state.last_result = {
                    "db_uri": pending["db_uri"],
                    "question": pending["question"],
                    "sql_query": pending["sql_query"],
                    "rows": rows,
                    "columns": list(columns),
                    "schema_columns": pending["schema_columns"],
                    "schema_for_prompt": pending["schema_for_prompt"],
                    "evidence": pending.get("evidence"),
                }

                st.session_state.ambiguity_questions = []
                st.session_state.ambiguity_query = None
                st.session_state.ambiguity_resolved = False
                st.session_state.ambiguity_resolved_query = None
                st.session_state.pending_execution = None
                st.session_state.execute_requested = False

            except Exception as e:
                st.session_state.execute_requested = False
                st.error(f"Error: {e}")

    last_result = st.session_state.last_result
    if last_result and last_result.get("db_uri") == st.session_state.db_uri:
        result = (
            last_result["sql_query"],
            last_result["rows"],
            last_result["columns"],
        )
        display_result(last_result["question"], result)
        render_evidence_panel(last_result.get("evidence"))

        confidence_key = f"{last_result['question']}|{last_result['sql_query']}"
        if confidence_key not in st.session_state.confidence_cache:
            st.session_state.confidence_cache[confidence_key] = score_sql_confidence(
                last_result["question"],
                last_result["sql_query"],
                last_result["schema_for_prompt"]
            )
        conf = st.session_state.confidence_cache[confidence_key]
        level = conf.get("level", "medium")
        score = conf.get("score", 5)
        reason_text = conf.get("reason", "")

        if level == "high":
            st.success(f"Confidence: HIGH ({score}/10). {reason_text}")
        elif level == "low":
            st.error(f"Confidence: LOW ({score}/10). {reason_text}")
        else:
            st.warning(f"Confidence: MEDIUM ({score}/10). {reason_text}")

        if isinstance(last_result["rows"], list) and last_result["columns"]:
            validation_key = f"{last_result['question']}|{last_result['sql_query']}"
            if validation_key not in st.session_state.validation_cache:
                st.session_state.validation_cache[validation_key] = validate_result_semantics(
                    last_result["question"],
                    last_result["sql_query"],
                    last_result["rows"],
                    last_result["columns"],
                )
            validation = st.session_state.validation_cache[validation_key]
            if (not validation.get("valid")) or validation.get("confidence") == "low":
                warning = validation.get("warning") or "Result may not match the question."
                st.warning(warning)
                with st.expander("Why?"):
                    st.write(validation.get("reason"))

        with st.expander("Was this result correct?"):
            feedback = st.radio("", ["Yes", "No"], horizontal=True, key="result_feedback")
            if feedback == "Yes":
                example_key = f"{last_result['question']}|{last_result['sql_query']}"
                if example_key not in st.session_state.few_shot_saved:
                    st.session_state.few_shot_examples.append({
                        "question": last_result["question"],
                        "sql": last_result["sql_query"]
                    })
                    st.session_state.few_shot_examples = st.session_state.few_shot_examples[-3:]
                    st.session_state.few_shot_saved[example_key] = True
                    st.success("Saved as in-session example.")

            if feedback == "No":
                correction = st.text_input(
                    "What should it have returned / what was wrong?",
                    key="result_correction",
                )
                if st.button("Submit Feedback", key="result_feedback_submit") and correction:
                    save_feedback(
                        last_result["question"],
                        last_result["sql_query"],
                        correction,
                        last_result["schema_columns"],
                    )
                    st.success("Thanks! This will improve future queries.")


