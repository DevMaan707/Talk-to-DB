from llm_agent import validate_result_semantics


def test_plausible_salary_result():
    rows = [("Alice", 75000.00), ("Bob", 62000.00), ("Carol", 91000.00)]
    columns = ["name", "salary"]
    result = validate_result_semantics(
        "Show all employee salaries",
        "SELECT name, salary FROM employees;",
        rows, columns
    )
    assert "valid" in result
    assert "confidence" in result
    assert "reason" in result
    print(f"OK: Plausible result -> valid={result['valid']}, confidence={result['confidence']}")
    print(f"Reason: {result['reason']}")


def test_suspicious_zero_salaries():
    rows = [(0,), (0,), (0,)]
    columns = ["salary"]
    result = validate_result_semantics(
        "What is the average employee salary?",
        "SELECT salary FROM employees;",
        rows, columns
    )
    print(f"WARN: Zero salary result -> valid={result['valid']}, confidence={result['confidence']}")
    print(f"Warning: {result.get('warning')}")


def test_wrong_table_result():
    rows = [("Widget A",), ("Widget B",)]
    columns = ["product"]
    result = validate_result_semantics(
        "Show all employee names",
        "SELECT product FROM orders;",
        rows, columns
    )
    print(f"WARN: Wrong table -> valid={result['valid']}, confidence={result['confidence']}")
    print(f"Warning: {result.get('warning')}")


def test_empty_result_is_valid():
    result = validate_result_semantics(
        "List all orders from 1900",
        "SELECT * FROM orders WHERE order_date < '1901-01-01';",
        [], []
    )
    assert result["valid"] is True, "Empty result should be valid"
    print("OK: Empty result treated as valid")


if __name__ == "__main__":
    test_plausible_salary_result()
    test_suspicious_zero_salaries()
    test_wrong_table_result()
    test_empty_result_is_valid()
