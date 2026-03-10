from pathlib import Path
from utils import check_schema_drift, snapshot_schema
from test_config import MOCK_SCHEMA

SNAP_FILE = Path("schema_snapshot.json")


def cleanup():
    if SNAP_FILE.exists():
        SNAP_FILE.unlink()


def test_first_run_creates_snapshot():
    cleanup()
    drifted, msg = check_schema_drift(MOCK_SCHEMA)
    assert SNAP_FILE.exists(), "Snapshot file not created"
    assert not drifted, "First run should not report drift"
    print(f"OK: First run created snapshot. Message: {msg}")


def test_same_schema_no_drift():
    drifted, msg = check_schema_drift(MOCK_SCHEMA)
    assert not drifted, "Same schema flagged as drifted"
    print(f"OK: Same schema -> no drift. Message: {msg}")


def test_added_column_detected():
    modified = MOCK_SCHEMA + [
        {"table_name": "employees", "column_name": "phone", "column_type": "VARCHAR"}
    ]
    drifted, msg = check_schema_drift(modified)
    assert drifted, "Added column not detected as drift"
    print(f"OK: Added column detected. Message: {msg}")


def test_removed_column_detected():
    shrunk = MOCK_SCHEMA[:-2]
    drifted, msg = check_schema_drift(shrunk)
    assert drifted, "Removed column not detected as drift"
    print(f"OK: Removed column detected. Message: {msg}")


def test_hash_deterministic():
    h1 = snapshot_schema(MOCK_SCHEMA)
    h2 = snapshot_schema(MOCK_SCHEMA)
    assert h1 == h2, "Same schema produces different hashes"
    print(f"OK: Hash deterministic: {h1}")


if __name__ == "__main__":
    test_first_run_creates_snapshot()
    test_same_schema_no_drift()
    test_added_column_detected()
    test_removed_column_detected()
    test_hash_deterministic()
    cleanup()
