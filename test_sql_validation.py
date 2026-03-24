from llm_agent import validate_sql_query
from test_config import MOCK_SCHEMA


def test_invalid_metadata_identifiers_blocked():
    try:
        validate_sql_query(
            "SELECT tablename, columnname FROM employees;",
            MOCK_SCHEMA,
            "show me all employees",
        )
        raise AssertionError("invalid metadata identifiers were allowed")
    except ValueError as exc:
        assert "invalid metadata identifiers" in str(exc).lower()
        print("OK: Invalid metadata identifiers are blocked")


def test_unknown_table_blocked():
    try:
        validate_sql_query(
            "SELECT id FROM missing_table;",
            MOCK_SCHEMA,
            "show me all employees",
        )
        raise AssertionError("unknown table was allowed")
    except ValueError as exc:
        assert "unknown table" in str(exc).lower()
        print("OK: Unknown tables are blocked")


def test_unknown_qualified_column_blocked():
    try:
        validate_sql_query(
            "SELECT employees.missing_col FROM employees;",
            MOCK_SCHEMA,
            "show me all employees",
        )
        raise AssertionError("unknown qualified column was allowed")
    except ValueError as exc:
        assert "unknown column" in str(exc).lower()
        print("OK: Unknown qualified columns are blocked")


def test_unknown_unqualified_column_blocked():
    try:
        validate_sql_query(
            "SELECT missing_col FROM employees;",
            MOCK_SCHEMA,
            "show me all employees",
        )
        raise AssertionError("unknown unqualified column was allowed")
    except ValueError as exc:
        assert "unknown identifiers" in str(exc).lower()
        print("OK: Unknown unqualified columns are blocked")


def test_valid_sql_passes():
    validate_sql_query(
        "SELECT name, salary FROM employees ORDER BY salary DESC;",
        MOCK_SCHEMA,
        "show all employees ordered by salary",
    )
    print("OK: Valid SQL passes static validation")


if __name__ == "__main__":
    test_invalid_metadata_identifiers_blocked()
    test_unknown_table_blocked()
    test_unknown_qualified_column_blocked()
    test_unknown_unqualified_column_blocked()
    test_valid_sql_passes()
