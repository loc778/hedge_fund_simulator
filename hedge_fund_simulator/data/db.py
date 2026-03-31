# data/db.py
# Shared database utilities used by all scripts

from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import insert
from dotenv import load_dotenv
from urllib.parse import quote_plus
import os

load_dotenv()

def get_engine():
    user = os.getenv('DB_USER')
    password = quote_plus(os.getenv('DB_PASSWORD'))
    host = os.getenv('DB_HOST')
    db = os.getenv('DB_NAME')

    DB_URL = f"mysql+mysqlconnector://{user}:{password}@{host}/{db}"
    
    print("DEBUG DB_URL:", DB_URL)   # 👈 ADD THIS

    return create_engine(DB_URL, pool_pre_ping=True, pool_recycle=3600)
def upsert_ignore(table, conn, keys, data_iter):
    """Insert rows, silently skip if duplicate key exists"""
    stmt = insert(table.table).prefix_with("IGNORE")
    data = [dict(zip(keys, row)) for row in data_iter]
    conn.execute(stmt, data)

def save_to_db(df, table_name, engine):
    """
    Standard save function used by all scripts.
    Handles chunking automatically for large datasets.
    When you scale to 500 stocks / 10 years (~500k rows),
    chunking prevents memory crashes.
    """
    total = len(df)
    chunk_size = 5000   # Save 5000 rows at a time

    print(f"💾 Saving {total:,} rows to {table_name}...")

    df.to_sql(
        name=table_name,
        con=engine,
        if_exists="append",
        index=False,
        method=upsert_ignore,
        chunksize=chunk_size    # Critical for large datasets
    )

    print(f"✅ Saved {total:,} rows to {table_name}")