"""Migrazione live: inserisce la riga stable_v11 in matching_algorithm_versions.

Collega la seconda metà del filtro hard "Coerenza su figli"
(Ainima_Algoritmo_Ranking_Finale_v1.md §2: "ha_figli/pref_accetta_figli E
pref_desidera_figli_futuri reciprocamente compatibili") — trovato durante un
audit richiesto esplicitamente dall'utente sui filtri hard non ancora
collegati (v. CLAUDE.md, stesso audit che ha anche portato a stable_v10 per
pref_stato_civile_accettato). Solo la prima metà (ha_figli/pref_accetta_figli)
era già implementata; pref_desidera_figli_futuri (pianificazione familiare
propria di ciascuno, non una preferenza sul partner) non veniva mai
confrontato reciprocamente. Regola: un contrasto diretto Sì↔No tra i due
lati è un'incompatibilità di piani di vita, sempre esclusa; "Da valutare" o
un dato non ancora compilato non escludono mai.

Idempotente (ON CONFLICT DO NOTHING, sicuro da rilanciare).

Uso:
    python scripts/migrate_2026_09_05_stable_v11_desidera_figli_futuri.py            (DB locale)
    python scripts/migrate_2026_09_05_stable_v11_desidera_figli_futuri.py --render   (DB Render)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

DESCRIZIONE = (
    "Collegata la seconda metà del filtro hard \"Coerenza su figli\" (Ainima_Algoritmo_Ranking_Finale_v1.md "
    "§2): pref_desidera_figli_futuri (pianificazione familiare propria di ciascuno, Sì/No/Da valutare) ora "
    "esclude reciprocamente quando i due lati sono in contrasto diretto Sì↔No — piano di vita fondamentale, "
    "mai negoziabile. 'Da valutare' o dato mancante non escludono in nessuna direzione. Trovato durante un "
    "audit sui filtri hard STEP 0 documentati ma non ancora collegati (stesso audit di stable_v10)."
)

SQL = """
INSERT INTO matching_algorithm_versions (versione, descrizione) VALUES
    ('stable_v11', %s)
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
    print("matching_algorithm_versions: riga stable_v11 inserita (o già presente).")
    conn.close()


if __name__ == "__main__":
    main()
