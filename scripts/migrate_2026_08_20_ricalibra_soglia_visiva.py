"""Migrazione live: nuovi parametri system_config per la ricalibrazione
della soglia del tie-break visivo RF-11a/RF-11b (v. CLAUDE.md 2026-08-20 —
test di matching reale Pietro/Lena Gallo) + bump a stable_v5 in
matching_algorithm_versions. Nessun Alembic nel progetto — pattern ad-hoc
già usato per le migrazioni precedenti.

Uso: python scripts/migrate_2026_08_20_ricalibra_soglia_visiva.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402


def main():
    conn = get_conn()
    cur = conn.cursor()

    print("1. Nuovi parametri system_config...")
    cur.execute("""
        INSERT INTO system_config (chiave, valore, descrizione) VALUES
            ('soglia_percentile_similarita_visiva', '0.90', 'Percentile target (0-1) della distribuzione di similarità ArcFace tra coppie casuali del pool, usato per ricalcolare soglia_similarita_visiva_minima'),
            ('soglia_similarita_visiva_minima', '0.20', 'Soglia minima di somiglianza visiva (RF-11a/RF-11b) sotto cui il tie-break non scatta — valore CALCOLATO da scripts/ricalcola_soglia_visiva.py sul percentile target sopra, non un default da editare a mano')
        ON CONFLICT (chiave) DO NOTHING
    """)

    print("2. matching_algorithm_versions: aggiungo stable_v5...")
    cur.execute("""
        INSERT INTO matching_algorithm_versions (versione, descrizione) VALUES
            ('stable_v5', 'Ricalibrata la soglia minima del tie-break visivo RF-11a/RF-11b: da valore assoluto fisso (0.20, scelto a occhio) a valore ricalcolato sul percentile target (default 90°) della distribuzione reale di similarità ArcFace tra coppie casuali del pool corrente (system_config.soglia_similarita_visiva_minima/soglia_percentile_similarita_visiva). Trovato durante un test di matching reale che 0.20 era sotto il 66° percentile delle coppie casuali — il tie-break scattava spesso su rumore statistico, non su somiglianza reale.')
        ON CONFLICT (versione) DO NOTHING
    """)

    conn.commit()
    conn.close()
    print("Migrazione completata.")


if __name__ == "__main__":
    main()
