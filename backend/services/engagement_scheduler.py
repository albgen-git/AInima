"""RF-32d: "motore" a monte della regola anti-invadenza (v. CLAUDE.md). Per
ciascuno dei 3 tipi di comunicazione (Pillola/Domanda approfondimento/
Ricalcolo profilo), scorre gli utenti Attivi per cui è trascorsa (o non è mai
scattata) la soglia minima di giorni configurata in system_config, ed esegue
l'azione corrispondente — la stessa identica infrastruttura per tutti e tre
(semantica comune: "soglia minima di attesa dall'ultimo invio/trigger", non
un calendario fisso, v. Documento_Requisiti_v1.md §7.8/§7.14/RF-32d).

Logica condivisa tra l'endpoint HTTP protetto (routers/internal_cron.py,
chiamato dalla GitHub Action schedulata) e lo script CLI
(scripts/cron_engagement_daily.py, per rilanci manuali) — stesso principio
già in uso per services/onboarding_export.py, mai due implementazioni
parallele della stessa logica.

RNF-12: la logica di assegnazione/tracciamento (engagement_log) gira
IDENTICA sui profili demo (is_demo=TRUE) — solo la CHIAMATA REALE al
provider email viene saltata, e solo dentro
services.engagement.invia_email_engagement_batch(), che questa funzione NON
chiama (assegna/mette in coda, non invia — l'invio resta un passo separato
con la propria cadenza settimanale già esistente, v. CLAUDE.md Blocco E).
Questa funzione quindi non ha bisogno di credenziali email, solo di accesso
al DB.

Query di selezione (per non scansionare l'intera tabella utenti ad ogni
run, v. CLAUDE.md): parte dall'indice parziale idx_users_attivi
(stato_account='Attivo') e usa una LATERAL join sull'indice composito
idx_engagement_log_user_tipo_data per recuperare, per ciascun utente, solo
l'ULTIMO trigger di quel tipo specifico — non l'intero storico.
"""

# Mappa tipo -> chiave system_config della soglia in giorni (§7.8).
SOGLIE = {
    "Pillola": "cadenza_giorni_pillola",
    "Domanda approfondimento": "cadenza_giorni_domanda_approfondimento",
    "Ricalcolo profilo": "cadenza_giorni_ricalcolo_profilo",
}

# Testo placeholder esplicito (v. CLAUDE.md — decisione presa: la libreria
# di domande vere non esiste ancora, ma la tabella/il meccanismo vanno
# comunque esercitati end-to-end; nessun codice legge/mostra ancora
# questo campo a un utente, quindi un placeholder marcato come tale è
# sicuro). Da sostituire quando il flusso completo (RF-32/32b) sarà
# definito insieme al contenuto reale delle domande.
DOMANDA_PLACEHOLDER = "[PLACEHOLDER — contenuto domanda di approfondimento non ancora definito, v. CLAUDE.md]"


def _config_int(cur, chiave: str, default: int) -> int:
    cur.execute("SELECT valore FROM system_config WHERE chiave = %s", (chiave,))
    r = cur.fetchone()
    return int(r["valore"]) if r else default


def _utenti_eleggibili(cur, tipo: str, soglia_giorni: int):
    """Utenti Attivi per cui non esiste alcun engagement_log di questo tipo,
    oppure l'ultimo risale ad almeno `soglia_giorni` fa. La LATERAL join
    recupera SOLO l'ultimo record per (user_id, tipo) sfruttando
    idx_engagement_log_user_tipo_data — non l'intero storico dell'utente."""
    cur.execute("""
        SELECT u.user_id, u.email, u.is_demo
        FROM users u
        LEFT JOIN LATERAL (
            SELECT data_invio_trigger FROM engagement_log el
            WHERE el.user_id = u.user_id AND el.tipo = %s
            ORDER BY el.data_invio_trigger DESC LIMIT 1
        ) ultimo ON true
        WHERE u.stato_account = 'Attivo'
          AND (ultimo.data_invio_trigger IS NULL
               OR ultimo.data_invio_trigger <= now() - (%s || ' days')::interval)
        ORDER BY u.user_id
    """, (tipo, soglia_giorni))
    return cur.fetchall()


def _log_trigger(cur, user_id, tipo: str, riferimento_contenuto=None):
    cur.execute("""
        INSERT INTO engagement_log (user_id, tipo, riferimento_contenuto)
        VALUES (%s, %s, %s)
    """, (str(user_id), tipo, str(riferimento_contenuto) if riferimento_contenuto else None))


def esegui(conn, dry_run=True):
    from services import engagement

    cur = conn.cursor()
    risultati = {"Pillola": [], "Domanda approfondimento": [], "Ricalcolo profilo": [], "Timeout match": []}

    # ── Timeout match (RF-14b/14c/14d) — porta a 'Scaduto' i match con
    #    data_scadenza_risposta superata e notifica entrambe le parti
    #    (v. services/match_timeout.py). Isolato in try/except: un
    #    fallimento qui non deve impedire al resto del cron di girare. In
    #    dry_run si salta (nessuna scrittura/email reale), stesso
    #    principio del resto dello script. ──
    if dry_run:
        cur.execute("""
            SELECT count(*) AS n FROM matches
            WHERE notifica_scadenza_inviata = FALSE
              AND ((stato IN ('Proposto','Accettato_A','Accettato_B') AND data_scadenza_risposta < now())
                   OR stato = 'Scaduto')
        """)
        risultati["Timeout match"] = [{"esito": "simulata"}] * cur.fetchone()["n"]
    else:
        try:
            from services import match_timeout

            risultati["Timeout match"] = match_timeout.scadi_match_e_notifica(conn)
        except Exception as e:
            conn.rollback()
            risultati["Timeout match"] = [{"esito": "errore", "dettaglio": str(e)}]

    # ── Generazione live "pillola del giorno" (Ainima_Prompt_Generazione_
    #    Live_Pillole_v3.md, v. CLAUDE.md) — UNA per esecuzione, PRIMA del
    #    ciclo per-utente sotto, così la riga appena pubblicata è già
    #    disponibile come "più recente" per chi risulta eleggibile in
    #    questo stesso run. Isolata in try/except (fail-open, come tutto
    #    il resto qui): un fallimento della generazione non deve impedire
    #    Domanda approfondimento/Ricalcolo profilo di girare comunque. In
    #    dry_run si salta del tutto (nessuna chiamata LLM/scrittura reale,
    #    stesso principio "calcola senza scrivere" del resto dello script).
    if dry_run:
        risultati["generazione_pillola"] = {"esito": "simulata"}
    else:
        try:
            from services import pillola_generator

            risultati["generazione_pillola"] = pillola_generator.genera_pillola_del_giorno(cur)
            conn.commit()
        except Exception as e:
            conn.rollback()
            risultati["generazione_pillola"] = {"pubblicata": False, "esito": "errore", "dettaglio": str(e)}

    # ── Pillola: assegna_pillola() già esistente (RF-31b), mette in coda
    #    email_coda_prossimo_invio — l'invio vero resta un passo separato. ──
    soglia = _config_int(cur, SOGLIE["Pillola"], 2)
    for u in _utenti_eleggibili(cur, "Pillola", soglia):
        try:
            if dry_run:
                risultati["Pillola"].append({"user_id": str(u["user_id"]), "esito": "simulata"})
                continue
            pillola = engagement.assegna_pillola(cur, u["user_id"])
            if pillola:
                _log_trigger(cur, u["user_id"], "Pillola", pillola["pillola_id"])
                conn.commit()
                risultati["Pillola"].append({"user_id": str(u["user_id"]), "esito": "assegnata", "pillola_id": str(pillola["pillola_id"])})
            else:
                # Nessuna pillola disponibile per questo contesto/utente
                # (es. esaurite quelle non ancora inviate) — non si scrive
                # engagement_log: l'utente resta eleggibile e viene
                # ritentato al prossimo run, invece di essere silenziato
                # per la soglia senza aver ricevuto nulla davvero.
                conn.rollback()
                risultati["Pillola"].append({"user_id": str(u["user_id"]), "esito": "nessuna_pillola_disponibile"})
        except Exception as e:
            conn.rollback()
            risultati["Pillola"].append({"user_id": str(u["user_id"]), "esito": "errore", "dettaglio": str(e)})

    # ── Domanda di approfondimento: il contenuto reale non è ancora
    #    definito (v. CLAUDE.md) — crea comunque il record in
    #    domande_approfondimento_risposte con un placeholder ESPLICITO,
    #    per esercitare l'infrastruttura di scheduling end-to-end senza
    #    bloccarsi sul contenuto, che nessun codice legge/mostra ancora. ──
    soglia = _config_int(cur, SOGLIE["Domanda approfondimento"], 7)
    for u in _utenti_eleggibili(cur, "Domanda approfondimento", soglia):
        try:
            if dry_run:
                risultati["Domanda approfondimento"].append({"user_id": str(u["user_id"]), "esito": "simulata"})
                continue
            cur.execute("""
                INSERT INTO domande_approfondimento_risposte (user_id, domanda_testo)
                VALUES (%s, %s) RETURNING risposta_id
            """, (str(u["user_id"]), DOMANDA_PLACEHOLDER))
            risposta_id = cur.fetchone()["risposta_id"]
            _log_trigger(cur, u["user_id"], "Domanda approfondimento", risposta_id)
            conn.commit()
            risultati["Domanda approfondimento"].append({"user_id": str(u["user_id"]), "esito": "creata", "risposta_id": str(risposta_id)})
        except Exception as e:
            conn.rollback()
            risultati["Domanda approfondimento"].append({"user_id": str(u["user_id"]), "esito": "errore", "dettaglio": str(e)})

    # ── Ricalcolo profilo: SOLO log del trigger, nessun ricalcolo reale
    #    (il "cosa" non è ancora definito, v. RF-32c) — non deve mai
    #    fallire per definizione, dato che non fa nulla oltre a scrivere
    #    una riga. ──
    soglia = _config_int(cur, SOGLIE["Ricalcolo profilo"], 60)
    for u in _utenti_eleggibili(cur, "Ricalcolo profilo", soglia):
        try:
            if dry_run:
                risultati["Ricalcolo profilo"].append({"user_id": str(u["user_id"]), "esito": "simulata"})
                continue
            _log_trigger(cur, u["user_id"], "Ricalcolo profilo")
            conn.commit()
            risultati["Ricalcolo profilo"].append({"user_id": str(u["user_id"]), "esito": "loggato"})
        except Exception as e:
            conn.rollback()
            risultati["Ricalcolo profilo"].append({"user_id": str(u["user_id"]), "esito": "errore", "dettaglio": str(e)})

    return risultati
