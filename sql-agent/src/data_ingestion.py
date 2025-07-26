import sqlite3
from sqlalchemy import create_engine
import requests
import pandas as pd
from loguru import logger as log
from utils.helper_functions import postgres_connection_string


def main(base_url: str, pg_db: str) -> None:
    log.info('Ingesting data from external Sqlite3 db')
    pg_engine = create_engine(
        postgres_connection_string(pg_db)
    )

    r = requests.get(base_url)

    with open('Chinook.db', 'wb') as f:
        f.write(r.content)
        
    sqlite_conn = sqlite3.connect("Chinook.db")
    table_names = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", sqlite_conn)["name"].tolist()

    for table in table_names:
        df = pd.read_sql(f"SELECT * FROM {table};", sqlite_conn)
        df.to_sql(table, pg_engine, if_exists="replace", index=False)
        print(f"Copied table {table} to PostgreSQL")
        
    sqlite_conn.close()
    log.success(f'Sqlite3 data copied to {pg_db} database')
    
    return


if __name__ == '__main__':
    base_url = "https://storage.googleapis.com/benchmarks-artifacts/chinook/Chinook.db"
    main(base_url=base_url, pg_db='chinook')