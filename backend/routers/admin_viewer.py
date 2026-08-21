"""Viewer HTML per sfogliare/correggere a mano i profili di test (RF-25).
Spostato qui da main.py invariato nella logica — v. commit precedente."""

import os

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from db import get_conn

router = APIRouter(tags=["admin-viewer"])
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))

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
