

from sqlalchemy import create_engine, text
from configuration.settings import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)

def get_engine():
    return engine 

def test_db_connection():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1;")).scalar() # what is scalar function?
        print(f"[OK] Database connected. Ping response: {res}")

if __name__  == "__main__":
    test_db_connection()