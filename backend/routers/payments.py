"""RF-17: addebito della fee di match confermato a entrambe le parti
(cattura della pre-autorizzazione). Stub: nessuna vera integrazione col
gateway (es. Stripe) — v. TODO. L'importo viene letto da system_config,
mai hardcoded (requisito esplicito ripetuto nei documenti)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from db import get_conn

router = APIRouter(prefix="/users/{user_id}/matches/{match_id}", tags=["payments"])


@router.post("/pay")
def paga_match(user_id: UUID, match_id: UUID):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_a_id, user_b_id, stato, pagamento_a_stato, pagamento_b_stato FROM matches WHERE match_id = %s",
                (str(match_id),))
    m = cur.fetchone()
    if not m:
        conn.close()
        raise HTTPException(404, "Match non trovato")
    if m["stato"] != "Confermato":
        conn.close()
        raise HTTPException(409, "Il match non è ancora stato accettato da entrambe le parti")
    if str(user_id) not in (str(m["user_a_id"]), str(m["user_b_id"])):
        conn.close()
        raise HTTPException(403, "Questo match non appartiene all'utente indicato")

    cur.execute("SELECT valore FROM system_config WHERE chiave = 'fee_match_confermato_eur'")
    fee = cur.fetchone()["valore"]

    lato = "a" if str(user_id) == str(m["user_a_id"]) else "b"
    cur.execute(f"UPDATE matches SET pagamento_{lato}_stato = 'Pagato' WHERE match_id = %s", (str(match_id),))

    cur.execute("SELECT pagamento_a_stato, pagamento_b_stato FROM matches WHERE match_id = %s", (str(match_id),))
    stati = cur.fetchone()
    entrambi_pagati = False
    # il lato appena aggiornato non è ancora visibile nella lettura sopra
    # con alcuni driver: normalizza esplicitamente prima del confronto
    pagamento_a = "Pagato" if lato == "a" else stati["pagamento_a_stato"]
    pagamento_b = "Pagato" if lato == "b" else stati["pagamento_b_stato"]
    if pagamento_a == "Pagato" and pagamento_b == "Pagato":
        entrambi_pagati = True
        cur.execute("""
            UPDATE matches SET data_conferma = now(), contatto_scambiato = TRUE
            WHERE match_id = %s
        """, (str(match_id),))

    conn.commit()
    conn.close()
    return {
        "pagato": True, "fee_eur": fee, "nota": "stub, nessun addebito reale sul gateway",
        "contatti_sbloccati": entrambi_pagati,
    }
