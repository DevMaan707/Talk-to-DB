DB_PORT = 5433
DB_NAME = "talktodb_test"
DB_USER = "testuser"
DB_PASSWORD = "testpass"
DB_HOST = "localhost"

DB_URI = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

MOCK_SCHEMA = [
    {"table_name": "employees", "column_name": "id",         "column_type": "INTEGER"},
    {"table_name": "employees", "column_name": "name",       "column_type": "VARCHAR"},
    {"table_name": "employees", "column_name": "salary",     "column_type": "DECIMAL"},
    {"table_name": "employees", "column_name": "department", "column_type": "VARCHAR"},
    {"table_name": "employees", "column_name": "created_at", "column_type": "TIMESTAMP"},
    {"table_name": "orders",    "column_name": "order_id",   "column_type": "INTEGER"},
    {"table_name": "orders",    "column_name": "product",    "column_type": "VARCHAR"},
    {"table_name": "orders",    "column_name": "revenue",    "column_type": "DECIMAL"},
    {"table_name": "orders",    "column_name": "quantity",   "column_type": "INTEGER"},
    {"table_name": "orders",    "column_name": "order_date", "column_type": "DATE"},
]
