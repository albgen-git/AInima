"""Migrazione live: rimuove psychometric_scores.stile_attaccamento.

Revisione privacy richiesta esplicitamente dall'utente (GDPR art. 9): il
campo poteva contenere "Timoroso/Disorganizzato", una categoria clinica
derivata da uno strumento tipo ECR-R. Indagine preliminare (v. CLAUDE.md
2026-09-06) ha confermato che il matching non lo usa mai (né l'etichetta né
una matrice 4x4 categoriale — matching_engine.eq_score() lavora solo su
ansia_score/evitamento_score continui) — sicuro da rimuovere senza toccare
alcuna logica di scoring.

Dove serve ancora mostrare l'etichetta (solo il pannello admin), viene
ricalcolata al volo dai due punteggi continui via
routers/psychometric.py::calcola_stile_attaccamento() — mai più persistita,
nemmeno in cache.

Idempotente (DROP COLUMN IF EXISTS).

Uso:
    python scripts/migrate_2026_09_06_rimuovi_stile_attaccamento.py            (DB locale)
    python scripts/migrate_2026_09_06_rimuovi_stile_attaccamento.py --render   (DB Render)
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
        SELECT count(*) AS n FROM information_schema.columns
        WHERE table_name = 'psychometric_scores' AND column_name = 'stile_attaccamento'
    """)
    esiste = cur.fetchone()["n"] > 0

    if not esiste:
        print("Colonna 'stile_attaccamento' già assente — nessuna azione.")
        conn.close()
        return

    cur.execute("""
        SELECT count(*) AS n FROM psychometric_scores WHERE stile_attaccamento IS NOT NULL
    """)
    n_valorizzate = cur.fetchone()["n"]

    cur.execute("ALTER TABLE psychometric_scores DROP COLUMN stile_attaccamento")
    conn.commit()
    print(f"Colonna 'stile_attaccamento' rimossa ({n_valorizzate} righe avevano un valore).")
    conn.close()


if __name__ == "__main__":
    main()
