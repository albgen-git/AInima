"""RF-25/25b/25c/25d: pannello di back-office — API JSON (il viewer HTML per
la correzione manuale a campo singolo vive in routers/admin_viewer.py).
Solo API per ora, nessuna pagina staff dedicata (decisione esplicita
dell'utente, v. CLAUDE.md 2026-08-19) — stesso livello del resto del
pannello admin attuale."""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException

from db import get_conn
from schemas.account import ModerationDecisionIn, RecoveryDecisionIn
from schemas.admin import AccountStatusUpdate, SystemConfigUpdate
from services import engagement
from services.email_provider import get_email_provider

router = APIRouter(prefix="/admin", tags=["admin"])

STATI_VALIDI = {"In attesa", "In attesa - verifica moderazione", "Attivo", "Sospeso", "Chiuso"}


@router.get("/users")
def cerca_utenti(q: str = "", offset: int = 0, limit: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, nome, cognome, email, stato_account, data_creazione
        FROM users
        WHERE %s = '' OR nome ILIKE %s OR cognome ILIKE %s OR email ILIKE %s
        ORDER BY data_creazione DESC LIMIT %s OFFSET %s
    """, (q, f"%{q}%", f"%{q}%", f"%{q}%", limit, offset))
    righe = cur.fetchall()
    conn.close()
    return righe


@router.patch("/users/{user_id}/status")
def aggiorna_stato_account(user_id: UUID, payload: AccountStatusUpdate):
    """Sospensione/riattivazione manuale (RF-25)."""
    if payload.stato_account not in STATI_VALIDI:
        raise HTTPException(400, f"Stato non valido, atteso uno tra {STATI_VALIDI}")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET stato_account = %s WHERE user_id = %s RETURNING user_id",
                (payload.stato_account, str(user_id)))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "Utente non trovato")
    conn.commit()
    conn.close()
    return {"aggiornato": True}


@router.get("/matches")
def monitora_match(stato: str | None = None, offset: int = 0, limit: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    if stato:
        cur.execute("""
            SELECT match_id, user_a_id, user_b_id, stato, final_score, data_proposta
            FROM matches WHERE stato = %s ORDER BY data_proposta DESC LIMIT %s OFFSET %s
        """, (stato, limit, offset))
    else:
        cur.execute("""
            SELECT match_id, user_a_id, user_b_id, stato, final_score, data_proposta
            FROM matches ORDER BY data_proposta DESC LIMIT %s OFFSET %s
        """, (limit, offset))
    righe = cur.fetchall()
    conn.close()
    return righe


@router.get("/matches/{match_id}/why")
def perche_questo_match(match_id: UUID):
    """Ricostruisce in forma leggibile perché un abbinamento è stato fatto:
    punteggio, versione dell'algoritmo con la sua descrizione a testo
    libero, e la fotografia esatta dei pesi/soglie usati in quel momento
    (possono differire da quelli attuali in system_config se nel frattempo
    sono stati ritoccati) — pensato per poter rispondere alla domanda anche
    a distanza di anni, quando la logica sarà cambiata più volte."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.match_id, m.user_a_id, m.user_b_id, m.stato, m.final_score,
               m.data_proposta, m.algoritmo_versione, m.algoritmo_parametri,
               m.selezionato_per_somiglianza_visiva, m.shortlist_candidati,
               m.flag_rifiuto_esplicito, m.flag_asimmetria_narrativa,
               v.descrizione AS algoritmo_descrizione, v.data_introduzione AS algoritmo_data_introduzione
        FROM matches m
        LEFT JOIN matching_algorithm_versions v ON v.versione = m.algoritmo_versione
        WHERE m.match_id = %s
    """, (str(match_id),))
    riga = cur.fetchone()
    conn.close()
    if not riga:
        raise HTTPException(404, "Match non trovato")

    nota = None
    if riga["algoritmo_versione"] is None:
        nota = ("Questo match non ha una versione registrata — creato prima dell'introduzione "
                "del versioning (v. CLAUDE.md), oppure inserito manualmente.")

    return {**riga, "nota": nota}


@router.get("/config")
def leggi_config():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT chiave, valore, descrizione, data_ultima_modifica FROM system_config ORDER BY chiave")
    righe = cur.fetchall()
    conn.close()
    return righe


@router.patch("/config/{chiave}")
def aggiorna_config(chiave: str, payload: SystemConfigUpdate):
    """RF-25b: qualsiasi peso/soglia/dimensione pool va esposto qui, mai
    hardcoded nel codice (requisito ripetuto in più documenti)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE system_config SET valore = %s, data_ultima_modifica = now()
        WHERE chiave = %s RETURNING chiave
    """, (payload.valore, chiave))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, f"Parametro '{chiave}' non esistente in system_config")
    conn.commit()
    conn.close()
    return {"aggiornato": True}


@router.post("/engagement/invia-email-batch")
def invia_email_engagement_batch(dry_run: bool = True):
    """Blocco E (v. CLAUDE.md — Ainima_Dashboard_Trigger_Email_v1.md §2.2):
    svuota email_coda_prossimo_invio raggruppando per utente, rispettando
    il tetto di frequenza. dry_run=True (default) calcola senza inviare —
    passare dry_run=false per inviare davvero. Da schedulare nel giorno
    fisso configurato (system_config.giorno_invio_email_engagement) —
    nessuno scheduler reale in questo scheletro (v. run-cycle)."""
    conn = get_conn()
    risultati = engagement.invia_email_engagement_batch(conn, dry_run=dry_run)
    conn.close()
    return {"dry_run": dry_run, "risultati": risultati}


@router.get("/metrics")
def metriche():
    """RF-25: iscrizioni, tasso di conversione match, rapporto di genere nel pool."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT count(*) AS n FROM users")
    totale = cur.fetchone()["n"]
    cur.execute("SELECT count(*) AS n FROM users WHERE stato_account = 'Attivo'")
    attivi = cur.fetchone()["n"]
    cur.execute("SELECT count(*) AS n FROM matches")
    proposti = cur.fetchone()["n"]
    cur.execute("SELECT count(*) AS n FROM matches WHERE stato = 'Confermato'")
    confermati = cur.fetchone()["n"]
    cur.execute("SELECT genere, count(*) AS n FROM users GROUP BY genere")
    rapporto_genere = {r["genere"]: r["n"] for r in cur.fetchall()}
    conn.close()

    return {
        "totale_iscritti": totale,
        "utenti_attivi": attivi,
        "match_proposti": proposti,
        "match_confermati": confermati,
        "tasso_conversione_pct": round(confermati / proposti * 100, 1) if proposti else 0.0,
        "rapporto_genere": rapporto_genere,
    }


@router.get("/moderation/queue")
def coda_moderazione():
    """RF-25c: immagini segnalate dal sistema automatico, in attesa di
    revisione umana."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.moderation_id, m.user_id, u.nome, u.cognome, u.email,
               m.tipo_immagine, m.immagine_url, m.esito_automatico, m.score_confidenza, m.data_scansione
        FROM content_moderation_log m
        JOIN users u ON u.user_id = m.user_id
        WHERE m.esito_automatico = 'Sospetta' AND m.esito_revisione_umana = 'In attesa'
        ORDER BY m.data_scansione ASC
    """)
    righe = cur.fetchall()
    conn.close()
    return righe


@router.post("/moderation/{moderation_id}/decision")
def decidi_moderazione(moderation_id: UUID, payload: ModerationDecisionIn):
    """RF-25c: approvare fa proseguire l'onboarding (torna 'In attesa',
    l'attivazione vera avviene poi al prossimo GET /auth/{id}/status se
    tutto il resto è completo); rifiutare lascia l'account bloccato finché
    l'utente non ricarica una nuova immagine conforme."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM content_moderation_log WHERE moderation_id = %s", (str(moderation_id),))
    riga = cur.fetchone()
    if not riga:
        conn.close()
        raise HTTPException(404, "Voce di moderazione non trovata")

    esito = "Approvato" if payload.approvato else "Rifiutato"
    cur.execute("""
        UPDATE content_moderation_log SET esito_revisione_umana = %s, revisionato_da = %s, data_revisione = now()
        WHERE moderation_id = %s
    """, (esito, str(payload.revisionato_da) if payload.revisionato_da else None, str(moderation_id)))

    if payload.approvato:
        cur.execute("""
            UPDATE users SET stato_account = 'In attesa'
            WHERE user_id = %s AND stato_account = 'In attesa - verifica moderazione'
        """, (str(riga["user_id"]),))

    conn.commit()
    conn.close()
    return {"aggiornato": True, "esito": esito}


@router.get("/recovery/queue")
def coda_recupero_accesso():
    """RF-25d: richieste di cambio email/recupero accesso in attesa di
    revisione, con i dati identificativi dichiarati affiancati al profilo
    che meglio corrisponde per email dichiarata (solo un aiuto al confronto
    — la decisione resta sempre manuale). Applica anche, di passaggio, i
    cambi email il cui periodo di grazia (RF-26d) è scaduto senza
    annullamento — nessun cron reale in questo scheletro, v. CLAUDE.md
    sullo stesso limite per il ciclo di matching mensile."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT request_id, user_id, email_nuova_richiesta FROM email_change_requests
        WHERE stato = 'In periodo di grazia' AND data_scadenza_grazia < now()
    """)
    scaduti = cur.fetchall()
    for r in scaduti:
        cur.execute("UPDATE users SET email = %s WHERE user_id = %s",
                    (r["email_nuova_richiesta"], str(r["user_id"])))
        cur.execute("UPDATE email_change_requests SET stato = 'Completata' WHERE request_id = %s",
                    (str(r["request_id"]),))
    if scaduti:
        conn.commit()

    cur.execute("""
        SELECT req.request_id, req.user_id, req.email_attuale_dichiarata, req.email_nuova_richiesta,
               req.dati_identificativi_forniti, req.origine, req.data_richiesta,
               u.nome AS profilo_nome, u.cognome AS profilo_cognome, u.email AS profilo_email,
               u.data_nascita AS profilo_data_nascita
        FROM email_change_requests req
        LEFT JOIN users u ON u.email = req.email_attuale_dichiarata
        WHERE req.stato = 'In attesa revisione'
        ORDER BY req.data_richiesta ASC
    """)
    righe = cur.fetchall()
    conn.close()
    return righe


@router.post("/recovery/{request_id}/decision")
def decidi_recupero_accesso(request_id: UUID, payload: RecoveryDecisionIn):
    """RF-25d/26c/26d: approvare apre il periodo di grazia (default 48h,
    system_config.recupero_accesso_grazia_ore) — email di annullamento alla
    vecchia casella, il cambio si applica da solo a scadenza (v. sweep in
    GET /recovery/queue) se nessuno annulla. Rifiutare non spiega il motivo
    (RF-26c, per non aiutare un tentativo di furto d'identità)."""
    if payload.approvato and payload.user_id is None:
        raise HTTPException(422, "user_id è richiesto per approvare — quale account è")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT stato, email_nuova_richiesta FROM email_change_requests WHERE request_id = %s",
                (str(request_id),))
    r = cur.fetchone()
    if not r:
        conn.close()
        raise HTTPException(404, "Richiesta non trovata")
    if r["stato"] != "In attesa revisione":
        conn.close()
        raise HTTPException(409, f"Richiesta già decisa (stato attuale: {r['stato']})")

    if not payload.approvato:
        cur.execute("""
            UPDATE email_change_requests SET stato = 'Rifiutata', revisionato_da = %s, data_decisione = now()
            WHERE request_id = %s
        """, (str(payload.revisionato_da) if payload.revisionato_da else None, str(request_id)))
        conn.commit()
        conn.close()
        return {"stato": "Rifiutata"}

    cur.execute("SELECT email FROM users WHERE user_id = %s", (str(payload.user_id),))
    utente = cur.fetchone()
    if not utente:
        conn.close()
        raise HTTPException(404, "user_id indicato non corrisponde a nessun utente")

    grazia_ore = _config_int_recovery(cur, "recupero_accesso_grazia_ore", 48)
    token = secrets.token_urlsafe(32)
    scadenza = datetime.now(timezone.utc) + timedelta(hours=grazia_ore)
    cur.execute("""
        UPDATE email_change_requests SET
            stato = 'In periodo di grazia', user_id = %s, revisionato_da = %s, data_decisione = now(),
            data_scadenza_grazia = %s, token_annullamento = %s
        WHERE request_id = %s
    """, (str(payload.user_id), str(payload.revisionato_da) if payload.revisionato_da else None,
          scadenza, token, str(request_id)))
    conn.commit()
    conn.close()

    email_vecchia = utente["email"]
    try:
        get_email_provider().invia_notifica(
            email_vecchia, "Richiesta di cambio email sul tuo account Ainima",
            f"<p>È stata approvata una richiesta di cambio email per il tuo account.</p>"
            f"<p>Se sei stato tu, non devi fare nulla: il cambio si completerà tra {grazia_ore} ore.</p>"
            f"<p>Se NON sei stato tu, annulla subito con questo link: "
            f"/account-recovery/cancel?request_id={request_id}&token={token}</p>",
        )
    except Exception as e:
        print(f"[ERRORE] invio notifica recupero accesso a {email_vecchia} fallito: {e}")

    return {"stato": "In periodo di grazia", "data_scadenza_grazia": scadenza}


def _config_int_recovery(cur, chiave: str, default: int) -> int:
    cur.execute("SELECT valore FROM system_config WHERE chiave = %s", (chiave,))
    r = cur.fetchone()
    return int(r["valore"]) if r else default
