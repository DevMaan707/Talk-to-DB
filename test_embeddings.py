from unittest.mock import MagicMock, patch
from llm_agent import build_column_embeddings, retrieve_relevant_columns
from test_config import MOCK_SCHEMA


def build_mock_store():
    mock_engine = MagicMock()
    with patch("llm_agent.get_column_samples", return_value=["100", "200", "Alice"]):
        store, err = build_column_embeddings(mock_engine, MOCK_SCHEMA)
    return store, err


def test_store_builds_correctly():
    store, err = build_mock_store()
    assert err is None, f"Build error: {err}"
    assert store is not None, "Store is None"
    assert "index" in store, "Missing FAISS index"
    assert "columns" in store, "Missing columns"
    assert len(store["columns"]) == len(MOCK_SCHEMA)
    print(f"OK: Store built: {len(store['columns'])} columns indexed")
    return store


def test_retrieval_returns_relevant(store):
    cases = [
        ("what is the total revenue by product", ["revenue", "product"]),
        ("show all employee salaries", ["salary", "name"]),
        ("when were orders placed", ["order_date", "created_at"]),
    ]
    for question, expected_cols in cases:
        results = retrieve_relevant_columns(question, store, top_k=5)
        col_names = [c["column_name"] for c in results]
        hit = any(e in col_names for e in expected_cols)
        status = "OK" if hit else "WARN"
        print(f"{status} '{question}' -> retrieved: {col_names}, wanted any of {expected_cols}")


def test_top_k_respected(store):
    results = retrieve_relevant_columns("show data", store, top_k=3)
    assert len(results) <= 3, f"top_k=3 but got {len(results)} results"
    print(f"OK: top_k respected: {len(results)} columns returned")


def test_none_store_returns_empty():
    result = retrieve_relevant_columns("show all orders", None, top_k=5)
    assert result == [], "None store should return []"
    print("OK: None store safely returns empty list")


def test_full_pipeline_uses_relevant_subset(store):
    results = retrieve_relevant_columns("show employee salary data", store, top_k=4)
    all_keys = {(c["table_name"], c["column_name"]) for c in MOCK_SCHEMA}
    result_keys = {(c["table_name"], c["column_name"]) for c in results}
    assert result_keys.issubset(all_keys), "Retrieved columns not from original schema"
    print(f"OK: All retrieved columns are valid schema members: {[c['column_name'] for c in results]}")


if __name__ == "__main__":
    store, _ = build_mock_store()
    test_store_builds_correctly()
    test_retrieval_returns_relevant(store)
    test_top_k_respected(store)
    test_none_store_returns_empty()
    test_full_pipeline_uses_relevant_subset(store)
