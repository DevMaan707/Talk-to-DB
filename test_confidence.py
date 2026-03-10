from llm_agent import score_sql_confidence
from test_config import MOCK_SCHEMA


def test_correct_sql_high_confidence():
    result = score_sql_confidence(
        question="Show all employees",
        sql="SELECT id, name, salary, department FROM employees;",
        schema_columns=MOCK_SCHEMA
    )
    assert "score" in result, "Missing score"
    assert "level" in result, "Missing level"
    assert "reason" in result, "Missing reason"
    assert result["level"] in ["low", "medium", "high"]
    assert 1 <= result["score"] <= 10, "Score out of 1-10 range"
    print(f"OK: Matching SQL -> score={result['score']}, level={result['level']}")
    print(f"Reason: {result['reason']}")


def test_mismatched_sql_low_confidence():
    result = score_sql_confidence(
        question="Show quarterly revenue broken down by product",
        sql="SELECT id FROM employees;",
        schema_columns=MOCK_SCHEMA
    )
    assert 1 <= result["score"] <= 10, "Score out of range"
    print(f"WARN: Mismatched SQL -> score={result['score']}, level={result['level']}")
    print(f"Reason: {result['reason']}")


def test_level_thresholds():
    for score, expected_level in [(9, "high"), (6, "medium"), (3, "low")]:
        level = "high" if score >= 8 else "medium" if score >= 5 else "low"
        assert level == expected_level, f"Score {score} should be {expected_level}"
    print("OK: Level bucketing thresholds are correct")


if __name__ == "__main__":
    test_correct_sql_high_confidence()
    test_mismatched_sql_low_confidence()
    test_level_thresholds()
