"""RF-02, RF-02b, RF-03/04, RF-09: autenticazione via email OTP (niente
password permanente), telefono autodichiarato senza verifica, metodo di
pagamento, stato onboarding. V. Documento_Requisiti_v1_2.md §4.1 — questa
versione del documento requisiti sostituisce la verifica telefonica via
SMS della v1 originale, v. CLAUDE.md per la cronologia della decisione."""

import calendar
import random
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from db import get_conn
from rate_limit import controlla_e_registra
from schemas.users import (
    PaymentMethodRequest, RequestOtpRequest, VerifyOtpRequest, VerifyOtpResponse,
)
from security import create_session_token, hash_otp, verify_otp_hash
from services.email_provider import get_email_provider

# Ordine degli step del wizard onboarding lato frontend (v.
# frontend/src/app/[locale]/onboarding/page.tsx STEP_KEYS) — usato per dire
# da dove riprendere dopo la verifica OTP, invece di saltare sempre allo
# stesso punto fisso. STEP_EMAIL/STEP_OTP_VERIFY precedono la creazione
# dell'account con dati anagrafici (l'utente esiste già in DB dopo
# request-otp, ma con la sola email) quindi non sono mai un valore di
# ritorno reale di primo_passo_incompleto — ci sono solo per tenere gli
# indici allineati 1:1 con l'array frontend.
#
# 2026-08-19 (v. CLAUDE.md): lo STEP_INTERVIEW (chat EQ) è sostituito da 3
# step scritti — STEP_ATTACCAMENTO, STEP_EQ (test a punteggio deterministico)
# e STEP_NARRATIVE (i due campi liberi RF-07b) — 13 step diventano 15.
# 2026-08-20: + STEP_INTEREST_TAGS (RF-08c, liste "mi piace/non sopporto") — 16 step.
STEP_EMAIL, STEP_OTP_VERIFY, STEP_BASIC_INFO, STEP_SENSITIVE_CONSENT, STEP_ORIENTATION, \
    STEP_PAYMENT, STEP_CIVIL_STATUS, STEP_PROFILE, STEP_PHOTOS, STEP_PREFERENCES, \
    STEP_BIGFIVE, STEP_ATTACCAMENTO, STEP_EQ, STEP_NARRATIVE, STEP_INTEREST_TAGS, \
    STEP_SUMMARY = range(16)

router = APIRouter(prefix="/auth", tags=["auth"])


def _config_int(cur, chiave: str, default: int) -> int:
    cur.execute("SELECT valore FROM system_config WHERE chiave = %s", (chiave,))
    r = cur.fetchone()
    return int(r["valore"]) if r else default


@router.post("/request-otp")
def richiedi_otp(payload: RequestOtpRequest, request: Request):
    """RF-02: primo contatto per un utente nuovo O di ritorno — stessa
    richiesta e stessa risposta per entrambi i casi (anti user-enumeration).
    Se l'email non esiste ancora crea l'account in stato 'In attesa' con
    la sola email; il resto dei dati anagrafici si compila negli step
    successivi del wizard (v. CLAUDE.md)."""
    conn = get_conn()
    cur = conn.cursor()

    ip = request.client.host if request.client else "sconosciuto"
    limite_ip = _config_int(cur, "otp_rate_limit_ip_per_ora", 10)
    if not controlla_e_registra(ip, limite_ip):
        conn.close()
        raise HTTPException(429, "Troppe richieste da questo indirizzo — riprova più tardi")

    cooldown = _config_int(cur, "otp_richiesta_cooldown_secondi", 60)
    cur.execute("SELECT creato_il FROM otp_codes WHERE email = %s", (payload.email,))
    riga_otp = cur.fetchone()
    if riga_otp:
        eta_secondi = (datetime.now(timezone.utc) - riga_otp["creato_il"]).total_seconds()
        if eta_secondi < cooldown:
            conn.close()
            raise HTTPException(429, f"Attendi almeno {int(cooldown - eta_secondi)} secondi prima di richiedere un nuovo codice")

    cur.execute("SELECT user_id FROM users WHERE email = %s", (payload.email,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (email, stato_account) VALUES (%s, 'In attesa') RETURNING user_id",
            (payload.email,),
        )
        nuovo = cur.fetchone()
        # righe vuote nelle tabelle satellite, cosi' i join successivi (profilo,
        # preferenze) possono usare UPDATE invece di dover distinguere INSERT/UPDATE
        for tabella in ("physical_profile", "socio_profile", "dealbreaker_criteria",
                        "soft_criteria", "psychometric_scores"):
            cur.execute(f"INSERT INTO {tabella} (user_id) VALUES (%s)", (nuovo["user_id"],))

    codice = f"{random.randint(0, 999999):06d}"
    scadenza_minuti = _config_int(cur, "otp_scadenza_minuti", 10)
    cur.execute("""
        INSERT INTO otp_codes (email, codice_hash, scade_il, tentativi, creato_il)
        VALUES (%s, %s, now() + (%s || ' minutes')::interval, 0, now())
        ON CONFLICT (email) DO UPDATE SET
            codice_hash = EXCLUDED.codice_hash, scade_il = EXCLUDED.scade_il,
            tentativi = 0, creato_il = EXCLUDED.creato_il
    """, (payload.email, hash_otp(codice), scadenza_minuti))
    conn.commit()
    conn.close()

    try:
        get_email_provider().invia_otp(payload.email, codice)
    except Exception as e:
        # mai il codice in chiaro nei log applicativi — solo il fatto che
        # l'invio è fallito, per debug locale (v. CLAUDE.md requisito sicurezza)
        print(f"[ERRORE] invio OTP a {payload.email} fallito: {e}")
        raise HTTPException(502, "Invio dell'email non riuscito — riprova tra qualche istante")

    return {"inviato": True}


@router.post("/verify-otp", response_model=VerifyOtpResponse)
def verifica_otp(payload: VerifyOtpRequest):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT codice_hash, scade_il, tentativi FROM otp_codes WHERE email = %s", (payload.email,))
    riga = cur.fetchone()

    def _rifiuta(status: int, messaggio: str):
        conn.close()
        raise HTTPException(status, messaggio)

    if not riga:
        # stesso messaggio generico usato anche per codice errato/scaduto
        # sotto — non si rivela mai se per quella email non è mai stato
        # richiesto un codice (anti user-enumeration)
        _rifiuta(401, "Codice non valido o scaduto")

    tentativi_massimi = _config_int(cur, "otp_tentativi_massimi", 5)
    if riga["tentativi"] >= tentativi_massimi:
        _rifiuta(429, "Troppi tentativi falliti — richiedi un nuovo codice")

    scaduto = riga["scade_il"] < datetime.now(timezone.utc)
    valido = not scaduto and verify_otp_hash(payload.codice, riga["codice_hash"])

    if not valido:
        cur.execute("UPDATE otp_codes SET tentativi = tentativi + 1 WHERE email = %s", (payload.email,))
        conn.commit()
        _rifiuta(401, "Codice non valido o scaduto")

    cur.execute("DELETE FROM otp_codes WHERE email = %s", (payload.email,))
    cur.execute(
        "UPDATE users SET email_verificata = TRUE WHERE email = %s RETURNING user_id, stato_account",
        (payload.email,),
    )
    utente = cur.fetchone()
    scadenza_giorni = _config_int(cur, "jwt_scadenza_giorni", 30)
    conn.commit()
    conn.close()

    token = create_session_token(utente["user_id"], scadenza_giorni)
    return VerifyOtpResponse(user_id=utente["user_id"], stato_account=utente["stato_account"], token=token)


@router.post("/{user_id}/payment-method")
def registra_metodo_pagamento(user_id: UUID, payload: PaymentMethodRequest):
    """RF-03/04. Stub: salva il token già tokenizzato dal client, NON esegue
    davvero la pre-autorizzazione simbolica sul gateway (es. Stripe) —
    TODO integrazione reale prima del lancio. Nessun dato di carta in
    chiaro arriva qui (RNF-06)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET metodo_pagamento_token = %s WHERE user_id = %s RETURNING user_id",
        (payload.metodo_pagamento_token, str(user_id)),
    )
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "Utente non trovato")
    conn.commit()
    conn.close()
    return {"pre_autorizzato": True, "nota": "stub, nessun addebito reale"}


@router.get("/{user_id}/status")
def stato_onboarding(user_id: UUID):
    """RF-09: l'account passa 'In attesa' -> 'Attivo' solo quando email
    verificata + carta verificata + profilo minimo (incluso telefono
    autodichiarato) + test Big Five sono tutti completi
    (checklist/onboarding_completo) — stesso sottoinsieme minimo di prima,
    il test Attaccamento/EQ/i campi liberi non sono un gate per 'Attivo'
    (mai lo era stata la vecchia chat-intervista). Se un'immagine risulta
    'Sospetta' alla moderazione (RF-06b), stato_account diventa 'In attesa
    - verifica moderazione' e non transita mai automaticamente ad 'Attivo'
    (il confronto sotto richiede stato_account == 'In attesa' esatto).
    Aggiunge anche primo_passo_incompleto: indice (0-15, v. STEP_* sopra)
    del primo passo del wizard non ancora completato, usato per riprendere
    da dove l'utente era rimasto — copre più passi di quelli richiesti per
    'Attivo' (stato civile, foto, criteri, attaccamento/EQ/narrativa)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.email_verificata, u.metodo_pagamento_token, u.stato_account,
               u.nome IS NOT NULL AND u.cognome IS NOT NULL
                   AND u.data_nascita IS NOT NULL AND u.genere IS NOT NULL AS info_base_ok,
               u.consenso_dati_sensibili AS consenso_ok,
               u.orientamento_sessuale IS NOT NULL AS orientamento_ok,
               u.telefono IS NOT NULL AS telefono_ok,
               u.stato_civile IS NOT NULL AS stato_civile_ok,
               p.altezza_cm IS NOT NULL AS profilo_fisico_ok,
               p.foto_profilo_url IS NOT NULL AS foto_profilo_ok,
               d.pref_eta_min IS NOT NULL AS preferenze_ok,
               ps.score_big5_estroversione IS NOT NULL AS bigfive_ok,
               ps.ansia_score IS NOT NULL AS attaccamento_ok,
               ps.eq_pilastro_autoconsapevolezza IS NOT NULL AS eq_ok,
               pn.descrizione_di_se IS NOT NULL AND pn.descrizione_partner_ideale IS NOT NULL AS narrativa_ok,
               it.data_ultima_modifica IS NOT NULL AS liste_ok
        FROM users u
        JOIN physical_profile p ON p.user_id = u.user_id
        JOIN dealbreaker_criteria d ON d.user_id = u.user_id
        JOIN psychometric_scores ps ON ps.user_id = u.user_id
        LEFT JOIN profile_narrative pn ON pn.user_id = u.user_id
        LEFT JOIN interest_tags it ON it.user_id = u.user_id
        WHERE u.user_id = %s
    """, (str(user_id),))
    r = cur.fetchone()
    if not r:
        conn.close()
        raise HTTPException(404, "Utente non trovato")

    profilo_minimo_ok = r["profilo_fisico_ok"] and r["telefono_ok"]
    checklist = {
        "email_verificata": r["email_verificata"],
        "carta_registrata": r["metodo_pagamento_token"] is not None,
        "profilo_fisico_compilato": profilo_minimo_ok,
        "test_bigfive_completato": r["bigfive_ok"],
        # 2026-08-19 (v. CLAUDE.md): attaccamento/EQ sono ora test scritti
        # obbligatori al pari del Big Five (RF-07, non più opzionali come lo
        # era la vecchia chat-intervista) — devono far parte del gate
        # 'Attivo', altrimenti l'account si attiva subito dopo il Big Five
        # (unico controllo di prima) e l'utente viene rimandato alla
        # dashboard senza mai attraversare questi due step del wizard.
        "test_attaccamento_completato": r["attaccamento_ok"],
        "test_eq_completato": r["eq_ok"],
    }
    completo = all(checklist.values())

    if completo and r["stato_account"] == "In attesa":
        cur.execute("UPDATE users SET stato_account = 'Attivo' WHERE user_id = %s", (str(user_id),))
        conn.commit()
        r = {**r, "stato_account": "Attivo"}
    conn.close()

    carta_ok = r["metodo_pagamento_token"] is not None
    primo_passo_incompleto = STEP_SUMMARY
    if not r["email_verificata"]:
        primo_passo_incompleto = STEP_BASIC_INFO
    elif not r["info_base_ok"]:
        primo_passo_incompleto = STEP_BASIC_INFO
    elif not r["consenso_ok"]:
        primo_passo_incompleto = STEP_SENSITIVE_CONSENT
    elif not r["orientamento_ok"]:
        primo_passo_incompleto = STEP_ORIENTATION
    elif not carta_ok:
        primo_passo_incompleto = STEP_PAYMENT
    elif not r["stato_civile_ok"]:
        primo_passo_incompleto = STEP_CIVIL_STATUS
    elif not profilo_minimo_ok:
        primo_passo_incompleto = STEP_PROFILE
    elif not r["foto_profilo_ok"]:
        primo_passo_incompleto = STEP_PHOTOS
    elif not r["preferenze_ok"]:
        primo_passo_incompleto = STEP_PREFERENCES
    elif not r["bigfive_ok"]:
        primo_passo_incompleto = STEP_BIGFIVE
    elif not r["attaccamento_ok"]:
        primo_passo_incompleto = STEP_ATTACCAMENTO
    elif not r["eq_ok"]:
        primo_passo_incompleto = STEP_EQ
    elif not r["narrativa_ok"]:
        primo_passo_incompleto = STEP_NARRATIVE
    elif not r["liste_ok"]:
        primo_passo_incompleto = STEP_INTEREST_TAGS

    return {
        "stato_account": r["stato_account"], "checklist": checklist, "onboarding_completo": completo,
        "primo_passo_incompleto": primo_passo_incompleto,
    }


def _prossima_data_ciclo(giorno_esecuzione: int) -> date:
    """Prossima occorrenza futura del giorno_esecuzione del mese (es. 1 =
    primo del mese). Se oggi è già passato quel giorno questo mese, salta
    al mese successivo. Puramente presentazionale: non esiste ancora un
    vero cron che lancia il batch a quella data (v. RF-11, run-cycle è
    lanciato manualmente/da admin in questo scheletro)."""
    oggi = date.today()
    ultimo_giorno_mese_corrente = calendar.monthrange(oggi.year, oggi.month)[1]
    giorno_effettivo = min(giorno_esecuzione, ultimo_giorno_mese_corrente)
    candidata = date(oggi.year, oggi.month, giorno_effettivo)
    if candidata >= oggi:
        return candidata
    mese, anno = (oggi.month % 12) + 1, oggi.year + (1 if oggi.month == 12 else 0)
    ultimo_giorno_prossimo_mese = calendar.monthrange(anno, mese)[1]
    return date(anno, mese, min(giorno_esecuzione, ultimo_giorno_prossimo_mese))


@router.get("/{user_id}/dashboard")
def dashboard(user_id: UUID):
    """Dati di riepilogo per la home dell'utente: stato account, stato
    abbonamento, prossima data prevista del ciclo di matching mensile,
    presenza di una proposta attiva. Campi aggiunti su richiesta esplicita
    (non esposti da nessun altro endpoint) — v. CLAUDE.md."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT stato_account, livello_abbonamento, data_scadenza_abbonamento
        FROM users WHERE user_id = %s
    """, (str(user_id),))
    u = cur.fetchone()
    if not u:
        conn.close()
        raise HTTPException(404, "Utente non trovato")

    cur.execute("SELECT valore FROM system_config WHERE chiave = 'giorno_esecuzione_ciclo_mensile'")
    giorno_ciclo = int(cur.fetchone()["valore"])

    cur.execute("""
        SELECT 1 FROM matches
        WHERE (user_a_id = %s OR user_b_id = %s) AND stato IN ('Proposto', 'Accettato_A', 'Accettato_B')
    """, (str(user_id), str(user_id)))
    ha_proposta_attiva = cur.fetchone() is not None
    conn.close()

    return {
        "stato_account": u["stato_account"],
        "livello_abbonamento": u["livello_abbonamento"],
        "data_scadenza_abbonamento": u["data_scadenza_abbonamento"],
        "prossima_data_ciclo": _prossima_data_ciclo(giorno_ciclo) if u["stato_account"] == "Attivo" else None,
        "ha_proposta_attiva": ha_proposta_attiva,
    }
