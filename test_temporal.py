from sqlalchemy import create_engine
from llm_agent import resolve_temporal_context
from test_config import DB_URI


def test_temporal_context_live():
    engine = create_engine(DB_URI)

    schema = [
        {"table_name": "employees", "column_name": "created_at", "column_type": "TIMESTAMP"},
        {"table_name": "orders", "column_name": "order_date", "column_type": "DATE"},
    ]

    result = resolve_temporal_context(engine, schema)

    assert len(result) > 0, "No temporal context returned"

    for col_key, bounds in result.items():
        assert bounds["min"] not in (None, "None"), f"Min is None for {col_key}"
        assert bounds["max"] not in (None, "None"), f"Max is None for {col_key}"
        print(f"OK: {col_key}: {bounds['min']} -> {bounds['max']}")


def test_non_date_columns_excluded():
    engine = create_engine(DB_URI)
    schema = [
        {"table_name": "employees", "column_name": "name", "column_type": "VARCHAR"},
        {"table_name": "employees", "column_name": "salary", "column_type": "DECIMAL"},
    ]
    result = resolve_temporal_context(engine, schema)
    assert result == {}, "Non-date columns should produce empty context"
    print("OK: Non-date columns correctly excluded from temporal context")


if __name__ == "__main__":
    test_temporal_context_live()
    test_non_date_columns_excluded()
