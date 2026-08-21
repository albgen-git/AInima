"""RF-26/26b/26c/26d: gestione dell'account e recupero accesso.

Cambio email self-service (RF-26) riusa lo stesso meccanismo OTP di
RF-02 (otp_codes è già chiave-per-email, non per user_id — richiedere un
OTP per la nuova email è meccanicamente identico a request-otp, solo senza
creare un nuovo utente). Il recupero accesso pubblico (RF-26b/26c/26d) è
invece un flusso a revisione umana (v. routers/admin.py per la coda)."""

import json
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException

from db import get_conn
from schemas.account import EmailChangeConfirmIn, EmailChangeRequestIn, RecoveryRequestIn
from security import hash_otp, verify_otp_hash
from services.email_provider import get_email_provider

router = APIRouter(tags=["account"])


def _config_int(cur, chiave: str, default: int) -> int:
    cur.execute("SELECT valore FROM system_config WHERE chiave = %s", (chiave,))
    r = cur.fetchone()
    return int(r["valore"]) if r else default


@router.post("/users/{user_id}/email-change/request")
def richiedi_cambio_email(user_id: UUID, payload: EmailChangeRequestIn):
    """RF-26: invia un OTP alla NUOVA email (stesso meccanismo di
    request-otp) — l'email del profilo non cambia finché l'OTP non è
    verificato in /email-change/confirm."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE user_id = %s", (str(user_id),))
    utente = cur.fetchone()
    if not utente:
        conn.close()
        raise HTTPException(404, "Utente non trovato")

    cur.execute("SELECT 1 FROM users WHERE email = %s", (payload.email_nuova,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(409, "Questa email è già associata a un altro account")

    codice = f"{secrets.randbelow(1_000_000):06d}"
    scadenza_minuti = _config_int(cur, "otp_scadenza_minuti", 10)
    cur.execute("""
        INSERT INTO otp_codes (email, codice_hash, scade_il, tentativi, creato_il)
        VALUES (%s, %s, now() + (%s || ' minutes')::interval, 0, now())
        ON CONFLICT (email) DO UPDATE SET
            codice_hash = EXCLUDED.codice_hash, scade_il = EXCLUDED.scade_il,
            tentativi = 0, creato_il = EXCLUDED.creato_il
    """, (payload.email_nuova, hash_otp(codice), scadenza_minuti))
    conn.commit()
    conn.close()

    try:
        get_email_provider().invia_otp(payload.email_nuova, codice)
    except Exception as e:
        print(f"[ERRORE] invio OTP cambio email a {payload.email_nuova} fallito: {e}")
        raise HTTPException(502, "Invio dell'email non riuscito — riprova tra qualche istante")
    return {"inviato": True}


@router.post("/users/{user_id}/email-change/confirm")
def conferma_cambio_email(user_id: UUID, payload: EmailChangeConfirmIn):
    """RF-26: verifica l'OTP e applica il cambio email, poi notifica la
    VECCHIA email (avviso di sicurezza, non richiede azione)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE user_id = %s", (str(user_id),))
    utente = cur.fetchone()
    if not utente:
        conn.close()
        raise HTTPException(404, "Utente non trovato")
    email_vecchia = utente["email"]

    # Non conosciamo qui la nuova email dichiarata — cerchiamo tra gli OTP
    # attivi quello il cui codice corrisponde (stesso principio anti
    # user-enumeration di verify-otp: nessun dettaglio extra nell'errore).
    cur.execute("SELECT email, codice_hash, scade_il, tentativi FROM otp_codes")
    candidato = None
    for riga in cur.fetchall():
        if riga["email"] == email_vecchia:
            continue  # non è una richiesta di cambio email
        if verify_otp_hash(payload.codice, riga["codice_hash"]) and riga["scade_il"] >= datetime.now(timezone.utc):
            candidato = riga
            break
    if not candidato:
        conn.close()
        raise HTTPException(401, "Codice non valido o scaduto")

    email_nuova = candidato["email"]
    cur.execute("SELECT 1 FROM users WHERE email = %s", (email_nuova,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(409, "Questa email è già associata a un altro account")

    cur.execute("UPDATE users SET email = %s WHERE user_id = %s", (email_nuova, str(user_id)))
    cur.execute("DELETE FROM otp_codes WHERE email = %s", (email_nuova,))
    conn.commit()
    conn.close()

    try:
        get_email_provider().invia_notifica(
            email_vecchia, "Il tuo indirizzo email Ainima è cambiato",
            f"<p>L'email del tuo account Ainima è stata cambiata in {email_nuova}.</p>"
            f"<p>Se non sei stato tu, contatta subito l'assistenza.</p>",
        )
    except Exception as e:
        print(f"[ERRORE] invio notifica cambio email a {email_vecchia} fallito: {e}")

    return {"email": email_nuova}


@router.post("/account-recovery/request")
def richiedi_recupero_accesso(payload: RecoveryRequestIn):
    """RF-26b: modulo pubblico, non autenticato. Non concede alcun accesso
    automatico — entra nella coda di revisione umana (RF-25d/26c)."""
    dati_identificativi = {
        "nome": payload.nome, "cognome": payload.cognome, "data_nascita": payload.data_nascita,
        "citta": payload.citta, "ultime4cifre_carta": payload.ultime4cifre_carta,
    }
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO email_change_requests
            (email_attuale_dichiarata, email_nuova_richiesta, dati_identificativi_forniti, origine, stato)
        VALUES (%s, %s, %s::jsonb, 'Modulo pubblico recupero accesso', 'In attesa revisione')
    """, (payload.email_attuale_dichiarata, payload.email_nuova_richiesta, json.dumps(dati_identificativi)))
    conn.commit()
    conn.close()
    # Stessa risposta generica indipendentemente dai dati forniti — non
    # conferma né smentisce se l'email dichiarata esiste davvero (anti
    # user-enumeration, stesso principio di RF-02).
    return {"ricevuta": True}


@router.get("/account-recovery/cancel")
def annulla_recupero_accesso(request_id: UUID, token: str):
    """RF-26d: link inviato alla VECCHIA email durante il periodo di grazia
    — annulla il cambio prima che diventi definitivo."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT stato, token_annullamento, data_scadenza_grazia FROM email_change_requests WHERE request_id = %s
    """, (str(request_id),))
    r = cur.fetchone()
    if not r:
        conn.close()
        raise HTTPException(404, "Richiesta non trovata")
    if r["stato"] != "In periodo di grazia" or r["token_annullamento"] != token:
        conn.close()
        raise HTTPException(409, "Link non valido o richiesta non più annullabile")
    if r["data_scadenza_grazia"] and r["data_scadenza_grazia"] < datetime.now(timezone.utc):
        conn.close()
        raise HTTPException(409, "Il periodo di grazia è già scaduto")

    cur.execute("UPDATE email_change_requests SET stato = 'Annullata' WHERE request_id = %s", (str(request_id),))
    conn.commit()
    conn.close()
    return {"annullata": True}
