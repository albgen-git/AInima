"""Connessione condivisa a PostgreSQL. Ogni richiesta apre/chiude la propria
connessione (semplice e sufficiente per un MVP a basso traffico; da rivedere
con un connection pool prima di produzione)."""

import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))


def get_conn():
    return psycopg2.connect(
        host=os.environ["PGHOST"], port=os.environ["PGPORT"],
        user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"],
        dbname=os.environ["PGDATABASE"],
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def get_db():
    """Dependency FastAPI: apre una connessione per la durata della richiesta."""
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()
