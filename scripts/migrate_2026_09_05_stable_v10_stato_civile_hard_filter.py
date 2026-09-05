"""Migrazione live: inserisce la riga stable_v10 in matching_algorithm_versions.

Collega pref_stato_civile_accettato al filtro hard dello STEP 0
(Ainima_Algoritmo_Ranking_Finale_v1.md §2: "stato civile compatibile con
pref_stato_civile_accettato") — elencato lì fin da subito ma mai
implementato in matching_engine.hard_filters_ok fino a questa richiesta
esplicita dell'utente (v. CLAUDE.md). Filtro RECIPROCO, stesso trattamento
già riservato a età/genere/figli: un candidato C è escluso dal pool di U se
C.stato_civile non è in U.pref_stato_civile_accettato, e viceversa. NULL
(preferenza mai compilata) equivale a "nessun filtro", non a un'esclusione
implicita.

Idempotente (ON CONFLICT DO NOTHING, sicuro da rilanciare).

Uso:
    python scripts/migrate_2026_09_05_stable_v10_stato_civile_hard_filter.py            (DB locale)
    python scripts/migrate_2026_09_05_stable_v10_stato_civile_hard_filter.py --render   (DB Render)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

DESCRIZIONE = (
    "Collegato il filtro hard STEP 0 \"stato civile compatibile con pref_stato_civile_accettato\" "
    "(Ainima_Algoritmo_Ranking_Finale_v1.md §2), elencato nel documento fin dall'origine ma mai "
    "implementato in matching_engine.hard_filters_ok. Filtro reciproco (come età/genere/figli): un "
    "candidato viene escluso se il proprio stato_civile non compare nell'array "
    "pref_stato_civile_accettato dell'altra parte, in entrambe le direzioni. NULL (preferenza non "
    "ancora compilata, es. multi-selezione introdotta il 2026-09-05) equivale a nessun filtro."
)

SQL = """
INSERT INTO matching_algorithm_versions (versione, descrizione) VALUES
    ('stable_v10', %s)
ON CONFLICT (versione) DO NOTHING;
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
    cur.execute(SQL, (DESCRIZIONE,))
    conn.commit()
    print("matching_algorithm_versions: riga stable_v10 inserita (o già presente).")
    conn.close()


if __name__ == "__main__":
    main()
