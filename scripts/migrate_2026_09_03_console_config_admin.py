"""Migrazione live: RF-25e (console di configurazione) + tabella di audit
generica per le azioni prese dal nuovo viewer admin autenticato (v. CLAUDE.md).

Aggiunge a system_config le 4 chiavi richieste da RF-25e/§7.8 non ancora
presenti (cadenza_giorni_proposta_abbinamento, cadenza_invio_pillole,
cadenza_domande_supplementari, verifica_carta_attiva) e la tabella
admin_action_log — non lega "chi" a system_config.modificato_da/
content_moderation_log.revisionato_da/email_change_requests.revisionato_da
(tutti UUID, pensati per una futura tabella staff che non esiste ancora,
sempre rimasti NULL in pratica) — usa invece lo username HTTP Basic Auth
(stringa reale, non un placeholder) come "chi", in una tabella dedicata
condivisa dalle 3 nuove sezioni (moderazione/recupero/config).

Idempotente (ON CONFLICT/IF NOT EXISTS, sicuro da rilanciare).

NOTA AMBIENTE: i valori di default inseriti in system_config qui sotto
sono pensati per l'ambiente di COLLAUDO attuale (l'unico che esiste oggi).
Un futuro DB di PRODUZIONE è un database separato — questa stessa
migrazione andrà rilanciata anche lì, ma i valori (specialmente
verifica_carta_attiva) vanno rivisti per quel contesto, mai assunti
identici a collaudo solo perché la migrazione è la stessa.

Uso:
    python scripts/migrate_2026_09_03_console_config_admin.py            (DB locale)
    python scripts/migrate_2026_09_03_console_config_admin.py --render   (DB Render, oggi l'unico ambiente di collaudo)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

SQL = """
CREATE TABLE IF NOT EXISTS admin_action_log (
    log_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operatore     TEXT NOT NULL,
    azione         TEXT NOT NULL,
    dettaglio       TEXT,
    data_azione      TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO system_config (chiave, valore, descrizione) VALUES
    ('cadenza_giorni_proposta_abbinamento', '30', 'RF-25e/RF-11: ogni quanti giorni gira il ciclo di generazione delle proposte di abbinamento'),
    ('cadenza_invio_pillole', '7', 'RF-25e/RF-31c: ogni quanti giorni viene proposta una nuova pillola di contenuto, per non mostrare sempre la stessa'),
    ('cadenza_domande_supplementari', '14', 'RF-25e: ogni quanti giorni vengono proposte nuove domande di affinamento supplementari'),
    ('verifica_carta_attiva', 'true', 'RF-25e/RF-04: se disattivato, l''onboarding prosegue senza richiedere la pre-autorizzazione carta — rimuove un filtro anti-abuso, richiede conferma esplicita per disattivare')
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
    print("admin_action_log creata + 4 chiavi system_config inserite (o già presenti).")
    conn.close()


if __name__ == "__main__":
    main()
