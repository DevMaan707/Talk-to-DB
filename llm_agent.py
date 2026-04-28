import os
import re
import json
import hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from utils import load_annotations

load_dotenv()

_LLM = None
EMBEDDING_CACHE_DIR = Path(".schema_embedding_cache")
SQL_KEYWORDS = {
    "select", "from", "where", "join", "left", "right", "inner", "outer", "full",
    "cross", "on", "group", "by", "order", "having", "limit", "offset", "as",
    "distinct", "and", "or", "not", "in", "is", "null", "like", "between", "case",
    "when", "then", "else", "end", "union", "all", "asc", "desc", "true", "false",
    "current_date", "current_timestamp", "interval", "over", "partition", "rows",
    "range", "preceding", "following", "with"
}
SQL_FUNCTIONS = {
    "count", "sum", "avg", "min", "max", "round", "coalesce", "lower", "upper",
    "date_trunc", "extract", "cast", "concat", "now", "current_timestamp",
    "datetime", "getdate", "abs", "distinct"
}
EVIDENCE_STOPWORDS = {
    "show", "list", "find", "get", "fetch", "display", "give", "me", "all", "the",
    "a", "an", "of", "for", "to", "by", "and", "or", "with", "from", "in", "on",
    "into", "want", "see", "data", "details", "table", "tables"
}


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
SCHEMA_INFO_TERMS = ["schema", "column", "columns", "field", "fields", "structure", "metadata"]
TABLE_LISTING_TERMS = ["show tables", "list tables", "all tables", "what tables", "which tables"]
FORBIDDEN_METADATA_IDENTIFIERS = {"tablename", "columnname"}


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


def get_schema_relationships(engine) -> list[dict]:
    inspector = inspect(engine)
    relationships = []
    for table_name in inspector.get_table_names():
        for fk in inspector.get_foreign_keys(table_name):
            local_columns = fk.get("constrained_columns") or []
            remote_columns = fk.get("referred_columns") or []
            remote_table = fk.get("referred_table")
            fk_name = fk.get("name") or f"{table_name}_fk"

            for local_col, remote_col in zip(local_columns, remote_columns):
                relationships.append({
                    "name": fk_name,
                    "source_table": table_name,
                    "source_column": local_col,
                    "target_table": remote_table,
                    "target_column": remote_col,
                })
    return relationships


def load_schema(db_uri: str):
    engine = create_engine(db_uri)
    schema_columns = get_schema_columns(engine)
    return engine, schema_columns


def load_schema_context(db_uri: str):
    engine = create_engine(db_uri)
    schema_columns = get_schema_columns(engine)
    relationships = get_schema_relationships(engine)
    return engine, schema_columns, relationships


def format_schema(schema_columns: list[dict], max_columns: int = 200) -> str:
    cols = schema_columns[:max_columns] if schema_columns else []
    return "\n".join(
        f"- {c['table_name']}.{c['column_name']} ({c.get('column_type', '')})".rstrip()
        for c in cols
    )


def format_relationships(relationships: list[dict] | None, max_relationships: int = 50) -> str:
    if not relationships:
        return "None"

    lines = []
    for rel in relationships[:max_relationships]:
        lines.append(
            f"- {rel['source_table']}.{rel['source_column']} -> "
            f"{rel['target_table']}.{rel['target_column']}"
        )
    return "\n".join(lines)


def build_schema_signature(schema_columns: list[dict], relationships: list[dict] | None = None) -> str:
    payload = {
        "columns": sorted(
            f"{col['table_name']}.{col['column_name']}:{col.get('column_type', '')}"
            for col in schema_columns
        ),
        "relationships": sorted(
            f"{rel['source_table']}.{rel['source_column']}->{rel['target_table']}.{rel['target_column']}"
            for rel in (relationships or [])
        ),
    }
    return hashlib.md5(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def get_embedding_cache_paths(
    db_uri: str,
    schema_columns: list[dict],
    relationships: list[dict] | None,
    model_name: str,
    sample_limit: int,
    cache_dir: Path | None = None,
) -> tuple[Path, Path]:
    root = cache_dir or EMBEDDING_CACHE_DIR
    db_hash = hashlib.md5(db_uri.encode("utf-8")).hexdigest()
    schema_hash = build_schema_signature(schema_columns, relationships)
    store_hash = hashlib.md5(
        f"{db_hash}:{schema_hash}:{model_name}:{sample_limit}".encode("utf-8")
    ).hexdigest()
    base_dir = root / store_hash
    return base_dir / "index.faiss", base_dir / "meta.json"


def is_schema_question(question: str, schema_columns: list[dict] | None = None) -> bool:
    """Detect if the question is asking about database schema/metadata vs actual data.
    
    A schema question asks about structure (tables, columns) without referencing
    specific data rows. A data question references actual tables to retrieve data.
    """
    q = question.lower().strip()

    # Direct schema intent should always be treated as metadata requests,
    # even when table names are mentioned (e.g., "schema of employees").
    explicit_schema_terms = [
        "schema",
        "metadata",
        "table structure",
        "database structure",
        "column names",
        "columns and types",
        "field names",
    ]
    if any(term in q for term in explicit_schema_terms):
        return True
    
    # If question mentions actual table names, it's likely a data question.
    # This runs after explicit schema checks above.
    if schema_columns:
        table_names = {col["table_name"].lower() for col in schema_columns}
        for table_name in table_names:
            if table_name in q:
                return False  # References actual table = data question
    
    # Strong indicators of schema/metadata questions (asking about structure, not data)
    structure_indicators = [
        "show tables", "list tables", "what tables", "which tables",
        "describe table", "describe schema", "table structure",
        "database schema", "show schema", "schema information",
    ]
    
    # Questions about columns without referencing data
    column_patterns = [
        r"what columns? (?:are|does) (?:the )?\w+ (?:table )?have",
        r"what (?:are|is) the (?:column|field) (?:name|list)",
        r"show (?:me )?the (?:columns?|fields?)(?: in| of)?",
        r"list (?:all )?(?:the )?(?:columns?|fields?)",
    ]
    
    if any(indicator in q for indicator in structure_indicators):
        return True
    
    for pattern in column_patterns:
        if re.search(pattern, q):
            return True
    
    return False


def get_question_tables(question: str, schema_columns: list[dict]) -> list[str]:
    q = question.lower()
    table_names = sorted({col["table_name"] for col in schema_columns})
    return [table_name for table_name in table_names if table_name.lower() in q]


def run_schema_query(question: str, schema_columns: list[dict]):
    requested_tables = set(get_question_tables(question, schema_columns))
    wants_columns = is_schema_question(question, schema_columns)

    if wants_columns:
        filtered = [
            col for col in schema_columns
            if not requested_tables or col["table_name"] in requested_tables
        ]
        rows = [
            (col["table_name"], col["column_name"], col.get("column_type", ""))
            for col in filtered
        ]
        columns = ["table_name", "column_name", "column_type"]
        if requested_tables:
            table_list = ", ".join(f"'{table_name}'" for table_name in sorted(requested_tables))
            sql_query = (
                "SELECT table_name, column_name, data_type "
                "FROM information_schema.columns "
                f"WHERE table_schema = 'public' AND table_name IN ({table_list}) "
                "ORDER BY table_name, ordinal_position;"
            )
        else:
            sql_query = (
                "SELECT table_name, column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "ORDER BY table_name, ordinal_position;"
            )
        return sql_query, rows, columns

    table_rows = sorted({col["table_name"] for col in schema_columns})
    rows = [(table_name,) for table_name in table_rows]
    columns = ["table_name"]
    sql_query = (
        "SELECT table_name "
        "FROM information_schema.tables "
        "WHERE table_schema = 'public' "
        "ORDER BY table_name;"
    )
    return sql_query, rows, columns


def normalize_table_name(token: str) -> str:
    cleaned = token.strip().rstrip(",;")
    cleaned = cleaned.split()[0]
    if "." in cleaned:
        cleaned = cleaned.split(".")[-1]
    return cleaned.strip('"[]`').lower()


def normalize_identifier(token: str) -> str:
    return token.strip().strip('"[]`').lower()


def extract_table_aliases(sql_query: str, allowed_tables: set[str]) -> tuple[dict[str, str], list[str]]:
    aliases = {}
    referenced_tables = []
    matches = re.findall(
        r"\b(?:from|join)\s+([A-Za-z0-9_\.\"`\[\]]+)(?:\s+(?:as\s+)?([A-Za-z_][A-Za-z0-9_]*))?",
        sql_query,
        flags=re.IGNORECASE,
    )
    for table_token, alias_token in matches:
        table_name = normalize_table_name(table_token)
        if table_name not in allowed_tables:
            raise ValueError(
                f"Generated SQL referenced unknown table '{table_name}'. "
                "Only tables from the loaded schema are allowed."
            )
        referenced_tables.append(table_name)
        aliases[table_name] = table_name
        alias_name = normalize_identifier(alias_token) if alias_token else ""
        if alias_name and alias_name not in SQL_KEYWORDS:
            aliases[alias_name] = table_name
    return aliases, referenced_tables


def extract_select_aliases(sql_query: str) -> set[str]:
    return {
        normalize_identifier(alias)
        for alias in re.findall(r"\bas\s+([A-Za-z_][A-Za-z0-9_]*)\b", sql_query, flags=re.IGNORECASE)
    }


def strip_sql_literals(sql_query: str) -> str:
    no_strings = re.sub(r"'(?:''|[^'])*'", " ", sql_query)
    no_numbers = re.sub(r"\b\d+(?:\.\d+)?\b", " ", no_strings)
    return no_numbers


def validate_qualified_identifiers(sql_query: str, columns_by_table: dict[str, set[str]], aliases: dict[str, str]) -> None:
    for qualifier, column_name in re.findall(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b",
        sql_query,
        flags=re.IGNORECASE,
    ):
        qualifier_name = normalize_identifier(qualifier)
        column = normalize_identifier(column_name)
        if qualifier_name in {"pg_catalog", "information_schema", "sys"}:
            continue
        if qualifier_name not in aliases:
            raise ValueError(f"Generated SQL referenced unknown alias or table '{qualifier}'.")
        table_name = aliases[qualifier_name]
        if column not in columns_by_table.get(table_name, set()):
            raise ValueError(
                f"Generated SQL referenced unknown column '{column_name}' on table '{table_name}'."
            )


def validate_unqualified_identifiers(
    sql_query: str,
    columns_by_table: dict[str, set[str]],
    referenced_tables: list[str],
    select_aliases: set[str],
    table_aliases: dict[str, str],
) -> None:
    scrubbed = strip_sql_literals(sql_query)
    scrubbed = re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\b", " ", scrubbed)
    candidate_tokens = {
        normalize_identifier(token)
        for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", scrubbed)
    }

    allowed_columns = set().union(*(columns_by_table.get(table, set()) for table in referenced_tables))
    # Include table aliases (keys of aliases dict) in ignored set
    alias_names = set(table_aliases.keys())
    ignored = SQL_KEYWORDS | SQL_FUNCTIONS | set(referenced_tables) | select_aliases | alias_names | {"public"}

    invalid_tokens = sorted(
        token for token in candidate_tokens
        if token not in ignored and token not in allowed_columns
    )
    if invalid_tokens:
        raise ValueError(
            "Generated SQL referenced unknown identifiers: " + ", ".join(invalid_tokens[:5])
        )


def validate_with_explain(sql_query: str, engine, db_uri: str) -> None:
    dialect = detect_dialect(db_uri)
    statement = sql_query.strip().rstrip(";")
    if dialect == "sqlite":
        explain_sql = f"EXPLAIN QUERY PLAN {statement}"
    elif dialect in {"mysql", "postgresql"}:
        explain_sql = f"EXPLAIN {statement}"
    else:
        return

    with engine.connect() as conn:
        conn.execute(text(explain_sql))


def validate_sql_query(
    sql_query: str,
    schema_columns: list[dict],
    question: str,
    relationships: list[dict] | None = None,
    engine=None,
    db_uri: str | None = None,
) -> None:
    lower_sql = sql_query.lower()
    allowed_tables = {col["table_name"].lower() for col in schema_columns}
    columns_by_table = {}
    for col in schema_columns:
        table_name = col["table_name"].lower()
        columns_by_table.setdefault(table_name, set()).add(col["column_name"].lower())

    invalid_identifiers = [
        ident for ident in FORBIDDEN_METADATA_IDENTIFIERS
        if re.search(rf"\b{ident}\b", lower_sql)
    ]
    if invalid_identifiers:
        raise ValueError(
            "Generated SQL used invalid metadata identifiers. Please retry the question."
        )

    if sql_query.count(";") > 1:
        raise ValueError("Only a single SELECT statement is allowed.")

    if not is_schema_question(question, schema_columns):
        if re.search(r"\b(pg_catalog|information_schema|sqlite_master|sys\.)\b", lower_sql):
            raise ValueError("System catalog queries are only allowed for explicit schema questions.")

    aliases, referenced_tables = extract_table_aliases(sql_query, allowed_tables)
    select_aliases = extract_select_aliases(sql_query)
    validate_qualified_identifiers(sql_query, columns_by_table, aliases)
    validate_unqualified_identifiers(sql_query, columns_by_table, referenced_tables, select_aliases, aliases)

    if engine is not None and db_uri:
        validate_with_explain(sql_query, engine, db_uri)


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


def build_prompt(
    question,
    db_uri,
    schema_columns,
    engine,
    few_shot_examples=None,
    relevant_columns=None,
    relationships=None,
):
    schema_for_prompt = relevant_columns if relevant_columns else schema_columns
    schema_str = format_schema(schema_for_prompt)
    relationship_str = format_relationships(relationships)

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

Rules:
- Use only tables and columns explicitly listed in Schema.
- Never invent identifier names such as `tablename` or `columnname`.
- For normal data questions, query only the business tables from Schema.
- Do not query `pg_catalog`, `information_schema`, `sqlite_master`, or `sys.*` unless the user explicitly asks for schema metadata.
- Use appropriate SQL features based on the question: JOINs (INNER/LEFT/RIGHT/FULL) for combining tables, subqueries or CTEs (WITH clauses) for complex logic, window functions (ROW_NUMBER, RANK, LAG, LEAD) for analytics, GROUP BY and aggregations (COUNT, SUM, AVG, MIN, MAX) for summaries, ORDER BY for sorting, LIMIT/OFFSET for pagination, CASE expressions for conditional logic, and views if the schema provides them.

Schema:
{schema_str}

Relationships:
{relationship_str}

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


def generate_sql_from_question(
    question: str,
    db_uri: str,
    schema_columns: list[dict],
    engine,
    few_shot_examples=None,
    relevant_columns=None,
    relationships=None,
) -> str:
    """Generate a strict SQL query from natural language question using LLM directly"""
    prompt = build_prompt(
        question,
        db_uri,
        schema_columns,
        engine,
        few_shot_examples,
        relevant_columns,
        relationships,
    )

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

    validate_sql_query(
        sql_query,
        schema_columns,
        question,
        relationships=relationships,
        engine=engine,
        db_uri=db_uri,
    )

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


def load_cached_embedding_store(index_path: Path, meta_path: Path):
    try:
        import faiss
    except Exception as e:
        return None, f"Embedding dependencies not available: {e}"

    if not index_path.exists() or not meta_path.exists():
        return None, None

    metadata = json.loads(meta_path.read_text())
    index = faiss.read_index(str(index_path))
    return {
        "index": index,
        "columns": metadata.get("columns", []),
        "texts": metadata.get("texts", []),
        "model_name": metadata.get("model_name", "all-MiniLM-L6-v2"),
        "relationships": metadata.get("relationships", []),
        "schema_hash": metadata.get("schema_hash"),
    }, None


def save_cached_embedding_store(index_path: Path, meta_path: Path, embed_store) -> None:
    import faiss

    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(embed_store["index"], str(index_path))
    meta = {
        "columns": embed_store["columns"],
        "texts": embed_store["texts"],
        "model_name": embed_store["model_name"],
        "relationships": embed_store.get("relationships", []),
        "schema_hash": embed_store.get("schema_hash"),
    }
    meta_path.write_text(json.dumps(meta, indent=2))


def get_column_relationship_text(column: dict, relationships: list[dict] | None) -> str:
    if not relationships:
        return "none"

    matches = []
    column_key = (column["table_name"], column["column_name"])
    for rel in relationships:
        source_key = (rel["source_table"], rel["source_column"])
        target_key = (rel["target_table"], rel["target_column"])
        if column_key == source_key:
            matches.append(
                f"joins to {rel['target_table']}.{rel['target_column']}"
            )
        elif column_key == target_key:
            matches.append(
                f"joined from {rel['source_table']}.{rel['source_column']}"
            )
    return "; ".join(matches) if matches else "none"


def dedupe_columns(columns: list[dict]) -> list[dict]:
    seen = set()
    ordered = []
    for col in columns:
        key = (col["table_name"], col["column_name"])
        if key in seen:
            continue
        seen.add(key)
        ordered.append(col)
    return ordered


def select_relevant_relationships(columns: list[dict], relationships: list[dict] | None) -> list[dict]:
    if not relationships:
        return []

    tables = {col["table_name"] for col in columns}
    selected = []
    for rel in relationships:
        if rel["source_table"] in tables or rel["target_table"] in tables:
            selected.append(rel)
    return selected


def tokenize_for_evidence(text_value: str) -> set[str]:
    return {
        token for token in re.findall(r"[A-Za-z0-9_]+", text_value.lower())
        if token and token not in EVIDENCE_STOPWORDS
    }


def describe_column_evidence(question: str, column: dict) -> str:
    q_tokens = tokenize_for_evidence(question)
    column_tokens = tokenize_for_evidence(column["column_name"])
    table_tokens = tokenize_for_evidence(column["table_name"])

    matches = sorted((column_tokens | table_tokens) & q_tokens)
    if matches:
        return "Matches question terms: " + ", ".join(matches[:3])

    if column["column_name"].lower() in {"created_at", "updated_at", "order_date", "date", "time"}:
        return "Selected as a temporal field for date-related reasoning"

    if column["column_name"].lower() in {"revenue", "profit", "cost", "salary", "budget"}:
        return "Selected as a metric-bearing field"

    return "Selected by schema retrieval relevance"


def build_query_evidence(
    question: str,
    schema_columns: list[dict],
    relevant_columns: list[dict] | None = None,
    relationships: list[dict] | None = None,
    temporal_context: dict | None = None,
    max_columns: int = 10,
) -> dict:
    selected_columns = relevant_columns if relevant_columns else schema_columns[:max_columns]
    selected_columns = dedupe_columns(selected_columns)[:max_columns]
    selected_tables = sorted({col["table_name"] for col in selected_columns})
    selected_relationships = select_relevant_relationships(selected_columns, relationships)

    temporal_items = []
    if temporal_context:
        selected_table_names = set(selected_tables)
        for key, bounds in temporal_context.items():
            table_name, _, column_name = key.partition(".")
            if table_name in selected_table_names or any(
                col["column_name"] == column_name for col in selected_columns
            ):
                temporal_items.append({
                    "ref": key,
                    "min": bounds["min"],
                    "max": bounds["max"],
                })

    evidence_columns = [
        {
            "ref": f"{col['table_name']}.{col['column_name']}",
            "column_type": col.get("column_type", ""),
            "reason": describe_column_evidence(question, col),
        }
        for col in selected_columns
    ]

    evidence_relationships = [
        {
            "ref": (
                f"{rel['source_table']}.{rel['source_column']} -> "
                f"{rel['target_table']}.{rel['target_column']}"
            ),
            "reason": "Available join path from detected foreign-key relationship",
        }
        for rel in selected_relationships
    ]

    summary = {
        "table_count": len(selected_tables),
        "column_count": len(evidence_columns),
        "relationship_count": len(evidence_relationships),
        "temporal_count": len(temporal_items),
    }

    return {
        "summary": summary,
        "tables": selected_tables,
        "columns": evidence_columns,
        "relationships": evidence_relationships,
        "temporal": temporal_items,
    }


def expand_related_columns(
    columns: list[dict],
    schema_columns: list[dict],
    relationships: list[dict] | None,
    limit: int | None = None,
) -> list[dict]:
    if not relationships:
        return dedupe_columns(columns)[:limit] if limit else dedupe_columns(columns)

    schema_lookup = {
        (col["table_name"], col["column_name"]): col
        for col in schema_columns
    }
    expanded = list(columns)
    table_columns = {}
    for col in schema_columns:
        table_columns.setdefault(col["table_name"], []).append(col)

    descriptive_names = {"name", "title", "description", "product", "department"}
    selected_keys = {(col["table_name"], col["column_name"]) for col in columns}
    selected_tables = {col["table_name"] for col in columns}

    for rel in relationships:
        source_key = (rel["source_table"], rel["source_column"])
        target_key = (rel["target_table"], rel["target_column"])
        touches_selected = (
            source_key in selected_keys or
            target_key in selected_keys or
            rel["source_table"] in selected_tables or
            rel["target_table"] in selected_tables
        )
        if not touches_selected:
            continue

        for key in (source_key, target_key):
            if key in schema_lookup:
                expanded.append(schema_lookup[key])

        for table_name in (rel["source_table"], rel["target_table"]):
            candidates = table_columns.get(table_name, [])
            descriptive = [
                col for col in candidates
                if col["column_name"].lower() in descriptive_names
            ]
            if descriptive:
                expanded.append(descriptive[0])

    expanded = dedupe_columns(expanded)
    return expanded[:limit] if limit else expanded


def build_column_embeddings(
    engine,
    schema_columns: list[dict],
    relationships: list[dict] | None = None,
    model_name: str = "all-MiniLM-L6-v2",
    sample_limit: int = 3,
    persist: bool = False,
    db_uri: str | None = None,
    cache_dir: Path | None = None,
):
    try:
        import numpy as np
        import faiss
    except Exception as e:
        return None, f"Embedding dependencies not available: {e}"

    if not schema_columns:
        return None, "No schema columns available for embeddings."

    schema_hash = build_schema_signature(schema_columns, relationships)
    if persist and db_uri:
        index_path, meta_path = get_embedding_cache_paths(
            db_uri,
            schema_columns,
            relationships,
            model_name,
            sample_limit,
            cache_dir=cache_dir,
        )
        cached_store, cache_err = load_cached_embedding_store(index_path, meta_path)
        if cached_store is not None:
            return cached_store, cache_err

    model = get_embedding_model(model_name)
    texts = []
    columns = []

    for col in schema_columns:
        samples = get_column_samples(engine, col["table_name"], col["column_name"], limit=sample_limit)
        sample_text = ", ".join(samples) if samples else "none"
        relationship_text = get_column_relationship_text(col, relationships)
        text_blob = (
            f"{col['table_name']}.{col['column_name']} ({col.get('column_type','')}). "
            f"Samples: {sample_text}. Relationships: {relationship_text}"
        )
        texts.append(text_blob)
        columns.append(col)

    embeddings = model.encode(texts, normalize_embeddings=True)
    embeddings = embeddings.astype("float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    embed_store = {
        "index": index,
        "columns": columns,
        "texts": texts,
        "model_name": model_name,
        "relationships": relationships or [],
        "schema_hash": schema_hash,
    }

    if persist and db_uri:
        save_cached_embedding_store(index_path, meta_path, embed_store)

    return embed_store, None


def retrieve_schema_context(
    question: str,
    embed_store,
    schema_columns: list[dict],
    relationships: list[dict] | None,
    top_k: int = 8,
    related_limit: int = 4,
) -> dict:
    base_columns = retrieve_relevant_columns(question, embed_store, top_k=top_k)
    expanded_columns = expand_related_columns(
        base_columns,
        schema_columns,
        relationships,
        limit=top_k + related_limit,
    )
    selected_relationships = select_relevant_relationships(expanded_columns, relationships)
    return {
        "columns": expanded_columns,
        "relationships": selected_relationships,
    }


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
You are a SQL assistant. Determine if the user question is TRULY ambiguous given the schema.

Schema:
{schema_str}

Question: "{question}"

A question is ONLY ambiguous if:
- It references tables that don't exist in the schema
- It's missing critical information that would prevent writing a SQL query
- It could reasonably be interpreted in two completely different ways

A question is NOT ambiguous just because:
- The user didn't specify exact column names (we can infer from schema)
- The user didn't specify join conditions (we have foreign key relationships)
- Multiple columns could theoretically be used (the system will pick the most logical one)

If the question is truly ambiguous, propose 1-2 short clarifying questions.
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
        json_str = _re.search(r"\{{.*\}}", raw, _re.DOTALL).group()
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


def prepare_query(
    db_uri: str,
    question: str,
    engine=None,
    schema_columns=None,
    relationships=None,
    few_shot_examples=None,
    relevant_columns=None,
):
    """Generate and validate SQL without executing it."""
    if engine is None:
        engine = create_engine(db_uri)
    if schema_columns is None:
        schema_columns = get_schema_columns(engine)
    if relationships is None:
        relationships = get_schema_relationships(engine)

    if is_schema_question(question, schema_columns):
        sql_query, _, _ = run_schema_query(question, schema_columns)
        return sql_query

    sql_query = generate_sql_from_question(
        question,
        db_uri,
        schema_columns,
        engine,
        few_shot_examples=few_shot_examples,
        relevant_columns=relevant_columns,
        relationships=relationships,
    )
    return sql_query


def execute_sql_query(sql_query: str, engine, question: str | None = None, schema_columns=None):
    """Execute a validated SQL query or serve deterministic schema results."""
    if question and is_schema_question(question, schema_columns):
        if schema_columns is None:
            schema_columns = get_schema_columns(engine)
        _, rows, columns = run_schema_query(question, schema_columns)
        return rows, columns

    with engine.connect() as conn:
        result = conn.execute(text(sql_query))
        rows = result.fetchall()
        columns = list(result.keys())

    return rows, columns


def run_query(
    db_uri: str,
    question: str,
    engine=None,
    schema_columns=None,
    relationships=None,
    few_shot_examples=None,
    relevant_columns=None,
):
    """Convert question -> SQL -> Execute SQL safely and return results + SQL"""
    if engine is None:
        engine = create_engine(db_uri)
    if schema_columns is None:
        schema_columns = get_schema_columns(engine)

    sql_query = prepare_query(
        db_uri,
        question,
        engine=engine,
        schema_columns=schema_columns,
        relationships=relationships,
        few_shot_examples=few_shot_examples,
        relevant_columns=relevant_columns,
    )
    rows, columns = execute_sql_query(
        sql_query,
        engine,
        question=question,
        schema_columns=schema_columns,
    )

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


