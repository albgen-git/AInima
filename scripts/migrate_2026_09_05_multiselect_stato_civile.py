"""Migrazione live: soft_criteria.pref_stato_civile_accettato da VARCHAR(30)
(scelta libera testuale) a TEXT[] (multi-selezione), richiesta esplicita
dell'utente — v. CLAUDE.md 2026-09-05.

I valori legacy non-NULL (testo libero, es. "Nubile", "Single???!") non
vengono interpretati/corretti in una delle 4 opzioni canoniche — vengono
preservati così come sono, incapsulati come array a un elemento, per non
"correggere" silenziosamente un dato storico (stessa filosofia già seguita
altrove nel progetto, es. seed_real_test_fixtures.py).

Uso:
    python scripts/migrate_2026_09_05_multiselect_stato_civile.py            (DB locale)
    python scripts/migrate_2026_09_05_multiselect_stato_civile.py --render   (DB Render)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


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

    cur.execute("""
        SELECT data_type FROM information_schema.columns
        WHERE table_name = 'soft_criteria' AND column_name = 'pref_stato_civile_accettato'
    """)
    tipo_attuale = cur.fetchone()["data_type"]

    if tipo_attuale == "ARRAY":
        print("Colonna già TEXT[] — migrazione già applicata, nessuna azione.")
        conn.close()
        return

    cur.execute("""
        ALTER TABLE soft_criteria
        ALTER COLUMN pref_stato_civile_accettato TYPE TEXT[]
        USING (
            CASE WHEN pref_stato_civile_accettato IS NULL THEN NULL
                 ELSE ARRAY[pref_stato_civile_accettato]
            END
        )
    """)
    conn.commit()
    print("Colonna pref_stato_civile_accettato convertita a TEXT[].")

    cur.execute("""
        SELECT user_id, pref_stato_civile_accettato FROM soft_criteria
        WHERE pref_stato_civile_accettato IS NOT NULL
    """)
    righe = cur.fetchall()
    print(f"{len(righe)} righe con valore non-NULL preservate come array a 1 elemento:")
    for r in righe:
        print(" ", dict(r))

    conn.close()


if __name__ == "__main__":
    main()
