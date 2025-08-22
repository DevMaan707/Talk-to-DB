import os
import re
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine, text
from langchain_nebius import ChatNebius
from dotenv import load_dotenv 

load_dotenv() 
# 🔹 Set API key
os.environ["NEBIUS_API_KEY"] = os.getenv("NEBIUS_API_KEY")
if not os.environ["NEBIUS_API_KEY"]:
    raise ValueError("NEBIUS_API_KEY not found in environment variables")

# 🔹 Setup LLM
llm = ChatNebius(
    model="Qwen/Qwen3-235B-A22B-Instruct-2507",  # ✅ Good model for SQL generation
    temperature=0
)

def generate_sql_from_question(question: str) -> str:
    """Generate a strict SQL query from natural language question using LLM directly"""
    prompt = f"""
    You are an expert SQL assistant.
    - Output ONLY a valid SQL query.
    - NO explanations, NO reasoning, NO comments, NO markdown.
    - The query MUST start with SELECT, INSERT, UPDATE, or DELETE.
    - Do NOT include LIMIT clauses unless explicitly asked.
    Question: {question}
    """

    # ✅ Call LLM directly
    response = llm.invoke(prompt)
    raw_output = response.content.strip()

    # ✅ Remove unwanted tags or markdown
    raw_output = re.sub(r"```sql|```", "", raw_output)
    raw_output = re.sub(r"<think>.*?</think>", "", raw_output, flags=re.DOTALL).strip()

    # ✅ Extract only SQL
    sql_match = re.findall(
        r"(SELECT .*?;|UPDATE .*?;|INSERT .*?;|DELETE .*?;)",
        raw_output,
        flags=re.DOTALL | re.IGNORECASE
    )
    sql_query = sql_match[-1].strip() if sql_match else raw_output.strip()

    # ✅ Remove LIMIT if any (optional rule)
    sql_query = re.sub(r"\s+LIMIT\s+\d+", "", sql_query, flags=re.IGNORECASE).strip()

    # ✅ Ensure query ends with semicolon
    if not sql_query.endswith(";"):
        sql_query += ";"

    # ✅ Validate query
    if not sql_query.upper().startswith(("SELECT", "INSERT", "UPDATE", "DELETE")):
        raise ValueError(f"Invalid SQL generated: {sql_query}")

    return sql_query

def python_to_sql_literal(val):
    """Convert Python value to SQL-safe literal"""
    if isinstance(val, str):
        return f"'{val}'"
    elif isinstance(val, (int, float, Decimal)):
        return str(val)
    elif isinstance(val, date):
        return f"'{val.isoformat()}'"
    else:
        raise ValueError(f"Unsupported type {type(val)}")

def run_query(db_uri: str, question: str):
    """Convert question -> SQL -> Execute SQL safely and return results + SQL"""
    engine = create_engine(db_uri)
    sql_query = generate_sql_from_question(question)

    with engine.connect() as conn:
        upper_sql = sql_query.strip().upper()

        if upper_sql.startswith("SELECT"):
            result = conn.execute(text(sql_query))
            rows = result.fetchall()
            columns = result.keys()
        else:
            result = conn.execute(text(sql_query))
            rows = f"{result.rowcount} rows affected"
            columns = []

    return sql_query, rows, columns


def explain_results(question: str, sql_query: str, rows, columns):
    """Generate a clear explanation of SQL results using LLM"""
    if isinstance(rows, list) and columns:
        # Convert first few rows to dict for readability
        data_preview = [dict(zip(columns, row)) for row in rows[:10]]
    else:
        data_preview = rows

    prompt = f"""
    You are a helpful SQL analyst.
    Question: {question}
    SQL Query: {sql_query}
    Results Preview: {data_preview}

    Provide a clear and structured explanation of what the results mean.
    - Summarize key findings
    - Mention patterns, insights, or anomalies
    - Avoid repeating raw values only
    """

    response = llm.invoke(prompt)
    return response.content.strip()