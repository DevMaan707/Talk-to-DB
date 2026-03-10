from datetime import datetime
import json
import hashlib
from pathlib import Path

SCHEMA_SNAPSHOT_FILE = "schema_snapshot.json"
FEEDBACK_FILE = "schema_annotations.json"


def log_query(db_uri, user_query, result):
    with open("query_logs.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] DB: {db_uri}\nQ: {user_query}\nA: {result}\n\n")


def snapshot_schema(schema_columns: list[dict]) -> str:
    """Returns a hash of the current schema."""
    schema_str = json.dumps(sorted(
        [f"{c['table_name']}.{c['column_name']}" for c in schema_columns]
    ))
    return hashlib.md5(schema_str.encode()).hexdigest()


def check_schema_drift(schema_columns: list[dict]) -> tuple[bool, str]:
    """
    Compares current schema hash to saved snapshot.
    Returns (drifted: bool, message: str)
    """
    current_hash = snapshot_schema(schema_columns)
    snap_path = Path(SCHEMA_SNAPSHOT_FILE)

    if not snap_path.exists():
        snap_path.write_text(json.dumps({"hash": current_hash}))
        return False, "Schema snapshot created."

    saved = json.loads(snap_path.read_text())

    if saved.get("hash") != current_hash:
        snap_path.write_text(json.dumps({"hash": current_hash}))
        return True, "WARNING: Schema has changed since last session. Few-shot examples may be stale."

    return False, "Schema unchanged."


def save_feedback(question: str, bad_sql: str, correction_note: str, schema_columns: list[dict]):
    """Stores user correction as a schema annotation for future prompts."""
    path = Path(FEEDBACK_FILE)
    data = json.loads(path.read_text()) if path.exists() else []

    mentioned = [
        f"{c['table_name']}.{c['column_name']}"
        for c in schema_columns
        if c["column_name"].lower() in question.lower()
    ]

    data.append({
        "question": question,
        "bad_sql": bad_sql,
        "correction": correction_note,
        "relevant_columns": mentioned
    })
    path.write_text(json.dumps(data, indent=2))


def load_annotations(schema_columns: list[dict]) -> str:
    """Returns relevant past corrections as a string to inject into prompts."""
    path = Path(FEEDBACK_FILE)
    if not path.exists():
        return ""

    data = json.loads(path.read_text())
    current_cols = {f"{c['table_name']}.{c['column_name']}" for c in schema_columns}

    relevant = [
        f"- User said '{d['question']}' -> SQL was wrong. correction hint: {d['correction']}"
        for d in data
        if any(col in current_cols for col in d.get("relevant_columns", []))
    ]

    return "\n".join(relevant[-5:])
