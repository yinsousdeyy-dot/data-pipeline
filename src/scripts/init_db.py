import os
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Resolve the project root directory (etl_modular)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
TARGET_DB = os.getenv("DB_NAME", "analytics_db")

def create_database():
    conn = psycopg2.connect(
        dbname="postgres",
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{TARGET_DB}';")
    exists = cursor.fetchone()

    if not exists:
        cursor.execute(f"CREATE DATABASE {TARGET_DB};")
        print(f"[OK] Database '{TARGET_DB}' created successfully.")
    else:
        print(f"[INFO] Database '{TARGET_DB}' already exists.")

    cursor.close()
    conn.close()

def run_ddl():
    # Look for either create_tables.sql or init_schema.sql in sql/ddl/
    ddl_dir = BASE_DIR / "sql" / "ddl"
    
    candidate_files = [
        ddl_dir / "create_tables.sql",
        ddl_dir / "init_schema.sql"
    ]
    
    ddl_path = next((f for f in candidate_files if f.exists()), None)
    
    if not ddl_path:
        # Fallback: create the file with default schema if missing
        ddl_dir.mkdir(parents=True, exist_ok=True)
        ddl_path = ddl_dir / "create_tables.sql"
        default_sql = """
        CREATE TABLE IF NOT EXISTS fct_orders (
            order_id VARCHAR(64) PRIMARY KEY,
            customer_id INT NOT NULL,
            customer_email VARCHAR(255) NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            status VARCHAR(20) NOT NULL,
            order_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_fct_orders_customer ON fct_orders(customer_id);
        """
        ddl_path.write_text(default_sql, encoding="utf-8")
        print(f"[INFO] Created default DDL file at: {ddl_path}")

    conn = psycopg2.connect(
        dbname=TARGET_DB,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()

    with open(ddl_path, "r", encoding="utf-8") as f:
        ddl_sql = f.read()

    cursor.execute(ddl_sql)
    conn.commit()
    print(f"[OK] Executed DDL script from: {ddl_path}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    create_database()
    run_ddl()