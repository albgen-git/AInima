"""Migrazione live: prerequisiti + infrastruttura per il cron di engagement
giornaliero (RF-32d — v. CLAUDE.md e Documento_Requisiti_v1.md §4.11/§7.8/
§7.14/§7.15/RNF-12).

PREREQUISITO BLOCCANTE (richiesto esplicitamente dall'utente prima di
costruire il cron): i 1000 profili demo hanno stato_account='Attivo' sul
DB di collaudo — un cron che scorra ciecamente tutti gli "Attivi" rischia
un invio email di massa verso indirizzi fittizi. Questa migrazione aggiunge
`users.is_demo` e lo popola per i profili demo esistenti PRIMA che il cron
esista.

Fasi:
1. ALTER TABLE users ADD COLUMN is_demo (idempotente).
2. Backfill is_demo = TRUE per source_actor_id IS NOT NULL (criterio già
   usato ovunque nel progetto per identificare il pool demo — affidabile,
   verificato: nessun utente reale ha mai source_actor_id valorizzato).
3. CREATE TABLE engagement_log, domande_approfondimento_risposte (idempotente,
   già in schema.sql — qui solo per i DB già esistenti).
4. Corregge le chiavi system_config sbagliate di una sessione precedente
   (cadenza_invio_pillole/cadenza_domande_supplementari, nome E default
   sbagliati, mai lette da alcun codice) con quelle corrette da §7.8.

Idempotente, sicuro da rilanciare.

Uso:
    python scripts/migrate_2026_09_04_engagement_scheduler.py            (DB locale)
    python scripts/migrate_2026_09_04_engagement_scheduler.py --render   (DB Render)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

SQL = """
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE users SET is_demo = TRUE WHERE source_actor_id IS NOT NULL AND is_demo = FALSE;

CREATE TABLE IF NOT EXISTS engagement_log (
    log_id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                  UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    tipo                       VARCHAR(30) NOT NULL,
    data_invio_trigger           TIMESTAMPTZ NOT NULL DEFAULT now(),
    riferimento_contenuto          UUID
);
CREATE INDEX IF NOT EXISTS idx_engagement_log_user_tipo_data
    ON engagement_log (user_id, tipo, data_invio_trigger DESC);
CREATE INDEX IF NOT EXISTS idx_users_attivi ON users (user_id) WHERE stato_account = 'Attivo';

CREATE TABLE IF NOT EXISTS domande_approfondimento_risposte (
    risposta_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    domanda_testo             TEXT,
    risposta                    TEXT,
    data_risposta                 TIMESTAMPTZ
);

DELETE FROM system_config WHERE chiave IN ('cadenza_invio_pillole', 'cadenza_domande_supplementari');

INSERT INTO system_config (chiave, valore, descrizione) VALUES
    ('cadenza_giorni_pillola', '2', 'RF-25e/RF-31c: soglia minima di giorni dall''ultimo invio/trigger di una pillola per l''utente, prima che il cron di engagement gliene assegni una nuova'),
    ('cadenza_giorni_domanda_approfondimento', '7', 'RF-25e/RF-32: soglia minima di giorni dall''ultimo invio/trigger di una domanda di approfondimento per l''utente'),
    ('cadenza_giorni_ricalcolo_profilo', '60', 'RF-25e/RF-32c: soglia minima di giorni dall''ultimo ricalcolo del profilo personale per l''utente')
ON CONFLICT (chiave) DO NOTHING;
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

    cur.execute("SELECT count(*) AS n FROM users WHERE is_demo = TRUE")
    n_demo = cur.fetchone()["n"]
    cur.execute("SELECT count(*) AS n FROM users WHERE is_demo = FALSE")
    n_reali = cur.fetchone()["n"]
    print(f"is_demo backfillato: {n_demo} profili demo, {n_reali} profili non-demo (reali).")
    print("engagement_log / domande_approfondimento_risposte create (o già presenti).")
    print("Chiavi system_config corrette: cadenza_giorni_pillola/domanda_approfondimento/ricalcolo_profilo.")
    conn.close()


if __name__ == "__main__":
    main()
