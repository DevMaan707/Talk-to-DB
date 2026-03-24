import os
import socket
import subprocess
import time
import sys

DB_NAME = "talktodb_test"
DB_USER = "testuser"
DB_PASSWORD = "testpass"
DB_PORT = 5433
DB_HOST = "localhost"
DB_URI = os.getenv(
    "DB_URI",
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
CONTAINER = "talktodb_pg"

SQL_SEED = """
CREATE TABLE IF NOT EXISTS employees (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(100),
    salary     DECIMAL(10,2),
    department VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
    order_id   SERIAL PRIMARY KEY,
    product    VARCHAR(100),
    revenue    DECIMAL(10,2),
    quantity   INT,
    order_date DATE DEFAULT CURRENT_DATE
);

TRUNCATE TABLE orders, employees RESTART IDENTITY;

INSERT INTO employees (name, salary, department, created_at) VALUES
    ('Alice',  75000, 'Engineering', '2023-01-10'),
    ('Bob',    62000, 'Marketing',   '2023-03-15'),
    ('Carol',  91000, 'Engineering', '2024-06-01'),
    ('Dave',   54000, 'HR',          '2022-11-20'),
    ('Eve',    83000, 'Engineering', '2024-12-05')
ON CONFLICT DO NOTHING;

INSERT INTO orders (product, revenue, quantity, order_date) VALUES
    ('Widget A', 1500.00, 10, '2024-01-15'),
    ('Widget B', 3200.00, 25, '2024-03-20'),
    ('Gadget X', 8750.00, 5,  '2025-01-10'),
    ('Gadget Y', 450.00,  2,  '2025-02-28'),
    ('Widget A', 2200.00, 15, '2025-03-01')
ON CONFLICT DO NOTHING;
"""


def run(cmd, check=True, capture=False, input_text=None):
    return subprocess.run(
        cmd, shell=True, check=check,
        capture_output=capture, text=True,
        input=input_text
    )


def port_in_use(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        return False
    except OSError:
        return True
    finally:
        sock.close()


def container_exists():
    r = run(f"docker ps -a --filter name={CONTAINER} --format '{{{{.Names}}}}'", capture=True)
    return CONTAINER in r.stdout


def container_running():
    r = run(f"docker ps --filter name={CONTAINER} --format '{{{{.Names}}}}'", capture=True)
    return CONTAINER in r.stdout


def start():
    if container_running():
        print(f"OK: container '{CONTAINER}' already running on port {DB_PORT}")
        return

    if port_in_use(DB_HOST, DB_PORT):
        print(f"INFO: port {DB_PORT} is already in use. Skipping Docker start.")
        return

    if container_exists():
        print(f"RESTART: existing container '{CONTAINER}'")
        run(f"docker start {CONTAINER}")
    else:
        print(f"DOCKER: creating PostgreSQL container on port {DB_PORT}...")
        run(
            f"docker run -d "
            f"--name {CONTAINER} "
            f"-e POSTGRES_DB={DB_NAME} "
            f"-e POSTGRES_USER={DB_USER} "
            f"-e POSTGRES_PASSWORD={DB_PASSWORD} "
            f"-p {DB_PORT}:5432 "
            f"postgres:15"
        )

    print("WAIT: PostgreSQL startup", end="", flush=True)
    for _ in range(30):
        r = run(
            f"docker exec {CONTAINER} pg_isready -U {DB_USER} -d {DB_NAME}",
            check=False, capture=True
        )
        if r.returncode == 0:
            print(" ready")
            break
        print(".", end="", flush=True)
        time.sleep(1)
    else:
        print("\nFAIL: PostgreSQL did not become ready in time.")
        sys.exit(1)


def seed_via_docker():
    print("SEED: inserting test data via Docker...")
    run(
        f"docker exec -i {CONTAINER} "
        f"psql -v ON_ERROR_STOP=1 -U {DB_USER} -d {DB_NAME}",
        input_text=SQL_SEED
    )
    print("OK: seed data inserted.")


def seed_direct():
    print("SEED: inserting test data via direct connection...")
    try:
        from sqlalchemy import create_engine, text
    except Exception as e:
        print(f"FAIL: SQLAlchemy not available: {e}")
        return False

    try:
        engine = create_engine(DB_URI)
        statements = [s.strip() for s in SQL_SEED.split(";") if s.strip()]
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
        print("OK: seed data inserted.")
        return True
    except Exception as e:
        print(f"FAIL: direct seed failed: {e}")
        return False


def seed():
    if container_running():
        seed_via_docker()
    else:
        seed_direct()


def stop():
    print(f"STOP: stopping container '{CONTAINER}'...")
    run(f"docker stop {CONTAINER}", check=False)
    print("OK: stopped.")


def destroy():
    stop()
    print(f"REMOVE: removing container '{CONTAINER}'...")
    run(f"docker rm {CONTAINER}", check=False)
    print("OK: removed.")


def status():
    if container_running():
        r = run(
            f"docker exec {CONTAINER} "
            f"psql -U {DB_USER} -d {DB_NAME} "
            f"-c \"SELECT COUNT(*) FROM employees;\"",
            check=False, capture=True
        )
        if r.returncode == 0:
            print(f"OK: DB reachable. Output:\n{r.stdout.strip()}")
        else:
            print(f"FAIL: DB not reachable:\n{r.stderr.strip()}")
        return

    print("INFO: no Docker container running. Checking direct connection...")
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(DB_URI)
        with engine.connect() as conn:
            res = conn.execute(text("SELECT COUNT(*) FROM employees;"))
            count = res.scalar()
        print(f"OK: DB reachable. employees count = {count}")
    except Exception as e:
        print(f"FAIL: DB not reachable: {e}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"
    actions = {
        "start": lambda: (start(), seed()),
        "stop": stop,
        "destroy": destroy,
        "status": status,
        "seed": seed
    }
    if cmd not in actions:
        print("Usage: python setup_docker_db.py [start|stop|destroy|status|seed]")
        sys.exit(1)
    actions[cmd]()
