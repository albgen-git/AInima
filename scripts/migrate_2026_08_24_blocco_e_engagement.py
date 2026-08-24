"""Migrazione live: Blocco E (v. CLAUDE.md — Ainima_Dashboard_Trigger_Email_v1.md,
Ainima_Engagement_Periodico_v1_BOZZA.md §2-3). Crea le 6 nuove tabelle
(domande_affinamento_pool/_log, pillole_libreria/_inviate_log,
email_coda_prossimo_invio, email_inviata_log) + 2 parametri admin_config,
poi popola domande_affinamento_pool con i 20 item reali verificati
(scripts/domande_affinamento_pool_data.py) e pillole_libreria con 3
pillole illustrative reali (non placeholder, per testare il meccanismo
end-to-end — il calendario editoriale completo resta un lavoro
successivo, v. CLAUDE.md).

Uso: python scripts/migrate_2026_08_24_blocco_e_engagement.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402
from domande_affinamento_pool_data import DOMANDE_AFFINAMENTO_POOL  # noqa: E402

PILLOLE_ILLUSTRATIVE = [
    {
        "titolo": "L'attesa non è tempo perso",
        "testo": (
            "Aspettare una proposta di abbinamento può generare un'ansia sottile: quella "
            "sensazione di essere in stand-by, come se la propria vita relazionale dipendesse "
            "da un segnale esterno. Un modo diverso di viverla: l'attesa è anche il tempo in "
            "cui i tuoi criteri, le tue priorità, la tua conoscenza di te stesso continuano a "
            "maturare — non è un vuoto tra due eventi, è parte del percorso. Un piccolo "
            "esercizio: la prossima volta che controlli se è arrivata una proposta, prova a "
            "chiederti anche \"cosa ho imparato di me questa settimana?\" — spesso la risposta "
            "è più interessante della notifica che stavi aspettando."
        ),
        "pilastro_editoriale": "Intelligenza Emotiva",
        "contesto_trigger": "Attesa generale",
        "tag_personalizzazione": ["ansia_alta"],
    },
    {
        "titolo": "Ascoltare per capire, non per rispondere",
        "testo": (
            "Nelle prime conversazioni con una persona nuova, la tentazione più comune è "
            "preparare la propria risposta mentre l'altro sta ancora parlando. È naturale — "
            "ma toglie qualcosa di importante: la possibilità di essere sorpresi da chi si ha "
            "davanti. Un piccolo cambio di abitudine che fa una grande differenza: quando "
            "l'altra persona finisce di parlare, prova a fare una pausa di due secondi prima "
            "di rispondere. Non serve a sembrare più riflessivo — serve davvero a esserlo, e a "
            "far sentire all'altro che le sue parole sono state ascoltate, non solo elaborate."
        ),
        "pilastro_editoriale": "Comunicazione & Conflitto",
        "contesto_trigger": "Attesa generale",
        "tag_personalizzazione": [],
    },
    {
        "titolo": "Prima di incontrarvi di persona",
        "testo": (
            "Il passaggio dal profilo al primo incontro reale è delicato: qualche aspettativa "
            "si conferma, qualche altra si ridimensiona, ed è del tutto normale. Un consiglio "
            "pratico: scegliete un contesto che permetta di parlare con calma (evitate un "
            "ambiente troppo rumoroso o un'attività che non lasci spazio alla conversazione) e "
            "concedetevi il permesso di non dover \"decidere\" tutto al primo caffè. Una "
            "relazione seria non si giudica in un'ora — l'obiettivo del primo incontro è solo "
            "capire se vale la pena di un secondo."
        ),
        "pilastro_editoriale": "Preparazione al Matrimonio",
        "contesto_trigger": "Post-match confermato",
        "tag_personalizzazione": [],
    },
]


def main():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS domande_affinamento_pool (
            item_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            codice_originale     VARCHAR(10) NOT NULL,
            test_origine          VARCHAR(20) NOT NULL,
            dimensione             VARCHAR(30) NOT NULL,
            reverse                  BOOLEAN NOT NULL,
            testo_it                  TEXT NOT NULL,
            testo_en                   TEXT NOT NULL,
            attivo                       BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS domande_affinamento_log (
            user_id           UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            item_id            UUID NOT NULL REFERENCES domande_affinamento_pool(item_id),
            data_posta          TIMESTAMPTZ NOT NULL DEFAULT now(),
            risposta              SMALLINT,
            data_risposta          TIMESTAMPTZ,
            PRIMARY KEY (user_id, item_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pillole_libreria (
            pillola_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            titolo               VARCHAR(150) NOT NULL,
            testo                 TEXT NOT NULL,
            pilastro_editoriale    VARCHAR(40) NOT NULL,
            contesto_trigger         VARCHAR(30) NOT NULL DEFAULT 'Attesa generale',
            tag_personalizzazione     VARCHAR(30)[] NOT NULL DEFAULT '{}',
            attiva                       BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pillole_inviate_log (
            user_id       UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            pillola_id     UUID NOT NULL REFERENCES pillole_libreria(pillola_id),
            data_invio       TIMESTAMPTZ NOT NULL DEFAULT now(),
            aperta             BOOLEAN NOT NULL DEFAULT FALSE,
            PRIMARY KEY (user_id, pillola_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_coda_prossimo_invio (
            coda_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id           UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            tipo_contenuto     VARCHAR(20) NOT NULL,
            contenuto_id         UUID NOT NULL,
            aggiunto_il            TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_inviata_log (
            invio_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            data_invio            TIMESTAMPTZ NOT NULL DEFAULT now(),
            contenuti_inclusi       JSONB NOT NULL,
            aperta                    BOOLEAN NOT NULL DEFAULT FALSE,
            cliccata                   BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    print("6 tabelle create/verificate.")

    cur.execute("""
        INSERT INTO system_config (chiave, valore, descrizione) VALUES
            ('cadenza_email_engagement_giorni', '7', 'Blocco E — tetto minimo di giorni tra due email di engagement per lo stesso utente, anti-invadenza (Ainima_Dashboard_Trigger_Email_v1.md §2.3)'),
            ('giorno_invio_email_engagement', 'Martedì', 'Blocco E — giorno fisso della settimana in cui si svuota la coda email di engagement (Ainima_Dashboard_Trigger_Email_v1.md §2.2)')
        ON CONFLICT (chiave) DO NOTHING
    """)
    print("2 parametri admin_config aggiunti/verificati.")

    cur.execute("SELECT count(*) AS n FROM domande_affinamento_pool")
    if cur.fetchone()["n"] == 0:
        for item in DOMANDE_AFFINAMENTO_POOL:
            cur.execute("""
                INSERT INTO domande_affinamento_pool
                    (codice_originale, test_origine, dimensione, reverse, testo_it, testo_en)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (item["codice_originale"], item["test_origine"], item["dimensione"],
                  item["reverse"], item["testo_it"], item["testo_en"]))
        print(f"{len(DOMANDE_AFFINAMENTO_POOL)} item inseriti in domande_affinamento_pool.")
    else:
        print("domande_affinamento_pool già popolata, nessun inserimento (idempotente).")

    cur.execute("SELECT count(*) AS n FROM pillole_libreria")
    if cur.fetchone()["n"] == 0:
        for p in PILLOLE_ILLUSTRATIVE:
            cur.execute("""
                INSERT INTO pillole_libreria (titolo, testo, pilastro_editoriale, contesto_trigger, tag_personalizzazione)
                VALUES (%s, %s, %s, %s, %s)
            """, (p["titolo"], p["testo"], p["pilastro_editoriale"], p["contesto_trigger"], p["tag_personalizzazione"]))
        print(f"{len(PILLOLE_ILLUSTRATIVE)} pillole illustrative inserite in pillole_libreria.")
    else:
        print("pillole_libreria già popolata, nessun inserimento (idempotente).")

    conn.commit()
    conn.close()
    print("Migrazione completata.")


if __name__ == "__main__":
    main()
