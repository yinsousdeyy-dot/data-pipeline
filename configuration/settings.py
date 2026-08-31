

# centralize configuration into a single typed module;

import os 
from pathlib import Path 
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent # finds and sets the main folder path for your project.
# resolve():  Cleans the path
# .parent(first one) : Moves up one folder level from your current file to its containing folder.
# .parent(second one) : Moves up one more folder level. This puts you at the main root folder of your entire project.If

# base_dir : represents the root (main) directory
RAW_DATA_DIR = BASE_DIR / "data" / "raw" # data and raw in built-in lib of pathlib are specific folder or subfolder inside base dir

PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

# Database configuration 
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "sousdey2026")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "analytics_db")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
