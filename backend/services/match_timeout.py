"""RF-14b/14c/14d: timeout dei match senza risposta decisiva entro la
finestra (`data_scadenza_risposta`, 7 giorni). Eseguito dal cron
giornaliero già esistente (RF-32d, services/engagement_scheduler.py) —
nessun processo separato, come richiesto esplicitamente dal documento.

Distinzione di prodotto chiave (RF-14b): il timeout NON è un rifiuto — una
coppia scaduta per mancata risposta resta eleggibile per future proposte
(v. matching_engine.load_coppie_escluse, che esclude solo Confermato/
Rifiutato). L'email di questo modulo riflette lo stesso principio: tono
neutro, mai un giudizio, mai "l'altra persona non ha risposto"/"tu non hai
risposto" — importante specialmente per chi aveva già accettato, per non
farlo sembrare un rifiuto personale rivolto a lui/lei (RF-14c)."""

from services import email_provider

OGGETTO_TIMEOUT = "La finestra per la vostra proposta di abbinamento è scaduta"

CORPO_TIMEOUT = """<p>Ciao {nome},</p>
<p>la finestra di una settimana per confermare la proposta di abbinamento che ti abbiamo inviato è scaduta senza una conferma reciproca da entrambe le parti.</p>
<p>Non significa che la proposta sia stata rifiutata, e non riflette in alcun modo la qualità del tuo profilo — succede, ed è normale. I tuoi dati restano invariati e la prossima proposta arriverà secondo i tempi consueti della piattaforma.</p>
<p>Il team di Ainima</p>"""


def _query_match_da_processare(cur):
    """Include sia i match ancora attivi con scadenza superata (caso
    normale) SIA quelli già passati a 'Scaduto' ma con notifica non ancora
    confermata inviata (recupero da un'esecuzione precedente interrotta a
    metà, es. tra l'UPDATE dello stato e l'invio email) — altrimenti un
    match già flippato a 'Scaduto' uscirebbe per sempre dal primo ramo del
    WHERE senza che l'email sia mai partita davvero."""
    cur.execute("""
        SELECT match_id, user_a_id, user_b_id, stato
        FROM matches
        WHERE notifica_scadenza_inviata = FALSE
          AND (
            (stato IN ('Proposto', 'Accettato_A', 'Accettato_B') AND data_scadenza_risposta < now())
            OR stato = 'Scaduto'
          )
    """)
    return cur.fetchall()


def scadi_match_e_notifica(conn) -> list[dict]:
    """Per ciascun match scaduto: porta lo stato a 'Scaduto' (idempotente
    se già lì), invia l'email neutra a entrambi (saltata se uno dei due
    profili è demo, v. RNF-12 — stesso filtro già in uso per pillole/
    domande), poi marca notifica_scadenza_inviata=TRUE SOLO se l'invio (o
    lo skip demo) è andato a buon fine — un fallimento lascia il match
    eleggibile per il tentativo successivo, isolato per riga (stesso
    pattern fail-open già in uso in engagement.py/engagement_scheduler.py)."""
    cur = conn.cursor()
    risultati = []

    for m in _query_match_da_processare(cur):
        match_id = str(m["match_id"])
        try:
            if m["stato"] != "Scaduto":
                cur.execute("UPDATE matches SET stato = 'Scaduto' WHERE match_id = %s", (match_id,))

            cur.execute(
                "SELECT user_id, nome, email, is_demo FROM users WHERE user_id IN (%s, %s)",
                (str(m["user_a_id"]), str(m["user_b_id"])),
            )
            utenti = cur.fetchall()

            if any(u["is_demo"] for u in utenti):
                cur.execute("UPDATE matches SET notifica_scadenza_inviata = TRUE WHERE match_id = %s", (match_id,))
                conn.commit()
                risultati.append({"match_id": match_id, "esito": "scaduto_demo_saltato"})
                continue

            # Nota su un edge case accettato: se l'invio al primo utente
            # riesce e quello al secondo fallisce, il rollback sotto
            # riporta il match a eleggibile per il tentativo successivo —
            # il primo utente potrebbe quindi ricevere l'email due volte
            # (una email neutra e innocua, non un'informazione sensibile).
            # Non risolto con una granularità per-destinatario: la stessa
            # scelta di semplicità già accettata altrove nel progetto per
            # rischi equivalenti a basso impatto.
            for u in utenti:
                email_provider.get_email_provider().invia_notifica(
                    u["email"], OGGETTO_TIMEOUT, CORPO_TIMEOUT.format(nome=u["nome"] or ""),
                )
            cur.execute("UPDATE matches SET notifica_scadenza_inviata = TRUE WHERE match_id = %s", (match_id,))
            conn.commit()
            risultati.append({"match_id": match_id, "esito": "scaduto_notificato"})
        except Exception as e:
            conn.rollback()
            risultati.append({"match_id": match_id, "esito": "errore", "dettaglio": str(e)})

    return risultati
