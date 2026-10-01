# Data Pipeline

A small end-to-end ETL project that generates synthetic e-commerce order data, validates it, quarantines bad rows, and loads clean records into PostgreSQL using idempotent upserts.

## Overview

The pipeline is organized into three main stages:

- Extraction: generate realistic raw order records or fetch from an API endpoint
- Transformation: validate records, normalize email and status fields, remove duplicates, and quarantine invalid data
- Loading: write clean data to PostgreSQL using `INSERT ... ON CONFLICT DO UPDATE`

This project is designed to be easy to understand, test, and extend for learning and portfolio use.

## Features

- Synthetic data generation with Faker
- Raw snapshot persistence in `data/raw/`
- Data validation with Pydantic models
- Quarantine output for bad records
- Duplicate handling with latest-record-wins logic
- PostgreSQL upsert into `fct_orders`
- Data quality checks after load
- Pytest coverage for transform logic

## Project structure

```text
.
├── configuration/
│   └── settings.py
├── data/
│   ├── processed/
│   └── raw/
├── src/
│   ├── extracts/
│   │   └── api_extractor.py
│   ├── load/
│   │   └── db_loader.py
│   ├── scripts/
│   │   └── init_db.py
│   ├── transform/
│   │   ├── cleaner.py
│   │   └── schemas.py
│   └── utils/
│       └── db.py
├── tests/
│   └── test_transform.py
├── .env.example
├── .gitignore
├── main.py
├── requirements.txt
├── taks.tf
└── README.md
```

## Requirements

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

The project uses:

- Python 3.10+
- pandas
- SQLAlchemy
- pydantic
- python-dotenv
- faker
- psycopg2-binary
- pytest
- requests

## Environment configuration

Create a local `.env` file using the example:

```bash
cp .env.example .env
```

Example `.env` values:

```env
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=analytics_db
```

## Database setup

Make sure PostgreSQL is running locally and the `analytics_db` database exists.

The project expects a table like this:

```sql
CREATE TABLE IF NOT EXISTS fct_orders (
    order_id TEXT PRIMARY KEY,
    customer_id INT NOT NULL,
    customer_email TEXT NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    status TEXT NOT NULL,
    order_timestamp TIMESTAMPTZ NOT NULL,
    loaded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

You can also initialize it with the script:

```bash
python -m src.scripts.init_db
```

## Run the pipeline

From the project root:

```bash
python main.py
```

This will:

1. generate synthetic orders
2. save a raw JSON snapshot
3. validate and clean the data
4. quarantine invalid rows
5. upsert rows to PostgreSQL
6. print a summary of the run

## Test the transformer

```bash
pytest -q
```

## Notes

- Invalid or malformed records are not dropped silently; they are saved to `data/processed/quarantined_orders.json`.
- Duplicate `order_id` rows are collapsed by keeping the latest record.
- Email addresses are normalized to lowercase and trimmed.
- Status values are normalized to uppercase.

## Example output

```text
--- Pipeline Run Summary ---
status : SUCCESS
raw_count : 300
clean_count : 278
quarantined_count : 22
upserted_count : 278
duration_seconds : 1.87
snapshot_file : /.../data/raw/orders_raw_20260101_120000.json
```

## Next improvements

- connect the extractor to a real API endpoint
- add Docker Compose for PostgreSQL and the app
- add Airflow or Prefect orchestration
- add CI/CD checks and linting
- add monitoring and observability
