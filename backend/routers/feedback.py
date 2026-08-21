"""RF-23/24: feedback raccolto 15gg dopo la chiusura del task, usato per
affinare i match successivi dello stesso utente."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from db import get_conn
from schemas.matching import FeedbackIn

router = APIRouter(prefix="/users/{user_id}/matches/{match_id}", tags=["feedback"])


@router.post("/feedback")
def invia_feedback(user_id: UUID, match_id: UUID, payload: FeedbackIn):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_a_id, user_b_id, contatto_scambiato FROM matches WHERE match_id = %s", (str(match_id),))
    m = cur.fetchone()
    if not m:
        conn.close()
        raise HTTPException(404, "Match non trovato")
    if str(user_id) not in (str(m["user_a_id"]), str(m["user_b_id"])):
        conn.close()
        raise HTTPException(403, "Questo match non appartiene all'utente indicato")
    if not m["contatto_scambiato"]:
        conn.close()
        raise HTTPException(409, "Il task non risulta ancora concluso")

    cur.execute("""
        INSERT INTO match_feedback (match_id, user_id, data_richiesta, data_risposta, esito, note_libere)
        VALUES (%s, %s, now(), now(), %s, %s)
        ON CONFLICT (match_id, user_id) DO UPDATE SET
            data_risposta = now(), esito = EXCLUDED.esito, note_libere = EXCLUDED.note_libere
    """, (str(match_id), str(user_id), payload.esito, payload.note_libere))
    conn.commit()
    conn.close()
    return {"registrato": True}
