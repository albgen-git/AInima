"""RF-12, RNF-11 (chiarimento esplicito — v. CLAUDE.md e
Documento_Requisiti_v1.md, nota storica su RF-12): sintesi caratteriale
di coppia per la proposta di match ("Prompt 4" storico, reintrodotto dopo
il chiarimento sulla direzione del vincolo RNF-11 — genera testo A
PARTIRE da uno scoring già calcolato, non lo influenza).

Modulo ISOLATO dal motore di scoring (services/matching_engine.py, che
non lo importa e non ne sa nulla — il trigger avviene dal livello router,
mai da dentro il motore stesso, per mantenere quel modulo puramente
computazionale). Legge in SOLA LETTURA: psychometric_scores (via
matching_engine.load_pool, già pura/read-only), dealbreaker_criteria/
soft_criteria (indirettamente, tramite lo stesso load_pool), matches
(solo per leggere/scrivere la sua unica colonna di competenza). Scrive
ESCLUSIVAMENTE matches.analisi_caratteriale_coppia del match indicato —
mai final_score, mai stato, mai alcun campo di preferenze/criteri di
alcun utente. Nessuna altra funzione in questo file esegue un UPDATE/
INSERT/DELETE al di fuori di quell'unica colonna."""

from services import llm_pipeline, matching_engine


def _profilo_psicometrico(u: dict) -> dict:
    """Punteggi già aggregati di un lato della coppia (mai le risposte
    grezze agli item, mai flag/confidenze interne — stesso principio già
    applicato in services/personal_report.py).

    2026-09-02 (v. CLAUDE.md, audit richiesto dall'utente dopo aver trovato
    il report di coppia generico): prima mancavano lo stile di attaccamento
    prevalente e i 4 pilastri EQ singoli (solo la maturità aggregata era
    disponibile) — lo stesso identico livello di dettaglio già usato dal
    report personale (RF-28, services/personal_report.py._assembla_punteggi)
    ora è disponibile anche qui."""
    return {
        "big_five": {
            "estroversione": u["estroversione"], "gradevolezza": u["gradevolezza"],
            "coscienziosita": u["coscienziosita"], "nevroticismo": u["nevroticismo"],
            "apertura": u["apertura"],
        },
        "attaccamento": {
            "ansia": u["ansia"], "evitamento": u["evitamento"],
            "stile_prevalente": u["stile_attaccamento"],
        },
        "eq": {
            "autoconsapevolezza": u["eq_pilastro_autoconsapevolezza"],
            "autoregolazione": u["eq_pilastro_autoregolazione"],
            "empatia": u["eq_pilastro_empatia"],
            "responsabilita": u["eq_pilastro_responsabilita"],
            "maturita_emotiva_complessiva": u["maturita"],
        },
    }


def _assembla_punteggi_coppia(pool: dict, id_a: str, id_b: str, cfg: dict) -> dict:
    """SOLA LETTURA sul pool già caricato in memoria da
    matching_engine.load_pool() (a sua volta una query read-only) — non
    esegue alcuna query di scrittura. Riusa le stesse funzioni pure già
    validate dal motore di scoring (bigfive_score/eq_score/
    punteggio_narrativo_strutturato/combina_soft_e_distanza/valuta_distanza),
    senza duplicarne la logica: lo stesso identico calcolo che ha prodotto
    il final_score già persistito su questo match.

    2026-09-02 (v. CLAUDE.md, audit): prima l'input si fermava a 3 numeri
    aggregati di coppia + 8 scalari a testa — troppo poco perché il Prompt 6
    potesse scrivere qualcosa di specifico, non un limite del prompt in sé.
    Ora include anche il DETTAGLIO per sotto-dimensione del Test Profilo
    Relazionale (13 righe categoria+punteggio, non solo la media) e le
    sovrapposizioni POSITIVE delle liste mi_piace/partner_vorrei (interessi
    condivisi citabili per nome, v. Ainima_Prompt_Report_Abbinamento_v1.md
    §"Regola vincolante: minimo di citazioni concrete"). Deliberatamente
    NON i valori grezzi self/partner_ideale per sotto-dimensione (il
    documento li elenca come input, ma il punteggio di COMPATIBILITÀ per
    sotto-dimensione già calcolato da punteggio_narrativo_strutturato() è
    più coerente con RNF-11 — è il dato già interpretato, non grezzo, e
    lascia all'LLM zero margine per fare da sé un confronto che il motore
    di scoring ha già fatto). MAI alcun dato riconducibile a
    flag_rifiuto_esplicito: combina_soft_e_distanza/punteggio_tag_liste
    costruiscono il dettaglio positivo senza mai leggere le liste di
    rifiuto (v. matching_engine.py, garanzia strutturale non solo di
    prompt)."""
    a, b = pool[id_a], pool[id_b]
    dist = matching_engine.haversine_km(a["lon"], a["lat"], b["lon"], b["lat"])
    _, punteggio_distanza = matching_engine.valuta_distanza(a, b, dist, cfg)
    bf = matching_engine.bigfive_score(a, b)
    eq = matching_engine.eq_score(a, b)
    narrativa, _, dettaglio_narrativo = matching_engine.punteggio_narrativo_strutturato(a, b)
    soft, _, interessi_condivisi = matching_engine.combina_soft_e_distanza(a, b, punteggio_distanza)
    final = (cfg["weight_bigfive"] * bf + cfg["weight_eq_attaccamento"] * eq +
             cfg["weight_narrativa"] * narrativa + cfg["weight_preferenze_soft"] * soft)

    return {
        "punteggio_compatibilita_finale": final,
        "corrispondenza_criteri_graditi": soft,
        "coerenza_valori_e_aspirazioni": narrativa,
        "dettaglio_sottodimensioni_profilo_relazionale": dettaglio_narrativo,
        "interessi_condivisi_citabili": interessi_condivisi,
        "persona_1": _profilo_psicometrico(a),
        "persona_2": _profilo_psicometrico(b),
    }


def genera_e_salva(conn, cur, match_id: str, id_a: str, id_b: str) -> str | None:
    """RF-12: genera la sintesi UNA SOLA volta per match (mai una per
    utente — v. Documento_Requisiti_v1.md). Se già presente, ritorna il
    valore salvato senza rigenerare né chiamare l'LLM di nuovo. Ritorna
    None se il match non esiste o se uno dei due profili non è (più) nel
    pool di matching attivo (caso limite, non dovrebbe succedere per un
    match già creato).

    Va chiamato DOPO che il match è già stato committato — un fallimento
    qui (LLM lento/non disponibile) non deve mai bloccare la creazione o
    la visualizzazione della proposta. Il chiamante (routers/matching.py)
    è responsabile del try/except, stesso principio già applicato al
    report personale RF-28 in services/personal_report.py."""
    cur.execute("SELECT analisi_caratteriale_coppia FROM matches WHERE match_id = %s", (str(match_id),))
    riga = cur.fetchone()
    if riga is None:
        return None
    if riga["analisi_caratteriale_coppia"] is not None:
        return riga["analisi_caratteriale_coppia"]

    pool = matching_engine.load_pool(cur)
    if id_a not in pool or id_b not in pool:
        return None
    cfg = matching_engine.load_config_floats(cur)
    punteggi = _assembla_punteggi_coppia(pool, id_a, id_b, cfg)
    testo = llm_pipeline.genera_analisi_caratteriale_coppia(punteggi)

    cur.execute(
        "UPDATE matches SET analisi_caratteriale_coppia = %s WHERE match_id = %s AND analisi_caratteriale_coppia IS NULL",
        (testo, str(match_id)),
    )
    conn.commit()
    return testo
