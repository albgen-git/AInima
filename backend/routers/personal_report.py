"""RF-28..RF-30b: report di analisi personale — endpoint di sola lettura
del report più recente + feedback. La generazione automatica NON avviene
qui: è agganciata ai 4 endpoint di submission dei test psicometrici (v.
routers/psychometric.py, che chiama services/personal_report.py subito
dopo aver committato il punteggio)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from db import get_conn
from schemas.personal_report import PersonalReportFeedbackIn
from services import personal_report

router = APIRouter(prefix="/users/{user_id}/personal-report", tags=["personal-report"])


@router.get("")
def ultimo_report(user_id: UUID):
    """RF: recupera l'ultima versione del report generata per l'utente."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT report_id, contenuto_report, versione, data_generazione, email_inviata
        FROM personal_report WHERE user_id = %s ORDER BY versione DESC LIMIT 1
    """, (str(user_id),))
    r = cur.fetchone()
    conn.close()
    if not r:
        return {"pronto": False}
    return {
        "pronto": True,
        "report_id": r["report_id"],
        "contenuto_report": r["contenuto_report"],
        "versione": r["versione"],
        "data_generazione": r["data_generazione"],
        "email_inviata": r["email_inviata"],
    }


@router.post("/regenerate")
def rigenera_report(user_id: UUID):
    """RF-30b: rigenerazione su richiesta — usata dal trigger automatico
    agganciato ai 4 endpoint di submission (v. routers/psychometric.py),
    ma esposta anche qui per i casi in cui i 4 test erano già completi
    PRIMA che questo meccanismo esistesse (nessun trigger sarebbe mai
    scattato altrimenti). No-op (204) se i 4 test non sono ancora tutti
    completi."""
    conn = get_conn()
    cur = conn.cursor()
    if not personal_report.quattro_test_completi(cur, user_id):
        conn.close()
        raise HTTPException(409, "I 4 test psicometrici non sono ancora tutti completi")
    testo = personal_report.genera_e_salva(conn, cur, user_id)
    conn.close()
    return {"generato": testo is not None}


@router.get("/{report_id}/feedback")
def leggi_feedback_report(user_id: UUID, report_id: UUID):
    """RF-30: feedback già lasciato dall'utente su questa versione di
    report, se esiste — usato dal frontend per precompilare stelle/
    commento invece di mostrare un form vuoto quando l'utente torna sulla
    stessa versione."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT valutazione_stelle, commento_libero FROM personal_report_feedback
        WHERE report_id = %s AND user_id = %s
    """, (str(report_id), str(user_id)))
    r = cur.fetchone()
    conn.close()
    if not r:
        return {"esiste": False}
    return {"esiste": True, "valutazione_stelle": r["valutazione_stelle"], "commento_libero": r["commento_libero"]}


@router.post("/{report_id}/feedback")
def invia_feedback_report(user_id: UUID, report_id: UUID, payload: PersonalReportFeedbackIn):
    """RF-30: valutazione a stelle (1-5, obbligatoria) + commento libero
    opzionale. Un solo feedback per utente per versione di report — se
    richiamato sulla stessa versione, aggiorna invece di duplicare."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM personal_report WHERE report_id = %s", (str(report_id),))
    r = cur.fetchone()
    if not r:
        conn.close()
        raise HTTPException(404, "Report non trovato")
    if str(r["user_id"]) != str(user_id):
        conn.close()
        raise HTTPException(403, "Questo report non appartiene all'utente indicato")

    cur.execute("""
        INSERT INTO personal_report_feedback (report_id, user_id, valutazione_stelle, commento_libero)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (report_id, user_id) DO UPDATE SET
            valutazione_stelle = EXCLUDED.valutazione_stelle,
            commento_libero = EXCLUDED.commento_libero,
            data_feedback = now()
    """, (str(report_id), str(user_id), payload.valutazione_stelle, payload.commento_libero))
    conn.commit()
    conn.close()
    return {"registrato": True}
