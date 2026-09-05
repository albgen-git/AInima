"""Migrazione live: "Pillola del giorno" + generazione live
(Ainima_Dashboard_Trigger_Email_v1.md §2.1bis,
Ainima_Prompt_Generazione_Live_Pillole_v3.md — v. CLAUDE.md). La selezione
della pillola non usa più tag_personalizzazione (inerte, le pillole sono
general purpose) — sceglie sempre la riga più recente in pillole_libreria
per data_creazione.

Fasi:
1. ALTER TABLE pillole_libreria ADD COLUMN data_creazione (idempotente).
   Un ALTER con DEFAULT now() valorizza TUTTE le righe preesistenti con lo
   STESSO istante (now() è stable per statement in Postgres) — per le 3
   pillole illustrative già in libreria (v. migrate_2026_08_24) questo
   produrrebbe un pareggio esatto, quindi "la più recente" sarebbe
   indeterminata al primo giro. Scaglionato qui sotto in modo deterministico
   (ordine fisico ctid, 10 minuti di distanza l'una dall'altra) SOLO per
   queste righe legacy — non rilevante per il futuro, dove la pipeline di
   generazione live scriverà data_creazione reali una riga alla volta.
2. Backfill eseguito solo se ci sono righe con data_creazione duplicata
   (idempotente: un secondo giro non trova più duplicati e non fa nulla).
3. ALTER TABLE pillole_libreria ADD COLUMN tecnica_usata (idempotente,
   NULL per le righe legacy — non hanno mai avuto questo dato).
4. CREATE TABLE pillole_generazione_log (idempotente) — log minimo per il
   monitoraggio dei tentativi di generazione (v. services/pillola_generator.py).
5. ALTER TABLE pillole_libreria ADD COLUMN tema_centrale (idempotente) —
   trovate ripetizioni reali di tema/immagine centrale (es. "silenzio" in
   3 pillole su 7 generate) che i controlli su pilastro/tecnica da soli
   non intercettavano, v. CLAUDE.md.

Uso:
    python scripts/migrate_2026_09_05_pillola_del_giorno.py            (DB locale)
    python scripts/migrate_2026_09_05_pillola_del_giorno.py --render   (DB Render)
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
    cur.execute("ALTER TABLE pillole_libreria ADD COLUMN IF NOT EXISTS data_creazione TIMESTAMPTZ NOT NULL DEFAULT now()")
    cur.execute("ALTER TABLE pillole_libreria ADD COLUMN IF NOT EXISTS tecnica_usata VARCHAR(50)")
    cur.execute("ALTER TABLE pillole_libreria ADD COLUMN IF NOT EXISTS tema_centrale VARCHAR(50)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pillole_generazione_log (
            log_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pillola_id         UUID REFERENCES pillole_libreria(pillola_id),
            tentativi            INT NOT NULL,
            esito                  VARCHAR(30) NOT NULL,
            dettaglio_scarti        JSONB,
            data_esecuzione            TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    conn.commit()

    # Backfill deterministico SOLO se esistono duplicati esatti (righe
    # legacy dallo stesso ALTER) — un rilancio successivo non trova più
    # nulla da scaglionare.
    cur.execute("""
        SELECT count(*) AS n FROM (
            SELECT data_creazione FROM pillole_libreria
            GROUP BY data_creazione HAVING count(*) > 1
        ) dup
    """)
    if cur.fetchone()["n"] > 0:
        cur.execute("SELECT pillola_id FROM pillole_libreria ORDER BY ctid")
        righe = cur.fetchall()
        for i, r in enumerate(righe):
            minuti_fa = (len(righe) - 1 - i) * 10
            cur.execute(
                "UPDATE pillole_libreria SET data_creazione = now() - (%s || ' minutes')::interval WHERE pillola_id = %s",
                (str(minuti_fa), r["pillola_id"]),
            )
        conn.commit()
        print(f"Backfill scaglionato applicato a {len(righe)} righe legacy (10 minuti di distanza l'una dall'altra).")
    else:
        print("Nessun pareggio su data_creazione — backfill non necessario.")

    cur.execute("SELECT titolo, data_creazione FROM pillole_libreria ORDER BY data_creazione DESC, pillola_id DESC")
    print("Ordine attuale (la prima è la 'pillola del giorno' oggi):")
    for r in cur.fetchall():
        print(" ", dict(r))

    conn.close()


if __name__ == "__main__":
    main()
