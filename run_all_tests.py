import subprocess
import sys

NO_DB_NEEDED = ["test_dialect.py", "test_drift.py", "test_access.py",
                "test_feedback.py", "test_embeddings.py", "test_sql_validation.py",
                "test_evidence.py"]
NEEDS_LLM = ["test_confidence.py", "test_ambiguity.py", "test_validation.py"]
NEEDS_LIVE_DB = ["test_temporal.py"]


def run_group(label, files):
    print(f"\n{'='*50}\n{label}\n{'='*50}")
    failed = []
    for t in files:
        print(f"\nTEST {t}")
        print("-" * 40)
        r = subprocess.run([sys.executable, t])
        if r.returncode != 0:
            print("FAIL")
            failed.append(t)
        else:
            print("PASS")
    return failed


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    all_failed = []

    if mode in ("all", "fast"):
        all_failed += run_group("No DB / No LLM needed", NO_DB_NEEDED)

    if mode in ("all", "llm"):
        all_failed += run_group("Needs LLM (GROQ_API_KEY required)", NEEDS_LLM)

    if mode in ("all", "db"):
        all_failed += run_group("Needs Live DB (run setup_docker_db.py start first)", NEEDS_LIVE_DB)

    print(f"\n{'='*50}")
    if all_failed:
        print(f"FAIL: {len(all_failed)} test(s) failed: {all_failed}")
    else:
        print("OK: All tests passed")
