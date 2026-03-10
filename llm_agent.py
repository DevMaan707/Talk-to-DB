import os
import re
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine, text, inspect
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from utils import load_annotations

load_dotenv()

_LLM = None


def get_llm():
    global _LLM
    if _LLM is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        _LLM = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0
        )
    return _LLM

ROLE_PERMISSIONS = {
    "admin": ["aggregation", "lookup", "comparison", "sensitive", "financial"],
    "analyst": ["aggregation", "lookup", "comparison", "financial"],
    "viewer": ["aggregation", "lookup"],
}

SENSITIVE_KEYWORDS = ["salary", "salaries", "password", "ssn", "email", "emails", "phone", "phones", "secret", "token", "credit"]
FINANCIAL_KEYWORDS = ["revenue", "profit", "cost", "budget", "invoice", "payment"]

DIALECT_RULES = {
    "mysql": {
        "limit_syntax": "LIMIT n",
        "current_time": "NOW()",
        "string_concat": "CONCAT(a, b)",
        "top_n": "Use LIMIT at end, not TOP",
        "notes": "Use backticks for reserved word column names."
    },
    "postgresql": {
        "limit_syntax": "LIMIT n",
        "current_time": "NOW() or CURRENT_TIMESTAMP",
        "string_concat": "a || b",
        "top_n": "Use LIMIT at end, not TOP",
        "notes": "Use double quotes for case-sensitive identifiers."
    },
    "sqlite": {
        "limit_syntax": "LIMIT n",
        "current_time": "datetime('now')",
        "string_concat": "a || b",
        "top_n": "Use LIMIT",
        "notes": "No native boolean type; use 0/1."
    },
    "mssql": {
        "limit_syntax": "TOP n (before column list)",
        "current_time": "GETDATE()",
        "string_concat": "a + b",
        "top_n": "Use TOP n in SELECT, not LIMIT",
        "notes": "Use square brackets for reserved word column names."
    }
}

_EMBED_MODEL = None


def detect_dialect(db_uri: str) -> str:
    """Infers SQL dialect from connection string."""
    uri = db_uri.lower()
    if "mysql" in uri:
        return "mysql"
    if "postgresql" in uri or "postgres" in uri:
        return "postgresql"
    if "sqlite" in uri:
        return "sqlite"
    if "mssql" in uri or "sqlserver" in uri:
        return "mssql"
    return "mysql"


def get_dialect_prompt_snippet(db_uri: str) -> str:
    dialect = detect_dialect(db_uri)
    rules = DIALECT_RULES[dialect]
    return (
        f"Database dialect: {dialect.upper()}\n"
        "Syntax rules:\n"
        f"- Pagination: {rules['limit_syntax']}\n"
        f"- Current time: {rules['current_time']}\n"
        f"- String concat: {rules['string_concat']}\n"
        f"- Top N rows: {rules['top_n']}\n"
        f"- Note: {rules['notes']}"
    )


def get_schema_columns(engine) -> list[dict]:
    inspector = inspect(engine)
    schema_columns = []
    for table_name in inspector.get_table_names():
        for col in inspector.get_columns(table_name):
            schema_columns.append({
                "table_name": table_name,
                "column_name": col.get("name"),
                "column_type": str(col.get("type")) if col.get("type") is not None else ""
            })
    return schema_columns


def load_schema(db_uri: str):
    engine = create_engine(db_uri)
    schema_columns = get_schema_columns(engine)
    return engine, schema_columns


def format_schema(schema_columns: list[dict], max_columns: int = 200) -> str:
    cols = schema_columns[:max_columns] if schema_columns else []
    return "\n".join(
        f"- {c['table_name']}.{c['column_name']} ({c.get('column_type', '')})".rstrip()
        for c in cols
    )


def resolve_temporal_context(engine, schema_columns: list[dict]) -> dict:
    """
    Finds date/time columns, queries their MIN/MAX from DB,
    returns a dict to inject into the LLM prompt.
    """
    temporal_context = {}
    date_keywords = ["date", "time", "created", "updated", "timestamp", "year", "month"]

    date_cols = [
        col for col in schema_columns
        if any(kw in col["column_name"].lower() for kw in date_keywords)
    ]

    with engine.connect() as conn:
        for col in date_cols:
            try:
                result = conn.execute(text(
                    f"SELECT MIN({col['column_name']}), MAX({col['column_name']}) "
                    f"FROM {col['table_name']}"
                ))
                min_val, max_val = result.fetchone()
                temporal_context[f"{col['table_name']}.{col['column_name']}"] = {
                    "min": str(min_val),
                    "max": str(max_val)
                }
            except Exception:
                continue

    return temporal_context


def format_few_shot(examples: list[dict] | None) -> str:
    if not examples:
        return "None"
    lines = []
    for ex in examples[-3:]:
        q = ex.get("question", "")
        s = ex.get("sql", "")
        lines.append(f"Q: {q}\nSQL: {s}")
    return "\n\n".join(lines)


def build_prompt(question, db_uri, schema_columns, engine, few_shot_examples=None, relevant_columns=None):
    schema_for_prompt = relevant_columns if relevant_columns else schema_columns
    schema_str = format_schema(schema_for_prompt)

    dialect_block = get_dialect_prompt_snippet(db_uri)
    temporal_block = resolve_temporal_context(engine, schema_columns)
    annotations = load_annotations(schema_columns)
    few_shot = format_few_shot(few_shot_examples)

    temporal_str = "\n".join(
        f"- {col}: {v['min']} to {v['max']}"
        for col, v in temporal_block.items()
    ) if temporal_block else "None"

    annotations_str = annotations if annotations else "None"

    return f"""
{dialect_block}

Schema:
{schema_str}

Temporal data bounds (use to interpret 'recent', 'last month', etc.):
{temporal_str}

Past correction hints (learn from these):
{annotations_str}

Verified past queries (use as examples):
{few_shot}

Generate a single valid SQL SELECT query for:
"{question}"

Return ONLY the SQL, no explanation.
"""


def generate_sql_from_question(question: str, db_uri: str, schema_columns: list[dict], engine, few_shot_examples=None, relevant_columns=None) -> str:
    """Generate a strict SQL query from natural language question using LLM directly"""
    prompt = build_prompt(question, db_uri, schema_columns, engine, few_shot_examples, relevant_columns)

    response = get_llm().invoke(prompt)
    raw_output = response.content.strip()

    raw_output = re.sub(r"```sql|```", "", raw_output)
    raw_output = re.sub(r"<think>.*?</think>", "", raw_output, flags=re.DOTALL).strip()

    sql_match = re.findall(
        r"(SELECT .*?;)",
        raw_output,
        flags=re.DOTALL | re.IGNORECASE
    )
    sql_query = sql_match[-1].strip() if sql_match else raw_output.strip()

    if not re.search(r"\blimit\b|\btop\b|\bfirst\b", question, re.IGNORECASE):
        sql_query = re.sub(r"\s+LIMIT\s+\d+", "", sql_query, flags=re.IGNORECASE).strip()

    if not sql_query.endswith(";"):
        sql_query += ";"

    blocked = ["insert", "update", "delete", "drop", "alter", "truncate"]
    if any(sql_query.lower().strip().startswith(w) for w in blocked):
        raise ValueError("Only SELECT queries are permitted.")

    if not sql_query.upper().startswith("SELECT"):
        raise ValueError(f"Invalid SQL generated: {sql_query}")

    return sql_query


def python_to_sql_literal(val):
    """Convert Python value to SQL-safe literal"""
    if isinstance(val, str):
        return f"'{val}'"
    if isinstance(val, (int, float, Decimal)):
        return str(val)
    if isinstance(val, date):
        return f"'{val.isoformat()}'"
    raise ValueError(f"Unsupported type {type(val)}")


def get_column_samples(engine, table_name: str, column_name: str, limit: int = 3) -> list[str]:
    samples = []
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                f"SELECT {column_name} FROM {table_name} WHERE {column_name} IS NOT NULL LIMIT {limit}"
            ))
            for row in result.fetchall():
                samples.append(str(row[0]))
    except Exception:
        return []
    return samples


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _EMBED_MODEL = SentenceTransformer(model_name)
    return _EMBED_MODEL


def build_column_embeddings(engine, schema_columns: list[dict], model_name: str = "all-MiniLM-L6-v2", sample_limit: int = 3):
    try:
        import numpy as np
        import faiss
    except Exception as e:
        return None, f"Embedding dependencies not available: {e}"

    if not schema_columns:
        return None, "No schema columns available for embeddings."

    model = get_embedding_model(model_name)
    texts = []
    columns = []

    for col in schema_columns:
        samples = get_column_samples(engine, col["table_name"], col["column_name"], limit=sample_limit)
        sample_text = ", ".join(samples) if samples else "none"
        text_blob = f"{col['table_name']}.{col['column_name']} ({col.get('column_type','')}). Samples: {sample_text}"
        texts.append(text_blob)
        columns.append(col)

    embeddings = model.encode(texts, normalize_embeddings=True)
    embeddings = embeddings.astype("float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    return {
        "index": index,
        "columns": columns,
        "texts": texts,
        "model_name": model_name
    }, None


def retrieve_relevant_columns(question: str, embed_store, top_k: int = 8) -> list[dict]:
    if not embed_store:
        return []

    try:
        import numpy as np
    except Exception:
        return []

    model = get_embedding_model(embed_store.get("model_name", "all-MiniLM-L6-v2"))
    q_vec = model.encode([question], normalize_embeddings=True).astype("float32")
    scores, idx = embed_store["index"].search(q_vec, top_k)
    picked = []
    for i in idx[0]:
        if i < 0:
            continue
        picked.append(embed_store["columns"][i])
    return picked


def detect_ambiguity(question: str, schema_columns: list[dict]) -> list[str]:
    schema_str = format_schema(schema_columns, max_columns=120)
    prompt = f"""
You are a SQL assistant. Determine if the user question is ambiguous given the schema.

Schema:
{schema_str}

Question: "{question}"

If the question is ambiguous or missing a required choice, propose 1-2 short clarifying questions.
Reply ONLY in JSON:
{{
  "ambiguous": true or false,
  "questions": ["q1", "q2"]
}}
"""

    response = get_llm().invoke(prompt)
    try:
        import json
        import re as _re
        raw = response.content
        json_str = _re.search(r"\{.*\}", raw, _re.DOTALL).group()
        data = json.loads(json_str)
        if data.get("ambiguous"):
            return data.get("questions", [])[:2]
    except Exception:
        return []
    return []


def score_sql_confidence(question: str, sql: str, schema_columns: list[dict]) -> dict:
    schema_str = format_schema(schema_columns, max_columns=120)
    prompt = f"""
You are a SQL reviewer. Rate how confident you are (1-10) that the SQL answers the question given the schema.

Schema:
{schema_str}

Question: "{question}"
SQL: {sql}

Reply ONLY in JSON:
{{
  "score": 1-10,
  "reason": "one short sentence"
}}
"""

    response = get_llm().invoke(prompt)
    score = 5
    reason = ""
    try:
        import json
        import re as _re
        raw = response.content
        json_str = _re.search(r"\{.*\}", raw, _re.DOTALL).group()
        data = json.loads(json_str)
        score = int(data.get("score", 5))
        reason = data.get("reason", "")
    except Exception:
        reason = "Confidence parsing failed."

    if score >= 8:
        level = "high"
    elif score >= 5:
        level = "medium"
    else:
        level = "low"

    return {"score": score, "level": level, "reason": reason}


def run_query(db_uri: str, question: str, engine=None, schema_columns=None, few_shot_examples=None, relevant_columns=None):
    """Convert question -> SQL -> Execute SQL safely and return results + SQL"""
    if engine is None:
        engine = create_engine(db_uri)
    if schema_columns is None:
        schema_columns = get_schema_columns(engine)

    sql_query = generate_sql_from_question(
        question,
        db_uri,
        schema_columns,
        engine,
        few_shot_examples=few_shot_examples,
        relevant_columns=relevant_columns,
    )

    with engine.connect() as conn:
        result = conn.execute(text(sql_query))
        rows = result.fetchall()
        columns = result.keys()

    return sql_query, rows, columns


def validate_result_semantics(question: str, sql: str, rows: list, columns: list) -> dict:
    """
    Asks LLM if the returned result makes sense for the question.
    Returns {"valid": bool, "warning": str | None, "reason": str, "confidence": str}
    """
    if not rows:
        return {"valid": True, "warning": None, "reason": "Empty result may be expected.", "confidence": "medium"}

    preview = rows[:5]
    preview_str = "\n".join([str(dict(zip(columns, row))) for row in preview])

    validation_prompt = f"""You are a result validator for a database query system.

User question: "{question}"
Generated SQL: {sql}
Result preview (first 5 rows):
{preview_str}

Does this result seem like a plausible, correct answer to the user's question?
Reply ONLY in this JSON format:
{{
  "valid": true or false,
  "confidence": "high" or "medium" or "low",
  "warning": "one sentence warning if something looks wrong, else null",
  "reason": "one sentence explanation"
}}"""

    response = get_llm().invoke(validation_prompt)

    try:
        import json
        import re as _re
        raw = response.content
        json_str = _re.search(r"\{.*\}", raw, _re.DOTALL).group()
        data = json.loads(json_str)
        if "confidence" not in data:
            data["confidence"] = "medium"
        if "warning" not in data:
            data["warning"] = None
        if "reason" not in data:
            data["reason"] = ""
        if "valid" not in data:
            data["valid"] = True
        return data
    except Exception:
        return {"valid": True, "warning": None, "reason": "Validation parse failed.", "confidence": "medium"}


def classify_query_intent(question: str) -> list[str]:
    """Returns list of intent tags for a question."""
    q = question.lower()
    intents = []

    if any(w in q for w in ["average", "sum", "count", "total", "max", "min", "group"]):
        intents.append("aggregation")
    if any(w in q for w in ["show", "list", "find", "get", "fetch", "display"]):
        intents.append("lookup")
    if any(w in q for w in ["compare", "difference", "versus", "vs", "more than", "less than"]):
        intents.append("comparison")
    if any(w in q for w in SENSITIVE_KEYWORDS):
        intents.append("sensitive")
    if any(w in q for w in FINANCIAL_KEYWORDS):
        intents.append("financial")

    if "aggregation" in intents and "lookup" not in intents:
        intents.append("lookup")

    return intents or ["lookup"]


def check_access(question: str, user_role: str) -> tuple[bool, str]:
    """
    Returns (allowed: bool, reason: str)
    """
    intents = classify_query_intent(question)
    allowed_intents = ROLE_PERMISSIONS.get(user_role, ["lookup"])

    blocked = [i for i in intents if i not in allowed_intents]
    if blocked:
        return False, f"Your role '{user_role}' cannot run queries involving: {', '.join(blocked)}"
    return True, "Access granted"


def explain_results(question: str, sql_query: str, rows, columns):
    """Generate a clear explanation of SQL results using LLM"""
    if isinstance(rows, list) and columns:
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

    response = get_llm().invoke(prompt)
    return response.content.strip()



