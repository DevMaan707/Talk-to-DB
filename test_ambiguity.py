from llm_agent import detect_ambiguity
from test_config import MOCK_SCHEMA


def test_unambiguous_questions():
    questions = [
        "Show all employees ordered by salary descending",
        "Count total orders placed after 2024-01-01",
        "List employees in the Engineering department",
    ]
    for q in questions:
        result = detect_ambiguity(q, MOCK_SCHEMA)
        status = "OK: Clear" if not result else "WARN: Ambiguous (unexpected)"
        print(f"{status}: '{q}' -> {result}")


def test_ambiguous_questions():
    questions = [
        ("show me top customers", "top by what metric?"),
        ("get recent orders", "how recent is recent?"),
        ("list high earning employees", "what threshold counts as high?"),
    ]
    for q, reason in questions:
        result = detect_ambiguity(q, MOCK_SCHEMA)
        status = "OK: Caught" if result else "WARN: Missed"
        print(f"{status}: '{q}' ({reason}) -> {result}")


def test_returns_list():
    result = detect_ambiguity("show top employees", MOCK_SCHEMA)
    assert isinstance(result, list), "Must return a list"
    assert len(result) <= 2, "Should return at most 2 questions"
    print(f"OK: Returns list of max 2 questions: {result}")


if __name__ == "__main__":
    test_unambiguous_questions()
    test_ambiguous_questions()
    test_returns_list()
