

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
import pandas as pd
from pydantic import ValidationError

from configuration.settings import PROCESSED_DATA_DIR
from src.transform.schemas import OrderRecordModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class OrderTransformer:
    """Validates raws records, filters invalid anomalies, and 
    outputs cleaned DataFrames."""

    def __init__(self, processed_dir: Path = PROCESSED_DATA_DIR):
        self.processed_dir = processed_dir 
        self.processed_dir.mkdir(parents=True ,exist_ok= True)
    def validate_and_clean(
        self, raw_records: List[Dict[str, Any]]
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Validate records against OrderRecordModel.
        Split into: 
         - df_clean :  validated records prepared as a pandas DataFrame
         - Quarantined: invalid records containing validation error metadata

        """
        valid_records: List[Dict[str, Any]] = []
        quarantined: List[Dict[str,Any]] = []

        for record in raw_records:
            try :
                validated = OrderRecordModel(**record)
                # convert back to dict with native Python/datetime objects
                valid_records.append(validated.model_dump())
            except ValidationError as err:
                quarantined.append({
                    "raw_record" : record,
                    "errors": [
                        {"loc": e["loc"], "msg": e["msg"], "type": e["type"]}
                        for e in err.errors()
                    ]
                })

        if not valid_records:
            logging.warning("No records passed validation.")
            return pd.DataFrame(), quarantined
        df_clean = pd.DataFrame(valid_records)

        # 1. Deduplicated by primary key keeping the latest entry 
        initialied_count = len(df_clean)
        df_clean = df_clean.drop_duplicates(subset=["order_id"], keep="last")
        dupes_dropped = initialied_count - len(df_clean)

        if dupes_dropped > 0:
            logging.info("Dropped %d duplicate order record.", dupes_dropped)

        # 2. Ensure order_timestamp is a timezone-aware UTC datetime
        df_clean["order_timestamp"] = pd.to_datetime(df_clean["order_timestamp"], utc=True)
        logging.info(
            " Transformation complete: %d valid records , %d quarantined records.",
            len(df_clean),
            len(quarantined)
        )
        return df_clean, quarantined
    def save_quarantined_records( self, quarantined: List[Dict[str, Any]], filename: str = "quarantined_orders.json")-> Path:
        """store malformed records in data/processed/ for audit and debugging."""

        target_path = self.processed_dir / filename 
        with open(target_path, "w", encoding= "utf-8") as f:
            json.dump(quarantined, f, indent=2)
        logging.info("Quarantined records saved to: %s", target_path)
        return target_path

if __name__ == "__main__": 
    from src.extracts.api_extractor import OrderExtractor

    extractor = OrderExtractor()
    raw_orders = extractor.extract_mock_orders(count=100)

    transformer = OrderTransformer()
    clean_df, bad_records = transformer.validate_and_clean(raw_orders)

    if bad_records:
        transformer.save_quarantined_records(bad_records)

    print("\n--- Cleaned DataFrame Preview ---")
    print(clean_df.head(5))
    print(f"\nDataFrame Info:\nShape: {clean_df.shape}")