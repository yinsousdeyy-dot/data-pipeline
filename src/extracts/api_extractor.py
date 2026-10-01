import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from faker import Faker

from configuration.settings import RAW_DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
fake = Faker()


class OrderExtractor:
    """
    Handles extracting order records from REST endpoints or synthetic generation.
    Supports both mock data generation and real API integration.
    """

    def __init__(self, raw_dir: Optional[Path] = None):
        self.raw_dir = raw_dir or RAW_DATA_DIR
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def extract_mock_orders(self, count: int = 500) -> List[Dict[str, Any]]:
        """Generates realistic synthetic e-commerce orders."""
        records: List[Dict[str, Any]] = []
        statuses = ["Completed", "Pending", "Canceled", "Refused", None]

        logging.info("Generating %d synthetic order records with Faker.", count)

        for _ in range(count):
            email = fake.email()
            if fake.pybool():
                email = f" {email.upper()}"

            amount = round(fake.pydecimal(left_digits=4, right_digits=2, positive=True), 2)
            if fake.pybool():
                amount = -abs(amount)

            record = {
                "order_id": fake.uuid4(),
                "customer_id": fake.random_int(min=1001, max=1080),
                "customer_email": email,
                "amount": float(amount),
                "status": fake.random_element(elements=statuses),
                "order_timestamp": fake.date_time_this_year().isoformat(),
            }
            records.append(record)

        return records

    def extract_from_api(
        self,
        endpoint_url: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 15,
        auth: Optional[tuple] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetches raw JSON payload from an external REST API with standard HTTP error handling.
        
        Args:
            endpoint_url: Full URL to the API endpoint
            params: Query parameters to pass to the API
            timeout: Request timeout in seconds
            auth: Optional tuple of (username, password) for HTTP Basic Auth
            
        Returns:
            List of records from the API
        """
        logging.info("Fetching data from API endpoint: %s", endpoint_url)

        try:
            headers = {"Accept": "application/json"}
            response = requests.get(
                endpoint_url, 
                params=params, 
                timeout=timeout,
                headers=headers,
                auth=auth
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            if isinstance(data, dict) and "results" in data:
                return data["results"]
            if isinstance(data, dict):
                return [data]
            return []

        except requests.exceptions.Timeout:
            logging.error("API request timed out after %d seconds to %s", timeout, endpoint_url)
            raise
        except requests.exceptions.ConnectionError as exc:
            logging.error("Failed to connect to API endpoint %s: %s", endpoint_url, exc)
            raise
        except requests.exceptions.HTTPError as exc:
            logging.error("HTTP error from API %s: %s", endpoint_url, exc)
            raise
        except requests.exceptions.RequestException as exc:
            logging.error("Failed to fetch data from API endpoint %s: %s", endpoint_url, exc)
            raise

    def normalize_api_records(self, api_records: List[Dict[str, Any]], count: int = 500) -> List[Dict[str, Any]]:
        """
        Normalize API records to match OrderRecordModel schema.
        Maps common API response formats to order fields.
        """
        normalized = []
        
        for item in api_records[:count]:
            if not isinstance(item, dict):
                logging.warning("Skipping non-dict record: %s", item)
                continue

            # Map API fields to order schema
            order_id = str(item.get("id") or item.get("order_id") or fake.uuid4())
            customer_id = item.get("customer_id", fake.random_int(min=1001, max=1080))
            customer_email = item.get("email") or item.get("customer_email") or fake.email()
            amount = item.get("amount") or item.get("total") or round(
                fake.pydecimal(left_digits=4, right_digits=2, positive=True), 2
            )
            status = item.get("status") or fake.random_element(
                elements=["Completed", "Pending", "Canceled", "Refused"]
            )
            order_timestamp = item.get("timestamp") or item.get("created_at") or item.get("date") or fake.date_time_this_year().isoformat()

            # Ensure types are correct
            if not isinstance(customer_id, int):
                try:
                    customer_id = int(customer_id)
                except (ValueError, TypeError):
                    customer_id = fake.random_int(min=1001, max=1080)

            if not isinstance(amount, (int, float)):
                try:
                    amount = float(amount)
                except (ValueError, TypeError):
                    amount = round(fake.pydecimal(left_digits=4, right_digits=2, positive=True), 2)

            normalized.append(
                {
                    "order_id": order_id,
                    "customer_id": customer_id,
                    "customer_email": customer_email,
                    "amount": amount,
                    "status": status,
                    "order_timestamp": order_timestamp,
                }
            )

        logging.info("Normalized %d API records to order schema.", len(normalized))
        return normalized

    def extract_orders(
        self,
        count: int = 500,
        use_api: bool = False,
        endpoint_url: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return either synthetic or external API orders based on configuration.
        Falls back to synthetic data if API fails.
        
        Args:
            count: Number of records to extract
            use_api: If True, attempt to fetch from API; else generate synthetic
            endpoint_url: Override default API endpoint URL
            params: Query parameters for the API
            
        Returns:
            List of order records
        """
        if use_api:
            url = endpoint_url or os.getenv("API_BASE_URL", "https://jsonplaceholder.typicode.com/posts")
            timeout = int(os.getenv("API_TIMEOUT_SECONDS", "15"))
            
            try:
                data = self.extract_from_api(url, params=params, timeout=timeout)
                
                if not data:
                    logging.warning("API returned empty response. Falling back to mock data.")
                    return self.extract_mock_orders(count=count)
                
                normalized = self.normalize_api_records(data, count=count)
                
                if not normalized:
                    logging.warning("Failed to normalize API records. Falling back to mock data.")
                    return self.extract_mock_orders(count=count)
                
                logging.info("Successfully extracted %d records from API.", len(normalized))
                return normalized
                
            except Exception as exc:
                logging.warning("API extraction failed (%s). Falling back to mock data.", str(exc))
                return self.extract_mock_orders(count=count)

        return self.extract_mock_orders(count=count)

    def save_raw_snapshot(self, payload: List[Dict[str, Any]], source_tag: str = "orders") -> Path:
        """Persists the exact raw payload to data/raw with an ISO-style UTC timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source_tag}_raw_{timestamp}.json"
        target_path = self.raw_dir / filename

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        logging.info("Successfully persisted %d raw records to: %s", len(payload), target_path)
        return target_path


if __name__ == "__main__":
    extractor = OrderExtractor()
    
    # Generate synthetic batch
    mock_payload = extractor.extract_mock_orders(count=200)
    saved_file = extractor.save_raw_snapshot(mock_payload, source_tag="orders_mock")
    print(f"[OK] Raw stage completed -> {saved_file}")
    
    # Test API extraction (optional)
    api_url = os.getenv("API_BASE_URL", "https://jsonplaceholder.typicode.com/posts")
    print(f"\n[INFO] To test API extraction, set USE_API_DATA=true and API_BASE_URL={api_url}")
