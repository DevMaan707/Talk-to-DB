from llm_agent import build_query_evidence
from test_config import MOCK_SCHEMA, MOCK_RELATIONSHIP_SCHEMA, MOCK_RELATIONSHIPS


def test_evidence_includes_retrieved_columns():
    evidence = build_query_evidence(
        "show employee salaries",
        MOCK_SCHEMA,
        relevant_columns=[
            {"table_name": "employees", "column_name": "name", "column_type": "VARCHAR"},
            {"table_name": "employees", "column_name": "salary", "column_type": "DECIMAL"},
        ],
    )
    refs = [item["ref"] for item in evidence["columns"]]
    assert "employees.name" in refs, "Expected employees.name in evidence"
    assert "employees.salary" in refs, "Expected employees.salary in evidence"
    print("OK: Evidence includes retrieved columns")


def test_evidence_includes_relationships_and_temporal_bounds():
    evidence = build_query_evidence(
        "show customer revenue by name",
        MOCK_RELATIONSHIP_SCHEMA,
        relevant_columns=MOCK_RELATIONSHIP_SCHEMA,
        relationships=MOCK_RELATIONSHIPS,
        temporal_context={
            "orders.order_date": {"min": "2024-01-01", "max": "2025-03-01"},
            "customers.created_at": {"min": "2023-01-01", "max": "2024-01-01"},
        },
    )
    assert evidence["relationships"], "Expected relationship evidence"
    temporal_refs = [item["ref"] for item in evidence["temporal"]]
    assert "orders.order_date" in temporal_refs, "Expected orders.order_date temporal evidence"
    print("OK: Evidence includes relationships and temporal bounds")


if __name__ == "__main__":
    test_evidence_includes_retrieved_columns()
    test_evidence_includes_relationships_and_temporal_bounds()
