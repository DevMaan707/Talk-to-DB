import streamlit as st
import pandas as pd
from urllib.parse import quote_plus
from llm_agent import run_query, explain_results
from utils import log_query

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="Talk to DB (Nebius)",
    page_icon="💬",
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
st.title("💬 Talk to Database — Powered by Nebius")
st.caption("Query your databases in plain English. No SQL required! 🚀")

# --- Session state ---
if "uri_generated" not in st.session_state:
    st.session_state.uri_generated = False
if "db_uri" not in st.session_state:
    st.session_state.db_uri = None
if "mode" not in st.session_state:
    st.session_state.mode = None

db_uri = None

# --- Step 1: Database Connection ---
if not st.session_state.uri_generated:
    st.subheader("🔗 Database Connection")

    st.session_state.mode = st.radio(
        "How would you like to connect?",
        ["✅ Yes, I know the URI", "❓ No, generate it for me"],
        horizontal=True
    )

    # --- Mode 1: User knows URI ---
    if st.session_state.mode.startswith("✅"):
        db_type = st.selectbox("Database Type", ["PostgreSQL", "MySQL"], key="known_db_type")

        default_uri = (
            "postgresql+psycopg2://user:password@host:5432/dbname"
            if db_type == "PostgreSQL"
            else "mysql+pymysql://user:password@host:3306/dbname"
        )
        db_uri = st.text_input("Enter DB URI", placeholder=default_uri, key="known_uri",type="password")
        st.session_state.db_uri = db_uri

    # --- Mode 2: User doesn’t know URI ---
    else:
        st.markdown("👉 Fill in the details and we'll generate a secure URI for you:")

        db_type = st.selectbox("Database Type", ["PostgreSQL", "MySQL"], key="gen_db_type")

        col1, col2 = st.columns(2)
        with col1:
            host = st.text_input("Host", placeholder="localhost")
            username = st.text_input("Username", placeholder="user")
            dbname = st.text_input("Database Name", placeholder="mydatabase")
        with col2:
            port = st.text_input("Port", placeholder="5432" if db_type == "PostgreSQL" else "3306")
            password = st.text_input("Password", type="password")

        if st.button("🔑 Generate URI", use_container_width=True):
            if not (host and port and username and password and dbname):
                st.markdown('<div class="warning-box">⚠️ Please fill all fields to generate URI.</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="success-box">✅ Connection URI Generated!</div>', unsafe_allow_html=True)
    st.code(st.session_state.db_uri, language="text")

    # Show Copy Button only if user selected "I know URI"
    if st.session_state.mode.startswith("✅"):
        copy_script = f"""
        <button style="margin-top:8px;padding:6px 12px;font-size:14px;border-radius:6px;
        border:none;background-color:#4CAF50;color:white;cursor:pointer;"
        onclick="navigator.clipboard.writeText('{st.session_state.db_uri}').then(() => alert('✅ Copied!'));">
            📋 Copy URI
        </button>
        """
        st.markdown(copy_script, unsafe_allow_html=True)

    # Back Button
    if st.button("⬅️ Back to Main Menu", use_container_width=True):
        st.session_state.uri_generated = False
        st.session_state.db_uri = None
        st.rerun()

# --- Step 2: Query Section ---
if st.session_state.db_uri and st.session_state.mode.startswith("✅"):
    st.subheader("💬 Ask Your Database")
    query = st.text_area("Type your question:", placeholder="e.g., Show me all products with stock greater than 50")

    # --- Helper to Display Results ---
    def display_result(query, result):
        st.markdown("### 📊 Query Results")

        if isinstance(result, tuple) and len(result) == 3:
            sql_query, rows, columns = result

            # Show SQL query
            st.markdown("**📝 Generated SQL Query:**")
            st.code(sql_query, language="sql")

            # Show results table
            df = pd.DataFrame(rows, columns=columns)
            row_height = 35
            table_height = min(800, max(200, len(df) * row_height))
            st.dataframe(df, use_container_width=True, height=table_height)

            # CSV download
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name="results.csv",
                mime="text/csv",
                use_container_width=True
            )

            # ✅ Expander for Explanation
            with st.expander("📝 Explain Results", expanded=False):
                with st.spinner("✨ Analyzing results..."):
                    from llm_agent import explain_results  # import inside to avoid circular issues
                    explanation = explain_results(query, sql_query, rows, columns)
                    st.markdown("### ✨ Explanation")
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
    if st.button("🚀 Run Query", type="primary", use_container_width=True):
        if not query:
            st.markdown('<div class="warning-box">⚠️ Please enter a query.</div>', unsafe_allow_html=True)
        else:
            with st.spinner("🔎 Generating SQL & fetching results..."):
                try:
                    result = run_query(st.session_state.db_uri, query)
                    display_result(query, result)  # pass query for explanation
                    log_query(st.session_state.db_uri, query, result)
                except Exception as e:
                    st.error(f"❌ Error: {e}")
