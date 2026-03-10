from llm_agent import detect_dialect, get_dialect_prompt_snippet


def test_dialect_detection():
    cases = {
        "mysql+pymysql://user:pass@host/db": "mysql",
        "postgresql+psycopg2://user:pass@host/db": "postgresql",
        "sqlite:///mydb.sqlite": "sqlite",
        "mssql+pyodbc://user:pass@host/db": "mssql",
        "unknown://user:pass@host/db": "mysql",
    }
    for uri, expected in cases.items():
        result = detect_dialect(uri)
        status = "OK" if result == expected else "FAIL"
        print(f"{status} {uri[:40]}... -> Expected: {expected}, Got: {result}")


def test_dialect_prompt_content():
    snippet = get_dialect_prompt_snippet("postgresql+psycopg2://x:y@z/db")
    assert "POSTGRESQL" in snippet.upper(), "Dialect name missing"
    assert "NOW()" in snippet, "Time function missing"
    assert "LIMIT" in snippet, "Pagination syntax missing"
    print("OK: PostgreSQL dialect prompt has correct rules")

    snippet_mysql = get_dialect_prompt_snippet("mysql+pymysql://x:y@z/db")
    assert "CONCAT" in snippet_mysql, "MySQL concat missing"
    print("OK: MySQL dialect prompt has correct rules")


if __name__ == "__main__":
    test_dialect_detection()
    test_dialect_prompt_content()
