import logging
from typing import Optional 
import pandas as pd 
from sqlalchemy import text
from sqlalchemy.engine import Engine 

from src.utils.db import get_engine 

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class PostgresLoader:
    """Manage loading cleaned dataframes into PostgreSQL using idempotent upsert operations."""
    def __init__(self, engine: Optional[Engine] =None):
        self.engine = engine or get_engine()

    def upsert_orders(self, df: pd.DataFrame, table_name: str = "fct_orders") -> int: 
        """
        Performs an idempotent upsert into the target analytical table.
        Inserts new order_ids and updates existing rows with latest values.
        """
        if df.empty:
            logging.warning("Received empty DataFrame. Skipping database load.")
            return 0
        # Parameterized PostgreSQL ON CONFLICT statement 
        upsert_stmt = text(
            f"""
                INSERT INTO {table_name}(
                    order_id,
                    customer_id,
                    customer_email,
                    amount,
                    status,
                    order_timestamp
                ) VALUES (
                    :order_id,
                    :customer_id,
                    :customer_email,
                    :amount,
                    :status,
                    :order_timestamp
                )
                ON CONFLICT (order_id) DO UPDATE SET
                    customer_id = EXCLUDED.customer_id,
                    customer_email = EXCLUDED.customer_email,
                    amount = EXCLUDED.amount , 
                    order_timestamp = EXCLUDED.order_timestamp,
                    loaded_at = CURRENT_TIMESTAMP;

            """
        )
        # the bug was that i was rewriting : amount=EXCLUDED.status TO amount=EXCLUDED.amount
        # the hint said: I will need to rewrite or cast the expression.

        # Convert DataFrame to list of dicts for batch execution 
        # Convert timestamp columns to strings or native datetime objects
        payload = df.to_dict(orient="records")

        # Atomic transaction: automatically commits on exit or rolls back on exception 
        with self.engine.begin() as conn:
            conn.execute(upsert_stmt, payload)

        logging.info("Successfully upserted %d records into target table '%s'.", len(payload), table_name)
        return len(payload)

    def fetch_row_count(self, table_name: str = "fct_orders") -> int:
        """Helper to verify current records counts in destination table."""
        query = text(f"SELECT COUNT(*) FROM {table_name};")
        with self.engine.connect() as conn:
            count = conn.execute(query).scalar()
            return count or 0

if __name__ == "__main__":
    from src.extracts.api_extractor import OrderExtractor
    from src.transform.cleaner import OrderTransformer

    #1. extract 
    extracter = OrderExtractor()
    raw_data = extracter.extract_mock_orders(count=50)

    #2. transformer 
    transformer = OrderTransformer()
    clean_df, _ = transformer.validate_and_clean(raw_data)

    #3. Load and verify
    loader = PostgresLoader()
    upserted_count =loader.upsert_orders(clean_df)
    total_table_rows= loader.fetch_row_count()

    print(f"\n[OK] Upserted {upserted_count} records.")
    print(f"[OK] Total rows currentyl in fct_orders: {total_table_rows}")



