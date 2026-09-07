"""Migrazione live: rimozione del vecchio spareggio estetico (upload
libero della foto "partner ideale", RF-11a/b originale) — sostituito per
intero dal torneo estetico (RF-08b/c, v. CLAUDE.md 2026-09-06/07).

Rimuove:
- physical_profile.foto_partner_ideale_url
- matches.selezionato_per_somiglianza_visiva

Aggiorna la descrizione di system_config.dimensione_shortlist_analisi_visiva
(non più legata al vecchio spareggio, resta solo per la dimensione della
shortlist di audit RF-11a) e registra stable_v13 in
matching_algorithm_versions.

Idempotente (DROP COLUMN IF EXISTS, INSERT ON CONFLICT).

Uso:
    python scripts/migrate_2026_09_07_rimuovi_vecchio_spareggio_estetico.py            (DB locale)
    python scripts/migrate_2026_09_07_rimuovi_vecchio_spareggio_estetico.py --render   (DB Render)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

SQL = """
ALTER TABLE physical_profile DROP COLUMN IF EXISTS foto_partner_ideale_url;
ALTER TABLE matches DROP COLUMN IF EXISTS selezionato_per_somiglianza_visiva;

UPDATE system_config SET descrizione =
    'Numero di candidati Top N per compatibilità caratteriale persistiti come shortlist di audit (RF-11a)'
WHERE chiave = 'dimensione_shortlist_analisi_visiva';

INSERT INTO matching_algorithm_versions (versione, descrizione) VALUES
    ('stable_v13', 'Rimosso il vecchio spareggio estetico (upload libero della foto "partner ideale", RF-11a/b originale, sempre attivo sulla shortlist) — sostituito per intero dal torneo estetico (RF-08b/c, stable_v12), oggi l''unico spareggio estetico del sistema. matching_engine.somiglianza_visiva()/seleziona_per_somiglianza_visiva() rimosse, non solo disattivate.')
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
    cur.execute(SQL)
    conn.commit()
    print("Vecchio spareggio estetico rimosso (foto_partner_ideale_url, selezionato_per_somiglianza_visiva).")
    conn.close()


if __name__ == "__main__":
    main()
