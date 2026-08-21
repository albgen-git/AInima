"""Ricalcola system_config.soglia_similarita_visiva_minima (RF-11a/RF-11b,
v. CLAUDE.md 2026-08-20) sul percentile target (soglia_percentile_
similarita_visiva) della distribuzione REALE di similarità ArcFace tra
coppie CASUALI del pool corrente (foto "partner ideale" di uno vs foto
profilo di un altro, senza alcuna relazione) — non un valore assoluto
scelto a occhio come il precedente 0.20.

Nessuno scheduler reale: va rilanciato manualmente man mano che il pool
cambia composizione, stesso limite già accettato per il centroide tag
(v. scripts/migrate_2026_08_20_centroide_tag_embedding.py).

Uso: python scripts/ricalcola_soglia_visiva.py
"""

import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402

N_CAMPIONE = 5000


def cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def main():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT valore FROM system_config WHERE chiave = 'soglia_percentile_similarita_visiva'")
    riga = cur.fetchone()
    percentile_target = float(riga["valore"]) if riga else 0.90

    cur.execute("""
        SELECT embedding_visivo_profilo, embedding_visivo_partner_ideale
        FROM physical_profile WHERE embedding_visivo_profilo IS NOT NULL
    """)
    righe = cur.fetchall()
    profili = [r["embedding_visivo_profilo"] for r in righe]
    ideali = [r["embedding_visivo_partner_ideale"] for r in righe if r["embedding_visivo_partner_ideale"] is not None]

    if len(profili) < 20 or len(ideali) < 20:
        print(f"Campione insufficiente (profili={len(profili)}, ideali={len(ideali)}) — soglia non ricalcolata.")
        conn.close()
        return

    rng = random.Random(2026)
    campione = sorted(
        cos(rng.choice(ideali), rng.choice(profili)) for _ in range(N_CAMPIONE)
    )
    indice = min(len(campione) - 1, int(len(campione) * percentile_target))
    nuova_soglia = campione[indice]

    cur.execute(
        "UPDATE system_config SET valore = %s WHERE chiave = 'soglia_similarita_visiva_minima'",
        (str(round(nuova_soglia, 4)),),
    )
    conn.commit()
    conn.close()

    print(f"Campione: {N_CAMPIONE} coppie casuali (profili={len(profili)}, ideali={len(ideali)})")
    print(f"Percentile target: {percentile_target}")
    print(f"Nuova soglia_similarita_visiva_minima: {nuova_soglia:.4f}")


if __name__ == "__main__":
    main()
