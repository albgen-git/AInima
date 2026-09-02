"""Migrazione live: rimuove embedding_visivo_profilo/embedding_visivo_partner_ideale
da physical_profile (v. CLAUDE.md — migrazione AWS Rekognition, RF-11b).

Non più letti da nessun codice (v. matching_engine.load_pool(), stable_v9):
il confronto di somiglianza visiva ora chiama AWS Rekognition CompareFaces
on-demand sulle foto già salvate (foto_profilo_url/foto_partner_ideale_url),
niente di precalcolato/persistito a lungo termine — vale identicamente per
gli utenti reali e per i 1000 profili demo (stesse colonne foto, stesso
storage). DROP e non solo deprecazione silenziosa: nessun consumatore
rimasto in produzione (verificato via grep su backend/), il documento
requisiti segna già il campo come "non più necessario" (§7.2).

Idempotente (DROP COLUMN IF EXISTS, sicuro da rilanciare).

Uso:
    python scripts/migrate_2026_09_03_rimuovi_embedding_visivo.py            (DB locale, da .env PG*)
    python scripts/migrate_2026_09_03_rimuovi_embedding_visivo.py --render   (DB Render, da .env DATABASE_URL)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

SQL = """
ALTER TABLE physical_profile
    DROP COLUMN IF EXISTS embedding_visivo_profilo,
    DROP COLUMN IF EXISTS embedding_visivo_partner_ideale;
"""


def main():
    if "--render" in sys.argv:
        import psycopg2
        import psycopg2.extras
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
        conn = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        from db import get_conn  # noqa: E402

        conn = get_conn()

    cur = conn.cursor()
    cur.execute(SQL)
    conn.commit()
    print("physical_profile: embedding_visivo_profilo/embedding_visivo_partner_ideale rimossi (o già assenti).")
    conn.close()


if __name__ == "__main__":
    main()
