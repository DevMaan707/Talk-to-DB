import streamlit as st
import pandas as pd
from urllib.parse import quote_plus
from llm_agent import (
    run_query,
    explain_results,
    validate_result_semantics,
    check_access,
    load_schema,
    detect_ambiguity,
    build_column_embeddings,
    retrieve_relevant_columns,
    score_sql_confidence,
)
from utils import log_query, check_schema_drift, save_feedback

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="Talk to DB (Nebius)",
    page_icon="ðŸ’¬",
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
st.title("ðŸ’¬ Talk to Database â€” Powered by Nebius")
st.caption("Query your databases in plain English. No SQL required! ðŸš€")

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

db_uri = None

# --- Step 1: Database Connection ---
if not st.session_state.uri_generated:
    st.subheader("ðŸ”— Database Connection")

    st.session_state.mode = st.radio(
        "How would you like to connect?",
        ["âœ… Yes, I know the URI", "â“ No, generate it for me"],
        horizontal=True
    )

    # --- Mode 1: User knows URI ---
    if st.session_state.mode.startswith("âœ…"):
        db_type = st.selectbox("Database Type", ["PostgreSQL", "MySQL"], key="known_db_type")

        default_uri = (
            "postgresql+psycopg2://user:password@host:5432/dbname"
            if db_type == "PostgreSQL"
            else "mysql+pymysql://user:password@host:3306/dbname"
        )
        db_uri = st.text_input("Enter DB URI", placeholder=default_uri, key="known_uri", type="password")
        st.session_state.db_uri = db_uri

    # --- Mode 2: User doesnâ€™t know URI ---
    else:
        st.markdown("ðŸ‘‰ Fill in the details and we'll generate a secure URI for you:")

        db_type = st.selectbox("Database Type", ["PostgreSQL", "MySQL"], key="gen_db_type")

        col1, col2 = st.columns(2)
        with col1:
            host = st.text_input("Host", placeholder="localhost")
            username = st.text_input("Username", placeholder="user")
            dbname = st.text_input("Database Name", placeholder="mydatabase")
        with col2:
            port = st.text_input("Port", placeholder="5432" if db_type == "PostgreSQL" else "3306")
            password = st.text_input("Password", type="password")

        if st.button("ðŸ”‘ Generate URI", use_container_width=True):
            if not (host and port and username and password and dbname):
                st.markdown('<div class="warning-box">âš ï¸ Please fill all fields to generate URI.</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="success-box">âœ… Connection URI Generated!</div>', unsafe_allow_html=True)
    st.code(st.session_state.db_uri, language="text")

    # Show Copy Button only if user selected "I know URI"
    if st.session_state.mode.startswith("âœ…"):
        copy_script = f"""
        <button style="margin-top:8px;padding:6px 12px;font-size:14px;border-radius:6px;
        border:none;background-color:#4CAF50;color:white;cursor:pointer;"
        onclick="navigator.clipboard.writeText('{st.session_state.db_uri}').then(() => alert('âœ… Copied!'));">
            ðŸ“‹ Copy URI
        </button>
        """
        st.markdown(copy_script, unsafe_allow_html=True)

    # Back Button
    if st.button("â¬…ï¸ Back to Main Menu", use_container_width=True):
        st.session_state.uri_generated = False
        st.session_state.db_uri = None
        st.rerun()

# --- Step 2: Query Section ---
if st.session_state.db_uri:
    st.subheader("ðŸ’¬ Ask Your Database")
    query = st.text_area("Type your question:", placeholder="e.g., Show me all products with stock greater than 50")

    # --- Helper to Display Results ---
    def display_result(question_text, result):
        st.markdown("### ðŸ“Š Query Results")

        if isinstance(result, tuple) and len(result) == 3:
            sql_query, rows, columns = result

            # Show SQL query
            st.markdown("**ðŸ“ Generated SQL Query:**")
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
                    label="ðŸ“¥ Download CSV",
                    data=csv,
                    file_name="results.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info(rows)

            # Expander for Explanation
            with st.expander("ðŸ“ Explain Results", expanded=False):
                with st.spinner("âœ¨ Analyzing results..."):
                    explanation = explain_results(question_text, sql_query, rows, columns)
                    st.markdown("### âœ¨ Explanation")
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

    # --- Run Query Button ---
    if st.button("ðŸš€ Run Query", type="primary", use_container_width=True):
        if not query:
            st.markdown('<div class="warning-box">âš ï¸ Please enter a query.</div>', unsafe_allow_html=True)
        else:
            allowed, reason = check_access(query, user_role)
            if not allowed:
                st.error(f"Access denied: {reason}")
                st.stop()

            with st.spinner("ðŸ”Ž Generating SQL & fetching results..."):
                try:
                    engine, schema_columns = load_schema(st.session_state.db_uri)
                    drifted, drift_msg = check_schema_drift(schema_columns)
                    if drifted:
                        st.warning(drift_msg)

                    # Build / reuse column embeddings
                    if (st.session_state.embedding_store is None) or (st.session_state.embedding_db_uri != st.session_state.db_uri):
                        embed_store, embed_err = build_column_embeddings(engine, schema_columns)
                        st.session_state.embedding_store = embed_store
                        st.session_state.embedding_db_uri = st.session_state.db_uri
                        if embed_err:
                            st.warning(embed_err)

                    relevant_columns = None
                    if st.session_state.embedding_store:
                        relevant_columns = retrieve_relevant_columns(query, st.session_state.embedding_store, top_k=8)

                    schema_for_prompt = relevant_columns if relevant_columns else schema_columns

                    # Ambiguity check before running
                    if not (st.session_state.ambiguity_resolved and st.session_state.ambiguity_query == query):
                        ambiguity_questions = detect_ambiguity(query, schema_for_prompt)
                        if ambiguity_questions:
                            st.session_state.ambiguity_questions = ambiguity_questions
                            st.session_state.ambiguity_query = query
                            st.session_state.ambiguity_resolved = False
                            st.warning("This question seems ambiguous. Please clarify.")
                            for q in ambiguity_questions:
                                st.write(q)
                            clarification = st.text_input("Clarification", key="ambiguity_clarification")
                            if st.button("Use clarification") and clarification:
                                st.session_state.ambiguity_resolved = True
                                st.session_state.ambiguity_resolved_query = f"{query}. Clarification: {clarification}"
                                st.rerun()
                            st.stop()

                    effective_query = query
                    if st.session_state.ambiguity_resolved and st.session_state.ambiguity_query == query:
                        effective_query = st.session_state.ambiguity_resolved_query

                    result = run_query(
                        st.session_state.db_uri,
                        effective_query,
                        engine=engine,
                        schema_columns=schema_columns,
                        few_shot_examples=st.session_state.few_shot_examples,
                        relevant_columns=relevant_columns,
                    )
                    display_result(effective_query, result)
                    log_query(st.session_state.db_uri, effective_query, result)

                    if isinstance(result, tuple) and len(result) == 3:
                        sql_query, rows, columns = result

                        # Confidence score
                        confidence_key = f"{effective_query}|{sql_query}"
                        if confidence_key not in st.session_state.confidence_cache:
                            st.session_state.confidence_cache[confidence_key] = score_sql_confidence(
                                effective_query,
                                sql_query,
                                schema_for_prompt
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

                        # Semantic result validation
                        if isinstance(rows, list) and columns:
                            validation = validate_result_semantics(effective_query, sql_query, rows, columns)
                            if (not validation.get("valid")) or validation.get("confidence") == "low":
                                warning = validation.get("warning") or "Result may not match the question."
                                st.warning(warning)
                                with st.expander("Why?"):
                                    st.write(validation.get("reason"))

                        # Feedback loop + in-session few-shot memory
                        with st.expander("Was this result correct?"):
                            feedback = st.radio("", ["Yes", "No"], horizontal=True)
                            if feedback == "Yes":
                                example_key = f"{effective_query}|{sql_query}"
                                if example_key not in st.session_state.few_shot_saved:
                                    st.session_state.few_shot_examples.append({
                                        "question": effective_query,
                                        "sql": sql_query
                                    })
                                    st.session_state.few_shot_examples = st.session_state.few_shot_examples[-3:]
                                    st.session_state.few_shot_saved[example_key] = True
                                    st.success("Saved as in-session example.")

                            if feedback == "No":
                                correction = st.text_input("What should it have returned / what was wrong?")
                                if st.button("Submit Feedback") and correction:
                                    save_feedback(effective_query, sql_query, correction, schema_columns)
                                    st.success("Thanks! This will improve future queries.")

                    # Clear ambiguity state after a successful run
                    st.session_state.ambiguity_questions = []
                    st.session_state.ambiguity_query = None
                    st.session_state.ambiguity_resolved = False
                    st.session_state.ambiguity_resolved_query = None

                except Exception as e:
                    st.error(f"Error: {e}")
