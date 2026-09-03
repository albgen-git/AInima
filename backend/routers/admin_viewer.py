"""Viewer HTML per sfogliare/correggere a mano i profili di test (RF-25),
esteso con la coda di moderazione (RF-25c), la coda di recupero accesso
(RF-25d) e la console di configurazione (RF-25e). Spostato qui da main.py
invariato nella logica — v. commit precedente.

Autenticazione (v. CLAUDE.md — richiesta esplicita dell'utente,
"rafforzamento dell'autenticazione prima di esporre azioni operative
reali"): prima di questa modifica il pannello admin non aveva ALCUNA
autenticazione, nemmeno sulle route già esistenti (lista/dettaglio/
modifica utenti demo) — chiunque conoscesse l'URL poteva leggere o
scrivere qualsiasi record. HTTP Basic Auth applicata a livello di router
(dependencies=[Depends(verifica_staff)]), quindi protegge automaticamente
sia le route preesistenti sia quelle nuove, senza doverla ripetere su
ognuna. Credenziali da ADMIN_USERNAME/ADMIN_PASSWORD (env, mai hardcoded
— SPECIFICHE di questo ambiente di collaudo: un futuro ambiente di
produzione avrà una propria coppia indipendente, v. .env/render.yaml)."""

import os
import secrets

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from db import get_conn

_basic_auth = HTTPBasic()


def verifica_staff(credentials: HTTPBasicCredentials = Depends(_basic_auth)) -> str:
    """Confronto a tempo costante (secrets.compare_digest, non `==`) per
    non aprire un side-channel timing sulla password — anche se il rischio
    pratico qui è basso, è lo standard corretto per un confronto di
    credenziali. Ritorna lo username, riusato come "operatore" nei log di
    audit (v. _log_azione sotto) — è l'unica identità reale che abbiamo
    oggi, non esiste ancora una tabella staff con id propri."""
    utente_atteso = os.environ.get("ADMIN_USERNAME", "")
    password_attesa = os.environ.get("ADMIN_PASSWORD", "")
    utente_ok = secrets.compare_digest(credentials.username, utente_atteso)
    password_ok = secrets.compare_digest(credentials.password, password_attesa)
    if not (utente_ok and password_ok):
        raise HTTPException(401, "Credenziali non valide", headers={"WWW-Authenticate": "Basic"})
    return credentials.username


def _log_azione(cur, operatore: str, azione: str, dettaglio: str = ""):
    cur.execute(
        "INSERT INTO admin_action_log (operatore, azione, dettaglio) VALUES (%s, %s, %s)",
        (operatore, azione, dettaglio),
    )


router = APIRouter(tags=["admin-viewer"], dependencies=[Depends(verifica_staff)])
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))


def foto_src(url: str | None) -> str:
    """physical_profile.foto_*_url è un path relativo allo storage locale
    (servito da /photos/, v. main.py) in locale, ma un URL R2 già assoluto
    sul pool demo migrato su Render (v. scripts/seed_render_from_local.py)
    — senza questa distinzione il template concatenava sempre "/photos/"
    davanti, producendo un URL rotto (es. "/photos/https://pub-....r2.dev/
    ...") che il browser risolve come path relativo al backend stesso e
    che quindi va sempre in 404 per il pool migrato."""
    if not url:
        return "/photos/"  # mantiene il comportamento onerror esistente per foto assenti
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"/photos/{url}"


templates.env.filters["foto_src"] = foto_src

ENUM_OPTIONS = {
    "genere": ["Maschile", "Femminile", "Non binario", "Altro"],
    "orientamento_sessuale": ["Eterosessuale", "Omosessuale", "Bisessuale", "Pansessuale", "Asessuale", "Altro"],
    "stato_account": ["In attesa", "In attesa - verifica moderazione", "Attivo", "Sospeso", "Chiuso"],
    "livello_abbonamento": ["Free", "Basic", "Premium"],
    "pref_genere_cercato": ["Maschile", "Femminile", "Non binario", "Altro"],
}

EDITABLE_FIELDS = {
    "users": {
        "nome": "text", "cognome": "text", "email": "text", "telefono": "text",
        "email_verificata": "bool", "data_nascita": "date",
        "genere": "enum", "orientamento_sessuale": "enum",
        "stato_civile": "text", "ha_figli": "bool",
        "stato_account": "enum", "livello_abbonamento": "enum",
        "mercato": "text", "valuta": "text", "locale": "text",
    },
    "physical_profile": {
        "altezza_cm": "int", "peso_kg": "float", "corporatura": "text",
        "colore_capelli": "text", "colore_occhi": "text",
        "fumo": "bool", "alcol": "bool", "stile_vita_sport": "text",
    },
    "socio_profile": {
        "comune_residenza": "text", "titolo_studio": "text",
        "settore_occupazionale": "text", "fascia_reddito": "text",
        "fede_religiosa": "text", "importanza_religione": "int",
        "importanza_vicinanza_geografica": "float",
    },
    "dealbreaker_criteria": {
        "pref_genere_cercato": "enum", "pref_eta_min": "int", "pref_eta_max": "int",
        "pref_accetta_figli": "text", "pref_desidera_figli_futuri": "text",
    },
    "soft_criteria": {
        "pref_altezza_min": "int", "pref_altezza_max": "int",
        "pref_fumo": "bool", "pref_alcol": "bool",
        "pref_importanza_religione": "int",
    },
    "psychometric_scores": {
        "score_big5_estroversione": "float", "score_big5_gradevolezza": "float",
        "score_big5_coscienziosita": "float", "score_big5_nevroticismo": "float",
        "score_big5_apertura": "float", "score_maturita_emotiva": "float",
        "ansia_score": "float", "evitamento_score": "float",
        "flag_profilo_per_revisione_dati": "bool",
    },
}


def cast_value(raw: str, tipo: str):
    if raw == "":
        return None
    if tipo == "bool":
        return raw in ("true", "True", "1", "on", "si", "Si")
    if tipo == "int":
        return int(raw)
    if tipo == "float":
        return float(raw)
    return raw


@router.get("/")
def lista(request: Request, q: str = "", offset: int = 0, limit: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    if q:
        cur.execute(
            """
            SELECT u.user_id, u.source_actor_id, u.nome, u.cognome, u.genere,
                   u.stato_account, p.foto_profilo_url
            FROM users u JOIN physical_profile p ON p.user_id = u.user_id
            WHERE u.nome ILIKE %s OR u.cognome ILIKE %s OR u.source_actor_id::text = %s
            ORDER BY u.source_actor_id LIMIT %s OFFSET %s
            """,
            (f"%{q}%", f"%{q}%", q, limit, offset),
        )
    else:
        cur.execute(
            """
            SELECT u.user_id, u.source_actor_id, u.nome, u.cognome, u.genere,
                   u.stato_account, p.foto_profilo_url
            FROM users u JOIN physical_profile p ON p.user_id = u.user_id
            ORDER BY u.source_actor_id LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
    utenti = cur.fetchall()
    cur.execute("SELECT count(*) AS n FROM users")
    totale = cur.fetchone()["n"]
    conn.close()
    return templates.TemplateResponse(request, "list.html", {
        "utenti": utenti, "q": q, "offset": offset, "limit": limit, "totale": totale,
    })


@router.get("/users/{user_id}")
def dettaglio(request: Request, user_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    u = cur.fetchone()
    if not u:
        conn.close()
        raise HTTPException(404, "Utente non trovato")

    tabelle = {}
    for tabella in ["users", "physical_profile", "socio_profile",
                     "dealbreaker_criteria", "soft_criteria", "psychometric_scores"]:
        cur.execute(f"SELECT * FROM {tabella} WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        tabelle[tabella] = row or {}
    conn.close()

    return templates.TemplateResponse(request, "detail.html", {
        "user_id": user_id, "u": u, "tabelle": tabelle,
        "editable": EDITABLE_FIELDS, "enum_options": ENUM_OPTIONS,
    })


@router.post("/users/{user_id}/update")
def aggiorna_campo(user_id: str, tabella: str = Form(...), campo: str = Form(...), valore: str = Form("")):
    if tabella not in EDITABLE_FIELDS or campo not in EDITABLE_FIELDS[tabella]:
        raise HTTPException(400, f"Campo non modificabile: {tabella}.{campo}")

    tipo = EDITABLE_FIELDS[tabella][campo]
    try:
        valore_cast = cast_value(valore, tipo)
    except ValueError:
        raise HTTPException(400, f"Valore non valido per {campo} (atteso {tipo})")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE {tabella} SET {campo} = %s WHERE user_id = %s", (valore_cast, user_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/users/{user_id}", status_code=303)


# ============================================================
# RF-25c — Coda di moderazione contenuti
# ============================================================

@router.get("/moderation")
def coda_moderazione(request: Request):
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
    return templates.TemplateResponse(request, "moderation.html", {"righe": righe})


@router.post("/moderation/{moderation_id}/decision")
def decidi_moderazione(moderation_id: str, approvato: str = Form(...), operatore: str = Depends(verifica_staff)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM content_moderation_log WHERE moderation_id = %s", (moderation_id,))
    riga = cur.fetchone()
    if not riga:
        conn.close()
        raise HTTPException(404, "Voce di moderazione non trovata")

    approvato_bool = approvato == "si"
    esito = "Approvato" if approvato_bool else "Rifiutato"
    cur.execute("""
        UPDATE content_moderation_log SET esito_revisione_umana = %s, data_revisione = now()
        WHERE moderation_id = %s
    """, (esito, moderation_id))

    if approvato_bool:
        cur.execute("""
            UPDATE users SET stato_account = 'In attesa'
            WHERE user_id = %s AND stato_account = 'In attesa - verifica moderazione'
        """, (riga["user_id"],))

    _log_azione(cur, operatore, "moderazione", f"moderation_id={moderation_id} esito={esito}")
    conn.commit()
    conn.close()
    return RedirectResponse(url="/moderation", status_code=303)


# ============================================================
# RF-25d — Coda di richieste di recupero accesso
# ============================================================

@router.get("/recovery")
def coda_recupero_accesso(request: Request):
    """Applica anche, di passaggio, i cambi email con periodo di grazia
    scaduto senza annullamento — stesso sweep già presente in
    GET /admin/recovery/queue (routers/admin.py), nessun cron reale."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT request_id, user_id, email_nuova_richiesta FROM email_change_requests
        WHERE stato = 'In periodo di grazia' AND data_scadenza_grazia < now()
    """)
    scaduti = cur.fetchall()
    for r in scaduti:
        cur.execute("UPDATE users SET email = %s WHERE user_id = %s",
                    (r["email_nuova_richiesta"], r["user_id"]))
        cur.execute("UPDATE email_change_requests SET stato = 'Completata' WHERE request_id = %s",
                    (r["request_id"],))
    if scaduti:
        conn.commit()

    cur.execute("""
        SELECT req.request_id, req.user_id, req.email_attuale_dichiarata, req.email_nuova_richiesta,
               req.dati_identificativi_forniti, req.origine, req.data_richiesta,
               u.user_id AS profilo_user_id, u.nome AS profilo_nome, u.cognome AS profilo_cognome,
               u.email AS profilo_email, u.data_nascita AS profilo_data_nascita
        FROM email_change_requests req
        LEFT JOIN users u ON u.email = req.email_attuale_dichiarata
        WHERE req.stato = 'In attesa revisione'
        ORDER BY req.data_richiesta ASC
    """)
    righe = cur.fetchall()
    conn.close()
    return templates.TemplateResponse(request, "recovery.html", {"righe": righe})


@router.post("/recovery/{request_id}/decision")
def decidi_recupero_accesso(
    request_id: str,
    approvato: str = Form(...),
    user_id: str = Form(""),
    operatore: str = Depends(verifica_staff),
):
    """RF-26c: il rifiuto non spiega mai il motivo (per non aiutare un
    eventuale tentativo di furto d'identità). RF-26d: l'approvazione apre
    il periodo di grazia — stessa logica di POST /admin/recovery/{id}/
    decision (routers/admin.py), qui riscritta in forma form-POST/redirect
    invece di JSON, coerente con lo stile del resto di questo viewer."""
    import secrets as secrets_mod
    from datetime import datetime, timedelta, timezone

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT stato FROM email_change_requests WHERE request_id = %s", (request_id,))
    r = cur.fetchone()
    if not r:
        conn.close()
        raise HTTPException(404, "Richiesta non trovata")
    if r["stato"] != "In attesa revisione":
        conn.close()
        raise HTTPException(409, f"Richiesta già decisa (stato attuale: {r['stato']})")

    approvato_bool = approvato == "si"
    if not approvato_bool:
        cur.execute("""
            UPDATE email_change_requests SET stato = 'Rifiutata', data_decisione = now()
            WHERE request_id = %s
        """, (request_id,))
        _log_azione(cur, operatore, "recupero_accesso", f"request_id={request_id} esito=Rifiutata")
        conn.commit()
        conn.close()
        return RedirectResponse(url="/recovery", status_code=303)

    if not user_id:
        conn.close()
        raise HTTPException(422, "Indica quale profilo esistente corrisponde a questa richiesta prima di approvare")
    cur.execute("SELECT email FROM users WHERE user_id = %s", (user_id,))
    utente = cur.fetchone()
    if not utente:
        conn.close()
        raise HTTPException(404, "user_id indicato non corrisponde a nessun utente")

    cur.execute("SELECT valore FROM system_config WHERE chiave = 'recupero_accesso_grazia_ore'")
    riga_cfg = cur.fetchone()
    grazia_ore = int(riga_cfg["valore"]) if riga_cfg else 48
    token = secrets_mod.token_urlsafe(32)
    scadenza = datetime.now(timezone.utc) + timedelta(hours=grazia_ore)
    cur.execute("""
        UPDATE email_change_requests SET
            stato = 'In periodo di grazia', user_id = %s, data_decisione = now(),
            data_scadenza_grazia = %s, token_annullamento = %s
        WHERE request_id = %s
    """, (user_id, scadenza, token, request_id))
    _log_azione(cur, operatore, "recupero_accesso", f"request_id={request_id} esito=Approvata user_id={user_id}")
    conn.commit()
    conn.close()

    email_vecchia = utente["email"]
    try:
        from services.email_provider import get_email_provider
        get_email_provider().invia_notifica(
            email_vecchia, "Richiesta di cambio email sul tuo account Ainima",
            f"<p>È stata approvata una richiesta di cambio email per il tuo account.</p>"
            f"<p>Se sei stato tu, non devi fare nulla: il cambio si completerà tra {grazia_ore} ore.</p>"
            f"<p>Se NON sei stato tu, annulla subito con questo link: "
            f"/account-recovery/cancel?request_id={request_id}&token={token}</p>",
        )
    except Exception as e:
        print(f"[ERRORE] invio notifica recupero accesso a {email_vecchia} fallito: {e}")

    return RedirectResponse(url="/recovery", status_code=303)


# ============================================================
# RF-25e — Console di configurazione centralizzata
# ============================================================

# Chiavi trattate come booleane sì/no nel form (checkbox), non testo
# libero — solo verifica_carta_attiva oggi, ma un elenco esplicito invece
# di indovinare dal valore corrente ('true'/'false') tiene la UI corretta
# anche se in futuro altre chiavi bool si aggiungono.
CONFIG_CHIAVI_BOOL = {"verifica_carta_attiva"}

# Chiavi per cui una disattivazione (true -> false) richiede la conferma
# esplicita a due passaggi (RF-25e, richiesta esplicita dell'utente) —
# non tutte le chiavi bool future avranno per forza questo stesso vincolo,
# quindi elenco dedicato invece di applicarlo a tutto CONFIG_CHIAVI_BOOL.
CONFIG_CHIAVI_RICHIEDONO_CONFERMA = {"verifica_carta_attiva"}


@router.get("/config")
def console_configurazione(request: Request):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT chiave, valore, descrizione, data_ultima_modifica FROM system_config ORDER BY chiave")
    righe = cur.fetchall()
    conn.close()
    return templates.TemplateResponse(request, "config.html", {
        "righe": righe, "chiavi_bool": CONFIG_CHIAVI_BOOL,
    })


@router.post("/config/{chiave}/update")
def aggiorna_configurazione(
    chiave: str,
    valore: str = Form(...),
    conferma_disattivazione: str = Form(""),
    operatore: str = Depends(verifica_staff),
):
    """Salvataggio esplicito (form POST, non auto-save) + traccia ogni
    modifica in admin_action_log con valore precedente -> nuovo (RF-25e).
    Per le chiavi in CONFIG_CHIAVI_RICHIEDONO_CONFERMA: una disattivazione
    (true -> false) senza la checkbox di conferma spuntata (lato server,
    non solo il dialog JS lato client in config.html) viene rifiutata —
    difesa in profondità, coerente con il principio già seguito altrove
    nel progetto di non fidarsi di un solo controllo lato client per
    un'azione con implicazioni di sicurezza."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT valore FROM system_config WHERE chiave = %s", (chiave,))
    riga = cur.fetchone()
    if not riga:
        conn.close()
        raise HTTPException(404, f"Parametro '{chiave}' non esistente in system_config")
    valore_precedente = riga["valore"]

    if (chiave in CONFIG_CHIAVI_RICHIEDONO_CONFERMA
            and valore_precedente == "true" and valore == "false"
            and conferma_disattivazione != "si"):
        conn.close()
        raise HTTPException(400, f"Disattivare '{chiave}' richiede la conferma esplicita — riprova spuntando la casella di conferma")

    cur.execute("""
        UPDATE system_config SET valore = %s, data_ultima_modifica = now()
        WHERE chiave = %s
    """, (valore, chiave))
    _log_azione(cur, operatore, "modifica_config", f"chiave={chiave} da='{valore_precedente}' a='{valore}'")
    conn.commit()
    conn.close()
    return RedirectResponse(url="/config", status_code=303)
