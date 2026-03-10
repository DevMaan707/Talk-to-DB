from llm_agent import check_access, classify_query_intent


def test_intent_tagging():
    cases = [
        ("show all employees", ["lookup"]),
        ("what is the average salary", ["aggregation", "sensitive"]),
        ("count orders by product", ["aggregation", "lookup"]),
        ("compare revenue vs last quarter", ["comparison", "financial"]),
        ("list all email addresses", ["lookup", "sensitive"]),
    ]
    for question, must_include in cases:
        intents = classify_query_intent(question)
        hits = all(e in intents for e in must_include)
        status = "OK" if hits else "WARN"
        print(f"{status} '{question}' -> got {intents}, needed {must_include}")


def test_viewer_blocked_sensitive():
    allowed, reason = check_access("show all employee salaries", "viewer")
    assert not allowed, "Viewer must be blocked from salary"
    print(f"OK: Viewer blocked from salary: {reason}")


def test_viewer_blocked_financial():
    allowed, reason = check_access("show total revenue by product", "viewer")
    assert not allowed, "Viewer must be blocked from financial"
    print(f"OK: Viewer blocked from financial: {reason}")


def test_viewer_allowed_basic():
    allowed, _ = check_access("show all products", "viewer")
    assert allowed, "Viewer should access basic lookups"
    print("OK: Viewer allowed basic lookup")


def test_analyst_blocked_sensitive():
    allowed, reason = check_access("list all passwords and tokens", "analyst")
    assert not allowed, "Analyst must be blocked from sensitive"
    print(f"OK: Analyst blocked from sensitive: {reason}")


def test_analyst_allowed_financial():
    allowed, _ = check_access("show total revenue by region", "analyst")
    assert allowed, "Analyst should access financial queries"
    print("OK: Analyst allowed financial query")


def test_admin_unrestricted():
    queries = [
        "show all salaries",
        "compare revenue vs budget",
        "fetch all email addresses",
        "get all tokens",
    ]
    for q in queries:
        allowed, _ = check_access(q, "admin")
        assert allowed, f"Admin should always have access: {q}"
        print(f"OK: Admin allowed: '{q}'")


if __name__ == "__main__":
    test_intent_tagging()
    test_viewer_blocked_sensitive()
    test_viewer_blocked_financial()
    test_viewer_allowed_basic()
    test_analyst_blocked_sensitive()
    test_analyst_allowed_financial()
    test_admin_unrestricted()
