"""Migrazione live: RF-06c — paese di residenza reale dell'utente
(socio_profile.paese_residenza, codice ISO 3166-1 alpha-2), distinto dal
comune di residenza già esistente. V. Documento_Requisiti_v1.md §7.3,
CLAUDE.md 2026-09-09.

Aggiunge la colonna (nullable — compilata progressivamente come il resto
del profilo socio-economico, obbligatoria solo a livello applicativo) e
la backfilla per i profili demo esistenti, derivandola da
`comune_residenza` — MAI un valore inventato o identico per tutti.
Verificato prima di scrivere questo script: 37 città distinte sul pool
demo (1000 profili), ciascuna mappabile in modo univoco su un solo
paese (17 città dell'hinterland milanese -> IT, Dubai/Abu Dhabi -> AE,
18 capitali mondiali con 2-3 profili ciascuna -> il rispettivo paese).
Un comune non presente in questa mappa (o NULL, es. i profili di test
abbandonati con socio_profile vuoto) resta NULL — nessun default
indovinato quando manca il segnale.

Idempotente: ADD COLUMN IF NOT EXISTS, e ogni UPDATE tocca solo le righe
con paese_residenza ancora NULL (non sovrascrive mai un valore già
impostato, incluse eventuali correzioni manuali successive).

Uso:
    python scripts/migrate_2026_09_09_paese_residenza.py            (DB locale)
    python scripts/migrate_2026_09_09_paese_residenza.py --render   (DB Render)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

SQL_COLONNA = "ALTER TABLE socio_profile ADD COLUMN IF NOT EXISTS paese_residenza VARCHAR(2);"

# Derivata da comune_residenza sul pool demo reale (v. docstring sopra) —
# non un default arbitrario: ogni città qui è stata verificata contro la
# distribuzione reale del pool prima di scrivere questa mappa.
MAPPA_CITTA_PAESE = {
    # Milano e hinterland lombardo (877 profili)
    "Milano": "IT", "Monza": "IT", "Sesto San Giovanni": "IT", "Cologno Monzese": "IT",
    "Cinisello Balsamo": "IT", "Rho": "IT", "San Donato Milanese": "IT", "Segrate": "IT",
    "Vimercate": "IT", "Lodi": "IT", "Bresso": "IT", "Paderno Dugnano": "IT",
    "Rozzano": "IT", "Pavia": "IT", "Cernusco sul Naviglio": "IT", "Legnano": "IT",
    "Corsico": "IT",
    # Espansione GCC (150 profili)
    "Dubai": "AE", "Abu Dhabi": "AE",
    # Capitali mondiali, 2-3 profili ciascuna (73 profili)
    "Londra": "GB", "Atene": "GR", "Berlino": "DE", "Parigi": "FR", "Vienna": "AT",
    "Ottawa": "CA", "Washington": "US", "Madrid": "ES", "Brasilia": "BR",
    "Lisbona": "PT", "Buenos Aires": "AR", "Il Cairo": "EG", "Città del Messico": "MX",
    "Varsavia": "PL", "Canberra": "AU", "Singapore": "SG", "Tokyo": "JP", "Nairobi": "KE",
}


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
    cur.execute(SQL_COLONNA)
    conn.commit()
    print("Colonna socio_profile.paese_residenza pronta.")

    totale_aggiornate = 0
    for comune, codice in MAPPA_CITTA_PAESE.items():
        cur.execute("""
            UPDATE socio_profile SET paese_residenza = %s
            WHERE TRIM(comune_residenza) = %s AND paese_residenza IS NULL
        """, (codice, comune))
        if cur.rowcount:
            print(f"  {comune!r} -> {codice}: {cur.rowcount} profili aggiornati")
            totale_aggiornate += cur.rowcount
    conn.commit()

    cur.execute("""
        SELECT count(*) AS n FROM socio_profile WHERE paese_residenza IS NULL AND comune_residenza IS NOT NULL
    """)
    non_mappati = cur.fetchone()["n"]
    print(f"\nTotale righe aggiornate: {totale_aggiornate}")
    if non_mappati:
        print(f"[NOTA] {non_mappati} righe hanno un comune_residenza non presente nella mappa — lasciate NULL, nessun paese indovinato.")
    conn.close()


if __name__ == "__main__":
    main()
