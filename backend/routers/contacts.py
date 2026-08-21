"""RF-20..RF-22b: scambio contatto via vCard e "Rubrica" degli abbinamenti conclusi."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response

from db import get_conn

router = APIRouter(tags=["contacts"])


@router.get("/users/{user_id}/matches/{match_id}/vcard")
def scarica_vcard(user_id: UUID, match_id: UUID):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_a_id, user_b_id, contatto_scambiato FROM matches WHERE match_id = %s
    """, (str(match_id),))
    m = cur.fetchone()
    if not m:
        conn.close()
        raise HTTPException(404, "Match non trovato")
    if str(user_id) not in (str(m["user_a_id"]), str(m["user_b_id"])):
        conn.close()
        raise HTTPException(403, "Questo match non appartiene all'utente indicato")
    if not m["contatto_scambiato"]:
        conn.close()
        raise HTTPException(409, "Contatto non ancora sbloccato — serve la conferma e il pagamento di entrambe le parti (RF-20)")

    altro_id = m["user_b_id"] if str(user_id) == str(m["user_a_id"]) else m["user_a_id"]
    cur.execute("SELECT nome, cognome, email, telefono FROM users WHERE user_id = %s", (str(altro_id),))
    altro = cur.fetchone()
    conn.close()

    # RF-20/RF-21: il contatto principale è l'email (verificata via OTP),
    # non più il telefono — che resta autodichiarato/non verificato (RF-02b)
    # e va incluso solo come informazione secondaria, se presente.
    righe = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{altro['nome']} {altro['cognome']}",
        f"N:{altro['cognome']};{altro['nome']};;;",
        f"EMAIL;TYPE=INTERNET:{altro['email']}",
    ]
    if altro["telefono"]:
        righe.append(f"TEL;TYPE=CELL:{altro['telefono']}")
    righe.append("END:VCARD")
    vcard = "\r\n".join(righe) + "\r\n"
    return Response(
        content=vcard, media_type="text/vcard",
        headers={"Content-Disposition": f'attachment; filename="{altro["nome"]}_{altro["cognome"]}.vcf"'},
    )


@router.get("/users/{user_id}/rubrica")
def rubrica(user_id: UUID):
    """RF-22b: elenco degli abbinamenti conclusi con successo."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.match_id, m.data_conferma,
               CASE WHEN m.user_a_id = %s THEN m.user_b_id ELSE m.user_a_id END AS altro_id
        FROM matches m
        WHERE (m.user_a_id = %s OR m.user_b_id = %s) AND m.contatto_scambiato = TRUE
        ORDER BY m.data_conferma DESC
    """, (str(user_id), str(user_id), str(user_id)))
    righe = cur.fetchall()

    voci = []
    for r in righe:
        cur.execute("""
            SELECT u.nome, u.cognome, p.foto_profilo_url
            FROM users u JOIN physical_profile p ON p.user_id = u.user_id
            WHERE u.user_id = %s
        """, (str(r["altro_id"]),))
        altro = cur.fetchone()
        voci.append({
            "match_id": r["match_id"], "data_conferma": r["data_conferma"],
            "nome": altro["nome"], "cognome": altro["cognome"], "foto_profilo_url": altro["foto_profilo_url"],
        })
    conn.close()
    return voci
