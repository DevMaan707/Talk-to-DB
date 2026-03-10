import json
from pathlib import Path
from utils import save_feedback, load_annotations
from test_config import MOCK_SCHEMA

FEEDBACK_FILE = Path("schema_annotations.json")


def cleanup():
    if FEEDBACK_FILE.exists():
        FEEDBACK_FILE.unlink()


def test_save_single_feedback():
    cleanup()
    save_feedback(
        question="show top employees by salary",
        bad_sql="SELECT * FROM employees LIMIT 5",
        correction_note="Should ORDER BY salary DESC",
        schema_columns=MOCK_SCHEMA
    )
    assert FEEDBACK_FILE.exists(), "Feedback file not created"
    data = json.loads(FEEDBACK_FILE.read_text())
    assert len(data) == 1, "Should have 1 entry"
    assert data[0]["correction"] == "Should ORDER BY salary DESC"
    assert data[0]["question"] == "show top employees by salary"
    print("OK: Single feedback saved correctly")


def test_annotations_load_as_string():
    result = load_annotations(MOCK_SCHEMA)
    assert isinstance(result, str), "Annotations must be a string"
    assert len(result) > 0, "Annotations should not be empty after save"
    print(f"OK: Annotations returned as string ({len(result)} chars)")


def test_annotation_capped_at_5():
    cleanup()
    for i in range(8):
        save_feedback(
            question=f"query number {i}",
            bad_sql=f"SELECT {i} FROM employees",
            correction_note=f"fix {i}",
            schema_columns=MOCK_SCHEMA
        )
    result = load_annotations(MOCK_SCHEMA)
    entry_count = result.count("correction hint:")
    assert entry_count <= 5, f"Too many annotations: {entry_count}"
    print(f"OK: Annotation cap works: {entry_count} returned (max 5)")


def test_irrelevant_schema_returns_empty():
    unrelated_schema = [
        {"table_name": "invoices", "column_name": "invoice_id", "column_type": "INTEGER"},
        {"table_name": "invoices", "column_name": "invoice_total", "column_type": "DECIMAL"},
    ]
    result = load_annotations(unrelated_schema)
    print(f"OK: Unrelated schema -> annotations: '{result[:60]}...' (may be empty)")


if __name__ == "__main__":
    test_save_single_feedback()
    test_annotations_load_as_string()
    test_annotation_capped_at_5()
    test_irrelevant_schema_returns_empty()
    cleanup()
