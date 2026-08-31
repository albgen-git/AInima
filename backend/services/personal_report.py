"""RF-28..RF-30b, §7.11/§7.12 — Report di analisi personale ("La tua
Prontezza Relazionale"). Modulo ISOLATO dal motore di scoring/matching
(RNF-11): legge solo psychometric_scores/profile_narrative/users (mai vi
scrive), scrive esclusivamente su personal_report/personal_report_feedback.
Nessun import da matching_engine.py e nessuna scrittura su tabelle di
scoring/preferenze/match — enforcement architetturale del vincolo RNF-11,
non solo di prompt (v. anche il commento in cima a services/llm_pipeline.py)."""

from uuid import UUID

from services import llm_pipeline
from services.email_provider import get_email_provider

# Stessi 4 campi usati da routers/auth.py per il gate di attivazione RF-09
# (bigfive_ok/attaccamento_ok/eq_ok/profilo_relazionale_ok) — qui replicati
# come SOLA condizione di lettura, non un secondo gate indipendente: se
# quella logica cambia, va aggiornata anche qui.
CAMPI_COMPLETAMENTO = [
    "score_big5_estroversione", "ansia_score",
    "eq_pilastro_autoconsapevolezza", "profilo_valori_self",
]


def quattro_test_completi(cur, user_id: UUID) -> bool:
    cur.execute(
        f"SELECT {', '.join(f'{c} IS NOT NULL AS {c}_ok' for c in CAMPI_COMPLETAMENTO)} "
        f"FROM psychometric_scores WHERE user_id = %s",
        (str(user_id),),
    )
    r = cur.fetchone()
    return bool(r) and all(r[f"{c}_ok"] for c in CAMPI_COMPLETAMENTO)


def _assembla_punteggi(cur, user_id: UUID) -> dict:
    """SOLA LETTURA — mai una scrittura su psychometric_scores da questo
    modulo. Solo i punteggi già aggregati (mai le risposte grezze agli
    item), mai i campi diagnostici/di qualità dato interni al sistema
    (flag_profilo_per_revisione_dati, confidenza_*, red flags) — quelli
    restano dato interno, mai passati a un LLM né mostrati all'utente."""
    cur.execute("""
        SELECT score_big5_estroversione, score_big5_gradevolezza, score_big5_coscienziosita,
               score_big5_nevroticismo, score_big5_apertura,
               ansia_score, evitamento_score, stile_attaccamento,
               eq_pilastro_autoconsapevolezza, eq_pilastro_autoregolazione,
               eq_pilastro_empatia, eq_pilastro_responsabilita, score_maturita_emotiva,
               profilo_valori_self, profilo_stile_vita_self,
               profilo_dinamica_relazionale_self, profilo_aspirazioni_self
        FROM psychometric_scores WHERE user_id = %s
    """, (str(user_id),))
    r = dict(cur.fetchone())
    return {
        "big_five": {
            "estroversione": r["score_big5_estroversione"], "gradevolezza": r["score_big5_gradevolezza"],
            "coscienziosita": r["score_big5_coscienziosita"], "nevroticismo": r["score_big5_nevroticismo"],
            "apertura": r["score_big5_apertura"],
        },
        "attaccamento": {
            "ansia": r["ansia_score"], "evitamento": r["evitamento_score"],
            "stile_prevalente": r["stile_attaccamento"],
        },
        "eq": {
            "autoconsapevolezza": r["eq_pilastro_autoconsapevolezza"],
            "autoregolazione": r["eq_pilastro_autoregolazione"],
            "empatia": r["eq_pilastro_empatia"], "responsabilita": r["eq_pilastro_responsabilita"],
            "maturita_emotiva_complessiva": r["score_maturita_emotiva"],
        },
        "profilo_relazionale": {
            "valori": r["profilo_valori_self"], "stile_vita": r["profilo_stile_vita_self"],
            "dinamica_relazionale": r["profilo_dinamica_relazionale_self"],
            "aspirazioni": r["profilo_aspirazioni_self"],
        },
    }


def _narrativa_utente(cur, user_id: UUID) -> str | None:
    cur.execute(
        "SELECT descrizione_di_se, descrizione_partner_ideale FROM profile_narrative WHERE user_id = %s",
        (str(user_id),),
    )
    narr = cur.fetchone()
    if not narr or not (narr["descrizione_di_se"] or narr["descrizione_partner_ideale"]):
        return None
    parti = []
    if narr["descrizione_di_se"]:
        parti.append(f"Descrizione di sé: {narr['descrizione_di_se']}")
    if narr["descrizione_partner_ideale"]:
        parti.append(f"Descrizione del partner ideale: {narr['descrizione_partner_ideale']}")
    return "\n".join(parti)


def genera_e_salva(conn, cur, user_id: UUID) -> str | None:
    """RF-28/30b: genera una nuova versione del report (copre sia il primo
    completamento sia una rigenerazione dopo l'aggiornamento di un test) e
    tenta l'invio email. Va chiamato DOPO che l'update dei punteggi
    psicometrici del chiamante è già committato, mai nella stessa
    transazione — un errore qui (LLM lento/non disponibile) non deve mai
    poter far fallire il salvataggio di un test psicometrico. Il chiamante
    deve comunque avvolgere questa funzione in un try/except (v.
    routers/psychometric.py): un fallimento di generazione qui non deve
    propagarsi come errore della submission del test.

    Ritorna il testo generato, o None se i 4 test non sono ancora tutti
    completi (nessuna riga scritta in quel caso)."""
    if not quattro_test_completi(cur, user_id):
        return None

    punteggi = _assembla_punteggi(cur, user_id)
    narrativa = _narrativa_utente(cur, user_id)
    testo = llm_pipeline.genera_report_prontezza_relazionale(punteggi, narrativa)

    cur.execute(
        "SELECT COALESCE(MAX(versione), 0) + 1 AS prossima FROM personal_report WHERE user_id = %s",
        (str(user_id),),
    )
    versione = cur.fetchone()["prossima"]
    cur.execute("""
        INSERT INTO personal_report (user_id, contenuto_report, versione)
        VALUES (%s, %s, %s) RETURNING report_id
    """, (str(user_id), testo, versione))
    report_id = cur.fetchone()["report_id"]
    conn.commit()

    _tenta_invio_email(conn, cur, user_id, report_id, testo)
    return testo


def _tenta_invio_email(conn, cur, user_id: UUID, report_id, testo: str):
    """RF-29 — best-effort, isolato dal salvataggio del report (già
    committato dal chiamante prima di questa funzione): un fallimento di
    invio non deve mai compromettere la disponibilità del report in app,
    stesso principio già applicato a invia_email_engagement_batch (v.
    CLAUDE.md — commit isolato per singolo invio, mai un batch tutto o
    niente)."""
    try:
        cur.execute("SELECT email FROM users WHERE user_id = %s", (str(user_id),))
        email = cur.fetchone()["email"]
        corpo_html = (
            "<p>Il tuo report \"La tua Prontezza Relazionale\" è pronto — lo trovi anche nella tua area personale.</p>"
            f"<div style=\"white-space:pre-wrap\">{testo}</div>"
        )
        get_email_provider().invia_notifica(email, "La tua Prontezza Relazionale è pronta", corpo_html)
        cur.execute(
            "UPDATE personal_report SET email_inviata = TRUE, data_invio_email = now() WHERE report_id = %s",
            (str(report_id),),
        )
        conn.commit()
    except Exception as e:
        print(f"[ERRORE] invio email report {report_id} (user {user_id}) fallito: {e}")
        conn.rollback()
