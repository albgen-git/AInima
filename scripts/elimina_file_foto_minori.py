"""Cancella FISICAMENTE i file .jpg delle foto già escluse dal DB perché
ritraevano minori (v. CLAUDE.md 2026-08-20) — finora solo il riferimento
DB era stato azzerato, i file restavano su storage/photos/ (motivo per cui
un errore successivo li ha riletti direttamente dal disco per uno dei test
di matching, mostrando una foto che il sistema aveva già escluso). Decisione
esplicita dell'utente: meglio non lasciarli in giro.

Ambito: tutti gli utenti con source_actor_id valorizzato la cui
foto_profilo_url/foto_partner_ideale_url è NULL nel DB — per questo dataset
di test, NULL su questi campi significa sempre "rimossa perché ritraeva un
minore" (tutti i 1000 profili importati avevano originariamente entrambe le
foto assegnate dalla pipeline di import).

Uso: python scripts/elimina_file_foto_minori.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402

STORAGE_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "photos")


def elimina(sottocartella, condizione_colonna):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT u.user_id FROM users u JOIN physical_profile p ON p.user_id = u.user_id
        WHERE u.source_actor_id IS NOT NULL AND p.{condizione_colonna} IS NULL
    """)
    ids = [str(r["user_id"]) for r in cur.fetchall()]
    conn.close()

    cancellati, mancanti = 0, 0
    for uid in ids:
        path = os.path.join(STORAGE_BASE, sottocartella, f"{uid}.jpg")
        if os.path.exists(path):
            os.remove(path)
            cancellati += 1
        else:
            mancanti += 1
    return len(ids), cancellati, mancanti


def main():
    tot, canc, manc = elimina("profilo", "foto_profilo_url")
    print(f"profilo: {tot} record NULL, {canc} file cancellati, {manc} già assenti")

    tot, canc, manc = elimina("partner_ideale", "foto_partner_ideale_url")
    print(f"partner_ideale: {tot} record NULL, {canc} file cancellati, {manc} già assenti")


if __name__ == "__main__":
    main()
