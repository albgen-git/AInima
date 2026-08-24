"""Blocco E (v. CLAUDE.md — Ainima_Dashboard_Trigger_Email_v1.md,
Ainima_Engagement_Periodico_v1_BOZZA.md): domande di affinamento, pillole
di saggezza, coda email. Logica vera in services/engagement.py — qui solo
gli endpoint HTTP."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import get_conn
from services import engagement

router = APIRouter(prefix="/users/{user_id}", tags=["engagement"])


class RispostaAffinamento(BaseModel):
    risposta: int  # 1-5


@router.get("/affinamento/pendenti")
def domande_affinamento_pendenti(user_id: UUID):
    """Item già assegnati a questo utente ma non ancora risposti — quelli
    mostrati dalla card dashboard "Domande di affinamento pendenti" (§1)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT dp.item_id, dp.testo_it, dp.testo_en FROM domande_affinamento_log dl
        JOIN domande_affinamento_pool dp ON dp.item_id = dl.item_id
        WHERE dl.user_id = %s AND dl.risposta IS NULL
        ORDER BY dl.data_posta
    """, (str(user_id),))
    righe = cur.fetchall()
    conn.close()
    return righe


@router.post("/affinamento/{item_id}/risposta")
def rispondi_affinamento(user_id: UUID, item_id: UUID, payload: RispostaAffinamento):
    if not (1 <= payload.risposta <= 5):
        raise HTTPException(422, "Risposta fuori scala 1-5")
    conn = get_conn()
    cur = conn.cursor()
    try:
        engagement.registra_risposta_affinamento(cur, user_id, item_id, payload.risposta)
    except ValueError as e:
        conn.close()
        raise HTTPException(409, str(e))
    conn.commit()
    conn.close()
    return {"registrato": True}


@router.get("/pillole/pendente")
def pillola_pendente(user_id: UUID):
    """Ultima pillola inviata non ancora aperta — la card dashboard
    "Pillola da leggere" (§1). None se non c'è nulla di pendente."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT pl.pillola_id, pl.titolo, pl.testo, pl.pilastro_editoriale FROM pillole_inviate_log pil
        JOIN pillole_libreria pl ON pl.pillola_id = pil.pillola_id
        WHERE pil.user_id = %s AND pil.aperta = FALSE
        ORDER BY pil.data_invio DESC LIMIT 1
    """, (str(user_id),))
    riga = cur.fetchone()
    conn.close()
    return riga


@router.post("/pillole/{pillola_id}/aperta")
def segna_pillola_aperta(user_id: UUID, pillola_id: UUID):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE pillole_inviate_log SET aperta = TRUE WHERE user_id = %s AND pillola_id = %s",
                (str(user_id), str(pillola_id)))
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Pillola non trovata per questo utente")
    conn.commit()
    conn.close()
    return {"aggiornato": True}


# ── Trigger admin/manuali — nessuno scheduler reale (v. CLAUDE.md) ────────

@router.post("/affinamento/assegna", tags=["admin"])
def assegna_domande_affinamento_admin(user_id: UUID, n: int = 2):
    """T1 — pesca n item dal pool (fonte 'item di riserva', §2.1) e li
    mette in coda email. Da invocare periodicamente per l'intero pool
    Attivo finché non esiste un vero scheduler."""
    conn = get_conn()
    cur = conn.cursor()
    assegnati = engagement.assegna_domande_affinamento(cur, user_id, n)
    conn.commit()
    conn.close()
    return {"assegnati": [dict(a) for a in assegnati]}


@router.post("/pillole/assegna", tags=["admin"])
def assegna_pillola_admin(user_id: UUID, contesto_trigger: str = "Attesa generale"):
    """T2 — assegna la pillola più adatta (tag-matching, §3.2) e la mette
    in coda email."""
    conn = get_conn()
    cur = conn.cursor()
    pillola = engagement.assegna_pillola(cur, user_id, contesto_trigger)
    conn.commit()
    conn.close()
    if pillola is None:
        return {"assegnata": None}
    return {"assegnata": dict(pillola)}
