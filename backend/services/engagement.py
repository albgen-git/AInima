"""Blocco E (v. CLAUDE.md — Ainima_Dashboard_Trigger_Email_v1.md,
Ainima_Engagement_Periodico_v1_BOZZA.md §2-3): domande di affinamento +
pillole di saggezza, coda/raggruppamento email anti-invadenza.

Implementata solo la fonte "item di riserva" (§2.1) per le domande di
affinamento — la seconda fonte del documento ("re-somministrazione
mirata" quando confidenza_dimensione è bassa) NON è ancora costruita,
resta un'estensione futura esplicitamente segnalata, non inventata qui.

Nessuno scheduler reale (stesso limite già accettato altrove nel
progetto, v. run_monthly_batch): invia_email_engagement_batch() va
invocata manualmente/da cron esterno, idealmente nel giorno configurato
in system_config.giorno_invio_email_engagement — la funzione stessa non
impone il giorno, solo il tetto di frequenza per utente (§2.3)."""

import json
import os

from services import email_provider

# Numero di item per dimensione nei test ATTUALI (post-taglio, v. CLAUDE.md
# Blocchi A/B) — base per la media incrementale quando una risposta di
# affinamento aggiorna uno score esistente (§2.2: "aggiorna, non
# sostituisce"). Le risposte grezze originali non sono persistite (stesso
# vincolo già noto per confidenza_dimensione), quindi la media viene
# ricostruita assumendo che lo score attuale rappresenti esattamente
# questo numero di risposte — approssimazione dichiarata, non un dato
# esatto.
N_ITEM_PER_DIMENSIONE = {"bigfive": 8, "attaccamento": 9, "eq": 6}

COLONNA_SCORE = {
    ("bigfive", "estroversione"): "score_big5_estroversione",
    ("bigfive", "gradevolezza"): "score_big5_gradevolezza",
    ("bigfive", "coscienziosita"): "score_big5_coscienziosita",
    ("bigfive", "nevroticismo"): "score_big5_nevroticismo",
    ("bigfive", "apertura"): "score_big5_apertura",
    ("attaccamento", "ansia_abbandono"): "ansia_score",
    ("attaccamento", "evitamento"): "evitamento_score",
    ("eq", "autoconsapevolezza"): "eq_pilastro_autoconsapevolezza",
    ("eq", "autoregolazione"): "eq_pilastro_autoregolazione",
    ("eq", "empatia"): "eq_pilastro_empatia",
    ("eq", "responsabilita"): "eq_pilastro_responsabilita",
}


def assegna_domande_affinamento(cur, user_id, n=2):
    """T1 (Ainima_Dashboard_Trigger_Email_v1.md §2.1) — pesca n item dal
    pool non ancora mai proposti a QUESTO utente (domande_affinamento_log,
    PK (user_id, item_id) impedisce le ripetizioni), li registra come
    "posti" e li mette in coda email. Ritorna la lista degli item
    assegnati (dict con item_id/testo_it/testo_en), vuota se il pool per
    questo utente è esaurito."""
    cur.execute("""
        SELECT item_id, testo_it, testo_en FROM domande_affinamento_pool
        WHERE attivo AND item_id NOT IN (
            SELECT item_id FROM domande_affinamento_log WHERE user_id = %s
        )
        ORDER BY random()
        LIMIT %s
    """, (str(user_id), n))
    item = cur.fetchall()
    if not item:
        return []

    for i in item:
        cur.execute("INSERT INTO domande_affinamento_log (user_id, item_id) VALUES (%s, %s)",
                     (str(user_id), str(i["item_id"])))
        aggiungi_a_coda_email(cur, user_id, "domande", i["item_id"])
    return item


def registra_risposta_affinamento(cur, user_id, item_id, risposta: int):
    """Registra la risposta (1-5) e aggiorna — non sostituisce — lo score
    esistente della dimensione coinvolta (§2.2), con la stessa
    ricodifica reverse già usata ovunque nel progetto. Solleva
    ValueError se l'item non è mai stato assegnato a questo utente o ha
    già una risposta."""
    cur.execute("""
        SELECT dl.risposta, dp.test_origine, dp.dimensione, dp.reverse
        FROM domande_affinamento_log dl
        JOIN domande_affinamento_pool dp ON dp.item_id = dl.item_id
        WHERE dl.user_id = %s AND dl.item_id = %s
    """, (str(user_id), str(item_id)))
    riga = cur.fetchone()
    if riga is None:
        raise ValueError("Item non assegnato a questo utente")
    if riga["risposta"] is not None:
        raise ValueError("Item già risposto")

    cur.execute("""
        UPDATE domande_affinamento_log SET risposta = %s, data_risposta = now()
        WHERE user_id = %s AND item_id = %s
    """, (risposta, str(user_id), str(item_id)))

    test_origine, dimensione = riga["test_origine"], riga["dimensione"]
    colonna = COLONNA_SCORE.get((test_origine, dimensione))
    if colonna is None:
        return  # dimensione senza colonna score diretta mappata — nessun aggiornamento

    ricodificato = 6 - risposta if riga["reverse"] else risposta
    nuovo_normalizzato = (ricodificato - 1) / 4  # stessa formula (grezzo-1)/4 usata ovunque

    cur.execute(f"SELECT {colonna} AS v FROM psychometric_scores WHERE user_id = %s", (str(user_id),))
    r = cur.fetchone()
    if r is None or r["v"] is None:
        return  # utente non ha ancora fatto il test di origine — nessuna media da aggiornare

    n = N_ITEM_PER_DIMENSIONE[test_origine]
    media_aggiornata = (r["v"] * n + nuovo_normalizzato) / (n + 1)
    cur.execute(f"UPDATE psychometric_scores SET {colonna} = %s WHERE user_id = %s",
                (media_aggiornata, str(user_id)))

    if test_origine in ("bigfive", "eq"):
        # ri-derivano score_maturita_emotiva/confidenza incrociata con
        # l'input ora aggiornato — v. routers/psychometric.py, stessa
        # funzione usata dai 3 endpoint di submission.
        from routers.psychometric import _ricalcola_confidenza_e_flag
        _ricalcola_confidenza_e_flag(cur, user_id)


def assegna_pillola(cur, user_id, contesto_trigger="Attesa generale"):
    """T2 (§3.2) — tag-matching puro, zero LLM nel percorso critico:
    sceglie la prima pillola attiva del contesto richiesto il cui tag di
    personalizzazione combacia con un segnale noto dell'utente
    (ansia_score/evitamento_score alti, eq_pilastro_empatia basso); in
    assenza di segnali specifici, sceglie contenuto generico del
    pilastro in rotazione (tag_personalizzazione vuoto). Mai riproposta
    due volte (pillole_inviate_log, PK (user_id, pillola_id))."""
    cur.execute("SELECT ansia_score, evitamento_score, eq_pilastro_empatia FROM psychometric_scores WHERE user_id = %s",
                (str(user_id),))
    r = cur.fetchone() or {}
    tag_utente = []
    if (r.get("ansia_score") or 0) > 0.7:
        tag_utente.append("ansia_alta")
    if (r.get("evitamento_score") or 0) > 0.7:
        tag_utente.append("evitamento_alto")
    if r.get("eq_pilastro_empatia") is not None and r["eq_pilastro_empatia"] < 0.3:
        tag_utente.append("empatia_bassa")

    cur.execute("""
        SELECT pillola_id, titolo FROM pillole_libreria
        WHERE attiva AND contesto_trigger = %s
          AND pillola_id NOT IN (SELECT pillola_id FROM pillole_inviate_log WHERE user_id = %s)
        ORDER BY (tag_personalizzazione && %s::varchar[]) DESC, random()
        LIMIT 1
    """, (contesto_trigger, str(user_id), tag_utente))
    pillola = cur.fetchone()
    if not pillola:
        return None

    cur.execute("INSERT INTO pillole_inviate_log (user_id, pillola_id) VALUES (%s, %s)",
                 (str(user_id), str(pillola["pillola_id"])))
    aggiungi_a_coda_email(cur, user_id, "pillola", pillola["pillola_id"])
    return pillola


def aggiungi_a_coda_email(cur, user_id, tipo_contenuto, contenuto_id):
    """§2.2: aggiunge alla coda — lo svuotamento vero avviene solo in
    invia_email_engagement_batch(), mai qui (nessun invio immediato)."""
    cur.execute("""
        INSERT INTO email_coda_prossimo_invio (user_id, tipo_contenuto, contenuto_id)
        VALUES (%s, %s, %s)
    """, (str(user_id), tipo_contenuto, str(contenuto_id)))


def stato_dashboard_engagement(cur, user_id):
    """Stati §1 (esclusa "Proposta di abbinamento attiva", già gestita da
    GET /auth/{id}/dashboard — priorità 1, non duplicata qui)."""
    cur.execute("""
        SELECT dp.testo_it FROM domande_affinamento_log dl
        JOIN domande_affinamento_pool dp ON dp.item_id = dl.item_id
        WHERE dl.user_id = %s AND dl.risposta IS NULL
        ORDER BY dl.data_posta
    """, (str(user_id),))
    domande_pendenti = [r["testo_it"] for r in cur.fetchall()]

    cur.execute("""
        SELECT pl.pillola_id, pl.titolo, pl.testo FROM pillole_inviate_log pil
        JOIN pillole_libreria pl ON pl.pillola_id = pil.pillola_id
        WHERE pil.user_id = %s AND pil.aperta = FALSE
        ORDER BY pil.data_invio DESC LIMIT 1
    """, (str(user_id),))
    pillola_pendente = cur.fetchone()

    return {
        "domande_pendenti": domande_pendenti,
        "pillola_pendente": dict(pillola_pendente) if pillola_pendente else None,
    }


def _oggetto_email(ha_domande: bool, ha_pillola: bool, titolo_pillola: str | None) -> str:
    """§3 — l'oggetto varia in base al contenuto, mai un elenco puntato nel corpo."""
    if ha_domande and ha_pillola:
        return "Novità sul tuo profilo Ainima"
    if ha_domande:
        return "2 minuti per affinare il tuo profilo Ainima"
    return f"La tua pillola di questa settimana: {titolo_pillola}"


def invia_email_engagement_batch(conn, dry_run=True):
    """Svuota email_coda_prossimo_invio raggruppando per utente (§2.2) —
    UNA sola email per utente con tutto ciò che è in coda, rispettando il
    tetto di frequenza (§2.3, system_config.cadenza_email_engagement_giorni).
    Non invia mai più di un'email per utente per invocazione. Va invocata
    dal giorno fisso configurato (nessuno scheduler reale, v. CLAUDE.md)."""
    cur = conn.cursor()
    cur.execute("SELECT valore FROM system_config WHERE chiave = 'cadenza_email_engagement_giorni'")
    cadenza_giorni = int(cur.fetchone()["valore"])

    cur.execute("""
        SELECT ec.coda_id, ec.user_id, ec.tipo_contenuto, ec.contenuto_id, u.email
        FROM email_coda_prossimo_invio ec
        JOIN users u ON u.user_id = ec.user_id
        ORDER BY ec.user_id
    """)
    righe = cur.fetchall()

    per_utente = {}
    for r in righe:
        blocco = per_utente.setdefault(str(r["user_id"]), {"email": r["email"], "voci": []})
        blocco["voci"].append(r)

    risultati = []
    for user_id, blocco in per_utente.items():
        cur.execute("""
            SELECT data_invio FROM email_inviata_log WHERE user_id = %s
            ORDER BY data_invio DESC LIMIT 1
        """, (user_id,))
        ultima = cur.fetchone()
        if ultima is not None:
            cur.execute("SELECT now() - %s < (%s || ' days')::interval AS troppo_presto",
                        (ultima["data_invio"], cadenza_giorni))
            if cur.fetchone()["troppo_presto"]:
                risultati.append({"user_id": user_id, "esito": "rimandato_tetto_frequenza"})
                continue

        voci = blocco["voci"]
        ha_domande = any(v["tipo_contenuto"] == "domande" for v in voci)
        pillole_voci = [v for v in voci if v["tipo_contenuto"] == "pillola"]
        titolo_pillola = None
        if pillole_voci:
            cur.execute("SELECT titolo FROM pillole_libreria WHERE pillola_id = %s", (str(pillole_voci[0]["contenuto_id"]),))
            row = cur.fetchone()
            titolo_pillola = row["titolo"] if row else None

        oggetto = _oggetto_email(ha_domande, bool(pillole_voci), titolo_pillola)
        # "ainima.local" era un placeholder mai sostituito con il dominio
        # reale (trovato testando dal vivo un invio reale, v. CLAUDE.md) —
        # FRONTEND_BASE_URL configurabile per un eventuale dominio custom
        # futuro, con il default già puntato al frontend Netlify attuale.
        frontend_url = os.environ.get("FRONTEND_BASE_URL", "https://ainima.netlify.app")
        corpo_html = (
            f"<p>Ciao,</p><p>c'è qualcosa di nuovo per te su Ainima — "
            f"{'alcune domande per affinare il tuo profilo' if ha_domande else ''}"
            f"{' e ' if ha_domande and pillole_voci else ''}"
            f"{'una pillola pensata per te' if pillole_voci else ''}.</p>"
            f"<p><a href=\"{frontend_url}/it/dashboard\">Vai alla tua dashboard</a></p>"
        )

        if not dry_run:
            # Commit per-utente, non una volta sola a fine batch: invia_notifica()
            # è una vera chiamata esterna, non transazionale — se l'invio per
            # l'utente N fallisce, un unico commit finale avrebbe fatto rollback
            # anche degli invii già riusciti per 1..N-1, che nel frattempo sono
            # realmente partiti. Risultato senza questo isolamento: quegli utenti
            # sarebbero rimasti con la coda intatta e nessuna riga in
            # email_inviata_log, quindi il prossimo giro li avrebbe scritti di
            # nuovo — email duplicate a utenti reali. Ogni utente è quindi un
            # tentativo isolato: un fallimento non tocca gli altri.
            try:
                email_provider.get_email_provider().invia_notifica(blocco["email"], oggetto, corpo_html)
                contenuti = [{"tipo": v["tipo_contenuto"], "id": str(v["contenuto_id"])} for v in voci]
                cur.execute("""
                    INSERT INTO email_inviata_log (user_id, contenuti_inclusi) VALUES (%s, %s::jsonb)
                """, (user_id, json.dumps(contenuti)))
                cur.execute("DELETE FROM email_coda_prossimo_invio WHERE user_id = %s", (user_id,))
                conn.commit()
            except Exception as e:
                conn.rollback()
                risultati.append({"user_id": user_id, "esito": "fallita", "errore": str(e)})
                continue

        risultati.append({"user_id": user_id, "esito": "inviata" if not dry_run else "simulata",
                           "oggetto": oggetto, "n_voci": len(voci)})

    return risultati
