

import logging
import sys
import time

from typing import Dict, Any

from src.extracts.api_extractor import OrderExtractor
from src.transform.cleaner import OrderTransformer
from src.load.db_loader import PostgresLoader
from src.utils.db import get_engine

logging.basicConfig(
    level = logging.INFO,
    formats = "%(asctime)s [%(levelname)s [%(filename)s:%(lineno)d] - %(message)s]",
    handlers =[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class DataQualityError(Exception):

    """ Raised when post-load data quality assertino fail."""
    pass

def run_data_quality_checks(loader: PostgresLoader, expected_min_rows: int) -> None:
    """Validatees destination data integrity after laoding..."""
    logger.info("Expecting post-load data qaulity assertion.")

    current_count = loader.fetch_row_count("fct_orders")
    if current_count < expected_min_rows:
        raise DataQualityError(
            f"Row Count validation failed! Expected at least {expected_min_rows} row, found {current_count}."
        )
    logger.info("Assertion Passed: Row count check satisfied (%d total rows)." , current_count)
def run_pipeline(record_count: int = 250) -> Dict[str,Any]:

    """ Coordinates the full ETL pipeline execution flow."""
    start_time = time.time()
    logger.info(f"Starting Modular ETL Pipeline run...")

    try:
        #1. EXTRACT
        logger.info("--- stage 1: Extraction ---")
        extractor = OrderExtractor()
        raw_orders = extractor.extract_mock_orders(count=record_count)
        raw_snapshot_path = extractor.save_raw_snapshot(raw_orders, source_tag = "orders")

        #2. Transform 
        logger.info("--- stage 2: Transforming ---")
        transformer = OrderTransformer()
        clean_df , quarantined = transformer.validate_and_clean(raw_orders)

        if quarantined:
            transformer.save_quarantined_records(quarantined)

        #3. Load
        logger.info("--- stage 3: Loading ---")
        loader = PostgresLoader()
        rows_upserted = loader.upsert_orders(clean_df)

        #4. Quality assuarance 
        logger.info("--- stage 4: Quality && Integrity Checks ---")
        run_data_quality_checks(loader, expected_min_rows=rows_upserted)

        elapsed = round(time.time() - start_time, 2)
        logger.info('Pipeline run completed successfully in %s seconds.', elapsed)

        return{ 
            "status": "SUCCESS",
            "raw_count": len(raw_orders), 
            "clean_count": len(clean_df),
            "quarantined_count": len(quarantined)
            ,
            "upserted_count": rows_upserted,
            "duration_seconds": elapsed,
            "snapshot_file": str(raw_snapshot_path) 
        }
    except Exception as exc:
        logger.exception("Pipeline failed critically during execution: %s", exc)
        sys.exit(1)

if __name__ == "__main__":

    metrics = run_pipeline(record_count=300)
    print("\n--- Pipeline Run Summary ---")
    for key,value in metrics.items():
        print(f" {key} : {value}")

        