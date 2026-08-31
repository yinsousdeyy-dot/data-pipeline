

import json 
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from faker import Faker
import requests

from configuration.settings import DATABASE_URL 
from configuration.settings import RAW_DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
fake = Faker()

class OrderExtractor:
    """
        Handles extracting order records from REST endpoints or synthetic generation
    """
    def __init__(self, raw_dir: Optional[Path] = None): 

        self.raw_dir = raw_dir or RAW_DATA_DIR
        self.raw_dir.mkdir(parents=True, exist_ok= True)

    def extract_mock_orders(self, count: int = 500 ) -> List[Dict[str, Any]]:
        """
        Generates realistic synthetic e-commerce orders.
        Deliberately injects edges cases (nulls, irrugalar casing, whitespace, outlines),
        """
        records: List[Dict[str, Any]] = [] 
        statues = ["Completed", "Pending", "Canceled", "Refused", None]

        logging.info("Generating %d synthetic order records with Faker..", count)

        for _ in range(count) :
            # Intentially inject dirty formatting anomalies 
            email =fake.email()
            if random.random() < 0.08: 
                email = f" {email.upper()}" # Whitespace & casing edge case

            amount = round(random.uniform(5.0, 1200.0), 2)
            if random.random() < 0.03 :
                amount = -25.50 # Corrupts negative value

            record = {
                "order_id" : fake.uuid4(),
                "customer_id" :random.randint(1001, 1080),
                "customer_email" :email,
                "amount" : amount,
                "status": random.choice(statues),
                "order_timestamp": fake.date_time_this_year().isoformat()
            }
            records.append(record)

        return records
    def extract_from_api(self, endpoint_url: str, params: Optional[Dict[str,Any]]= None, timeout: int = 15) -> List[Dict[str,Any]]:
        """Fetches raw JOSN payload from an external REST API with standard HTTP error handling."""
        logging.info("Fetching data from API ENDPOINT: %s", endpoint_url)

        try:
            response = requests.get(endpoint_url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                return data
            elif isinstance(data,dict) and "data" in data:
                return data["data"]
            return [data]

        except requests.exceptions.RequestException as e:
            logging.error("Failed to fetch data from API endpoint %s: %s", endpoint_url, e)
            raise

    def save_raw_snapshot(self, payload: List[Dict[ str, Any]], source_tag: str = "orders") -> Path:
        """" Perists the exact raw payload to data/raw with and ISO-style UTC timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source_tag}_raw_{timestamp}.json"
        target_path = self.raw_dir / filename

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        logging.info("Successfully persisted %d raw records to: %s", len(payload), target_path)
        return target_path


if __name__ ==  "__main__":
    extractor = OrderExtractor()
    #1. Generate synthetic batch 
    mock_payload = extractor.extract_mock_orders(count=200)

    #2. Stage immutable snapshot in data/raw/
    saved_file = extractor.save_raw_snapshot(mock_payload, source_tag="orders_mock")
    print(f"[OK] Raw stage completed -> {saved_file}")

