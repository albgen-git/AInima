"""
Motore di matching — versione di servizio della logica già validata in
scripts/simulate_matching.py.

Differenza rispetto allo script CLI: qui le funzioni ritornano dati
strutturati (non stampano) e run_monthly_batch() scrive davvero le
proposte nella tabella matches, invece di limitarsi a simularle.

Aggiornamento 2026-08-19 (stable_v3, v. CLAUDE.md — sessione con lo
psicologo del progetto): (a) attaccamento da formula continua ansia/
evitamento (Ainima_Test_Attaccamento_v1.md) al posto della matrice 4x4 su
etichette dedotte da LLM; (b) Coerenza Narrativa da similarità vettoriale
pura tra self/ideal embedding (Ainima_Matching_Semantico_Report_v1.md §5),
Judge LLM Prompt 4 eliminato — RNF-11, nessuna IA generativa nel calcolo
dei punteggi; (c) filtro hard su flag_profilo_per_revisione_dati al posto
di red_flags_rilevati; (d) selezione per somiglianza visiva (RF-11a/RF-11b)
sempre applicata sulla shortlist di N candidati per compatibilità
caratteriale, non più solo come tie-break tra quasi pari.

Aggiornamento 2026-08-20 (stable_v4, v. Ainima_Liste_Piace_Detesta_v1.md):
Punteggio_Tag_Liste dentro lo STEP 4 — confronto a similarità vettoriale
per singolo tag (non per profilo intero, a differenza della Coerenza
Narrativa) tra le liste mi_piace/non_sopporto/partner_vorrei/
partner_non_vorrei, con penalità dedicata sui rifiuti espliciti.

Aggiornamento 2026-08-20 (stable_v5, v. CLAUDE.md — test di matching reale
Pietro/Lena Gallo): la soglia minima del tie-break visivo RF-11a/RF-11b non
è più un valore assoluto hardcoded (0.20) — verificato che il 90° percentile
delle similarità ArcFace tra coppie CASUALI del pool era già 0.334, quindi
0.20 lasciava scattare il tie-break su rumore statistico più di una volta
su tre. Ora è un valore ricalcolato su un percentile configurabile della
distribuzione reale (`soglia_similarita_visiva_minima`/
`soglia_percentile_similarita_visiva` in system_config).

Aggiornamento 2026-08-21 (stable_v8, v. CLAUDE.md — Blocco D,
Ainima_Test_Profilo_Relazionale_v1.md): la Coerenza Narrativa (STEP 3) non
usa più il confronto a embedding tra i campi liberi — sostituita da
punteggio_narrativo_strutturato(), aritmetica diretta su 13 sotto-dimensioni
chiuse (26 item, self vs partner ideale). coerenza_narrativa_score()
rimossa, non solo rinominata (self_embedding_vector/ideal_embedding_vector
restano calcolati per altri usi, ma load_pool() non li carica più per il
matching). flag_asimmetria_narrativa ora persistito su matches, stesso
trattamento di flag_rifiuto_esplicito (v. routers/matching.py, routers/admin.py).
"""

import json
import math
from datetime import datetime, timedelta

import numpy as np

from services import tag_matching

# v. tabella matching_algorithm_versions in db/schema.sql per la descrizione
# estesa — da aggiornare (nuova riga in quella tabella + bump qui) ogni
# volta che cambia la LOGICA dell'algoritmo, non i soli parametri (quelli
# sono già tracciati automaticamente via system_config, v. run_monthly_batch).
ALGORITMO_VERSIONE = "stable_v8"

# Sopra questa penalità sui rifiuti espliciti, il flag va esposto invece
# di restare nascosto dentro la media (Ainima_Liste_Piace_Detesta_v1.md §5).
SOGLIA_RIFIUTO_ESPLICITO = 0.7


def cosine(v1, v2):
    v1, v2 = np.array(v1), np.array(v2)
    denom = np.linalg.norm(v1) * np.linalg.norm(v2)
    if denom == 0:
        return 0.0
    return float(np.dot(v1, v2) / denom)


def haversine_km(lon1, lat1, lon2, lat2):
    """None (non un crash) se manca una coordinata su uno dei due lati —
    bug reale trovato dal vivo (v. CLAUDE.md): un utente reale senza
    coordinate (comune_residenza mai geocodificato — v. nota su
    routers/profile.py) mandava in crash l'intero motore di matching, sia
    per il trigger singolo sia per il ciclo mensile, non solo per quel
    profilo. Il chiamante (valuta_distanza) tratta None come 'filtro
    distanza non superato', coerente con lo stile hard-filter esistente."""
    if None in (lon1, lat1, lon2, lat2):
        return None
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def bigfive_score(a, b):
    """STEP 2 (Big Five). Ogni riga è pesata dalla confidenza minima tra i
    due profili sulla dimensione da cui deriva (Blocco C, v. CLAUDE.md —
    Ainima_Test_Psicometrico_BigFive_v1.md §7 Step 4): un profilo con
    varianza interna anomala su una dimensione pesa meno quella riga nella
    media finale, invece di contare quanto un dato affidabile. La riga
    "assertivita" deriva dalla stessa dimensione Estroversione della riga
    omonima, quindi condivide la sua confidenza."""
    nevro_diff = 1 - abs(a["nevroticismo"] - b["nevroticismo"])
    nevro_bonus = 0.1 if (a["nevroticismo"] + b["nevroticismo"]) / 2 < 0.3 else 0.0
    nevro = min(1.0, nevro_diff + nevro_bonus)
    coscienziosita = 1 - abs(a["coscienziosita"] - b["coscienziosita"])
    apertura = 1 - abs(a["apertura"] - b["apertura"])
    diff_e = abs(a["estroversione"] - b["estroversione"])
    assertivita = max(0.0, 1 - abs(diff_e - 0.3) / 0.7)
    estroversione = 1 - abs(a["estroversione"] - b["estroversione"]) * 0.5
    gradevolezza = (a["gradevolezza"] + b["gradevolezza"]) / 2

    conf_estroversione = min(a["conf_estroversione"], b["conf_estroversione"])
    righe_pesate = [
        (nevro, min(a["conf_nevroticismo"], b["conf_nevroticismo"])),
        (coscienziosita, min(a["conf_coscienziosita"], b["conf_coscienziosita"])),
        (assertivita, conf_estroversione),
        (estroversione, conf_estroversione),
        (gradevolezza, min(a["conf_gradevolezza"], b["conf_gradevolezza"])),
        (apertura, min(a["conf_apertura"], b["conf_apertura"])),
    ]
    peso_totale = sum(peso for _, peso in righe_pesate)
    return sum(valore * peso for valore, peso in righe_pesate) / peso_totale


def eq_score(a, b):
    """STEP 2 (Ainima_Algoritmo_Ranking_Finale_v1.md §4): maturità emotiva
    (soglia, non lineare — un piccolo divario è normale/positivo, oltre
    0.35 la penalità cresce più che proporzionalmente) + attaccamento a
    formula continua (§4b) su ansia/evitamento, con penalità mirata sul
    pattern "inseguimento-fuga" (uno ansioso, l'altro evitante) — sostituisce
    la matrice 4x4 su etichette dedotte da LLM."""
    media = (a["maturita"] + b["maturita"]) / 2
    sbil = abs(a["maturita"] - b["maturita"])
    penalita = (sbil - 0.35) * 1.5 if sbil > 0.35 else 0.0
    punteggio_maturita = min(1.0, max(0.0, media - penalita))

    media_ansia = (a["ansia"] + b["ansia"]) / 2
    media_evitamento = (a["evitamento"] + b["evitamento"]) / 2
    penalita_incrocio = max(a["ansia"] * b["evitamento"], b["ansia"] * a["evitamento"])
    attaccamento_score = 1 - (media_ansia * 0.3) - (media_evitamento * 0.3) - (penalita_incrocio * 0.4)
    attaccamento_score = min(1.0, max(0.0, attaccamento_score))

    return punteggio_maturita * 0.6 + attaccamento_score * 0.4


# Nome-categoria -> chiavi delle sotto-dimensioni, stesso ordine del
# documento (Ainima_Test_Profilo_Relazionale_v1.md §2-5). Duplicato qui
# (non importato da schemas.psychometric) perché matching_engine.py non
# dipende da nessun modulo di schemas/routers — v. principio già seguito
# per le altre funzioni di scoring, che leggono solo dai dict del pool.
SOTTODIMENSIONI_PROFILO_RELAZIONALE = {
    "valori": ["centralita_famiglia", "orientamento_carriera", "bisogno_stabilita", "crescita_personale"],
    "stile_vita": ["socialita", "organizzazione", "ritmo_vita"],
    "dinamica_relazionale": ["autonomia_fusione", "condivisione_ruoli", "espressivita_emotiva"],
    "aspirazioni": ["impegno_lungo_termine", "mobilita_geografica", "orizzonte_progettuale"],
}


def punteggio_narrativo_strutturato(a, b):
    """STEP 3 (Ainima_Test_Profilo_Relazionale_v1.md §6, Blocco D — v.
    CLAUDE.md): sostituisce coerenza_narrativa_score() (similarità a
    embedding, rimossa) — aritmetica diretta su 13 sotto-dimensioni chiuse
    (26 item, self vs partner ideale), bidirezionale come la vecchia
    versione ma per sotto-dimensione invece che sull'intero profilo.

    Ritorna (punteggio, flag_asimmetria_narrativa): il flag scatta se ANCHE
    UNA SOLA sotto-dimensione ha uno scarto > 0.5 tra le due direzioni —
    un'asimmetria forte e localizzata non va mediata via silenziosamente
    (stesso principio già applicato a flag_rifiuto_esplicito).

    Ritorna (0.5, False) — neutro, non un segnale di incompatibilità — se
    manca anche un solo profilo_*_self/partner_ideale per uno dei due lati
    (dato non ancora disponibile, stesso trattamento della vecchia versione
    per l'embedding mancante)."""
    campi = [f"profilo_{cat}_self" for cat in SOTTODIMENSIONI_PROFILO_RELAZIONALE] + \
            [f"profilo_{cat}_partner_ideale" for cat in SOTTODIMENSIONI_PROFILO_RELAZIONALE]
    if any(a[campo] is None or b[campo] is None for campo in campi):
        return 0.5, False

    flag_asimmetria = False
    punteggi_categoria = []
    for categoria, sottodim in SOTTODIMENSIONI_PROFILO_RELAZIONALE.items():
        a_self, a_ideale = a[f"profilo_{categoria}_self"], a[f"profilo_{categoria}_partner_ideale"]
        b_self, b_ideale = b[f"profilo_{categoria}_self"], b[f"profilo_{categoria}_partner_ideale"]
        compatibilita_sottodim = []
        for d in sottodim:
            coerenza_a_verso_b = 1 - abs(a_self[d] - b_ideale[d])
            coerenza_b_verso_a = 1 - abs(b_self[d] - a_ideale[d])
            compatibilita_sottodim.append((coerenza_a_verso_b + coerenza_b_verso_a) / 2)
            if abs(coerenza_a_verso_b - coerenza_b_verso_a) > 0.5:
                flag_asimmetria = True
        punteggi_categoria.append(sum(compatibilita_sottodim) / len(compatibilita_sottodim))

    punteggio = sum(punteggi_categoria) / len(punteggi_categoria)
    return punteggio, flag_asimmetria


def tag_overlap_score(source_embs, target_embs):
    """Ainima_Liste_Piace_Detesta_v1.md §3 — confronto DIREZIONALE: per
    ogni tag della lista source, prende il miglior match nella lista
    target, poi fa la media. A differenza della Coerenza Narrativa
    (un embedding per l'intero profilo), qui ogni tag ha il proprio
    embedding — un solo tag molto simile può bastare a far salire il
    punteggio anche se gli altri non si assomigliano.

    None se la lista source è vuota (dato mancante, da escludere dalla
    media — non un disallineamento); 0.0 se la lista target è vuota
    (nessuna corrispondenza possibile, quello è un vero segnale)."""
    if not source_embs:
        return None
    if not target_embs:
        return 0.0
    migliori = [max(cosine(emb_s, emb_t) for emb_t in target_embs) for emb_s in source_embs]
    return sum(migliori) / len(migliori)


def punteggio_tag_liste(a, b):
    """Ainima_Liste_Piace_Detesta_v1.md §4-5. Le 3 componenti:
    - Interessi_Comuni: quanto A.mi_piace e B.mi_piace si assomigliano
      (bonus, simmetrico).
    - Corrispondenza_Desideri: quanto ciò che A cerca esplicitamente
      (partner_vorrei) compare in ciò che B è/ama (mi_piace), e viceversa.
    - Penalita_Rifiuti: quanto un rifiuto esplicito di uno (non_sopporto
      + partner_non_vorrei, unione) compare in ciò che l'altro è/ama —
      pesa più di una semplice assenza di affinità, per questo è una
      sottrazione separata, non solo un punteggio basso su desideri.

    Una componente None (entrambe le liste coinvolte vuote da quel lato)
    viene esclusa dalla media pesata invece di contare come 0 — un campo
    non compilato è un dato mancante, non un disallineamento.

    Ritorna (punteggio: float|None, flag_rifiuto_esplicito: bool)."""
    def _media_bidirezionale(fwd, bwd):
        valori = [v for v in (fwd, bwd) if v is not None]
        return sum(valori) / len(valori) if valori else None

    interessi_comuni = _media_bidirezionale(
        tag_overlap_score(a["mi_piace_emb"], b["mi_piace_emb"]),
        tag_overlap_score(b["mi_piace_emb"], a["mi_piace_emb"]),
    )
    corrispondenza_desideri = _media_bidirezionale(
        tag_overlap_score(a["partner_vorrei_emb"], b["mi_piace_emb"]),
        tag_overlap_score(b["partner_vorrei_emb"], a["mi_piace_emb"]),
    )
    rifiuti_a = a["partner_non_vorrei_emb"] + a["non_sopporto_emb"]
    rifiuti_b = b["partner_non_vorrei_emb"] + b["non_sopporto_emb"]
    penalita_rifiuti = _media_bidirezionale(
        tag_overlap_score(rifiuti_a, b["mi_piace_emb"]),
        tag_overlap_score(rifiuti_b, a["mi_piace_emb"]),
    )

    pesate = []
    if corrispondenza_desideri is not None:
        pesate.append((corrispondenza_desideri, 0.6))
    if interessi_comuni is not None:
        pesate.append((interessi_comuni, 0.4))
    if not pesate:
        return None, False

    punteggio = sum(v * w for v, w in pesate) / sum(w for _, w in pesate)
    if penalita_rifiuti is not None:
        punteggio -= penalita_rifiuti
    punteggio = min(1.0, max(0.0, punteggio))

    flag_rifiuto_esplicito = penalita_rifiuti is not None and penalita_rifiuti > SOGLIA_RIFIUTO_ESPLICITO
    return punteggio, flag_rifiuto_esplicito


def soft_score(a, b):
    componenti = []
    if a["pref_altezza_min"] is not None and a["pref_altezza_max"] is not None and b["altezza_cm"] is not None:
        if a["pref_altezza_min"] <= b["altezza_cm"] <= a["pref_altezza_max"]:
            componenti.append(1.0)
        else:
            fuori = min(abs(b["altezza_cm"] - a["pref_altezza_min"]), abs(b["altezza_cm"] - a["pref_altezza_max"]))
            componenti.append(max(0.0, 1 - fuori / 20))
    if a["pref_fumo"] is not None and b["fumo"] is not None:
        componenti.append(1.0 if a["pref_fumo"] == b["fumo"] else 0.3)
    if a["pref_alcol"] is not None and b["alcol"] is not None:
        componenti.append(1.0 if a["pref_alcol"] == b["alcol"] else 0.5)
    if a["pref_importanza_religione"] is not None and b["importanza_religione"] is not None:
        componenti.append(1 - abs(a["pref_importanza_religione"] - b["importanza_religione"]) / 4)
    if not componenti:
        return 0.5
    return sum(componenti) / len(componenti)


def combina_soft_e_distanza(seeker, cand, punteggio_distanza):
    """STEP 4 (Algoritmo_Ranking_Finale §6): Punteggio_Preferenze_Soft è la
    media ponderata tra le preferenze reciproche dichiarate (già bidirezionali,
    v. CLAUDE.md sulla scelta di renderle simmetriche), Punteggio_Distanza
    calcolato al punto 3bis, e Punteggio_Tag_Liste (Ainima_Liste_Piace_
    Detesta_v1.md §6, stable_v4) — ciascuno escluso dalla media se non
    disponibile (dato mancante), mai trattato come 0.

    Ritorna (punteggio: float, flag_rifiuto_esplicito: bool) — il flag va
    esposto nel report/admin, non lasciato nascosto dentro la media."""
    preferenze = (soft_score(seeker, cand) + soft_score(cand, seeker)) / 2
    punteggio_tag, flag_rifiuto_esplicito = punteggio_tag_liste(seeker, cand)

    componenti = [preferenze]
    if punteggio_distanza is not None:
        componenti.append(punteggio_distanza)
    if punteggio_tag is not None:
        componenti.append(punteggio_tag)

    return sum(componenti) / len(componenti), flag_rifiuto_esplicito


def valuta_distanza(seeker, cand, dist_km, cfg):
    """STEP 0 punto 3bis (Algoritmo_Ranking_Finale_v1.md): la distanza non è
    più un tetto fisso in km uguale per tutti (pref_distanza_max_km,
    SUPERATO). Sotto la soglia urbana resta un fattore graduato "classico";
    oltre, diventa un filtro condizionale basato su quanto le due persone
    dichiarano di tenerci (importanza_vicinanza_geografica) e se condividono
    almeno una lingua in cui sostenere una relazione (lingue_parlate) — i km
    reali oltre quella soglia smettono di essere psicologicamente rilevanti
    in sé (Milano-Roma vs Milano-Dubai è quasi la stessa "non dietro
    l'angolo"), conta la disponibilità dichiarata a gestire la distanza.

    Ritorna (passa: bool, punteggio_distanza: float|None) — punteggio_distanza
    è None quando il filtro fallisce (nessun punteggio da propagare)."""
    if dist_km is None:
        # coordinate mancanti su uno dei due lati (v. haversine_km) — non è
        # "lontano", è "sconosciuto": il filtro distanza non può essere
        # valutato, quindi non passa, invece di confondersi con il ramo
        # "oltre l'area urbana ma lingua condivisa" che presume una distanza
        # reale nota.
        return False, None
    soglia_urbana = cfg["soglia_area_urbana_km"]
    if dist_km <= soglia_urbana:
        return True, 1 - (dist_km / soglia_urbana)

    lingue_a = set(seeker["lingue_parlate"] or [])
    lingue_b = set(cand["lingue_parlate"] or [])
    if not (lingue_a & lingue_b):
        # senza una lingua condivisa la relazione non può nemmeno iniziare,
        # a prescindere da quanto due profili siano affini sul resto —
        # qui il filtro resta rigido.
        return False, None

    imp_a = seeker["importanza_vicinanza_geografica"]
    imp_b = cand["importanza_vicinanza_geografica"]
    importanza_media = ((imp_a if imp_a is not None else 0.5) + (imp_b if imp_b is not None else 0.5)) / 2

    if importanza_media > cfg["soglia_importanza_vicinanza_esclusione"]:
        # entrambi (o anche uno solo, in modo marcato) considerano la
        # vicinanza un fattore decisivo: rispettarlo è più importante che
        # proporre comunque il match.
        return False, None

    return True, max(0.2, min(0.8, 1 - importanza_media))


def hard_filters_ok(seeker, cand, dist_km, cfg):
    if cand["flag_revisione"]:
        return False, None
    if not (seeker["pref_eta_min"] <= cand["eta"] <= seeker["pref_eta_max"]):
        return False, None
    if not (cand["pref_eta_min"] <= seeker["eta"] <= cand["pref_eta_max"]):
        return False, None
    passa_distanza, punteggio_distanza = valuta_distanza(seeker, cand, dist_km, cfg)
    if not passa_distanza:
        return False, None
    if seeker["pref_genere_cercato"] and cand["genere"] != seeker["pref_genere_cercato"]:
        return False, None
    if cand["pref_genere_cercato"] and seeker["genere"] != cand["pref_genere_cercato"]:
        return False, None
    if seeker["pref_accetta_figli"] == "No" and cand["ha_figli"]:
        return False, None
    if cand["pref_accetta_figli"] == "No" and seeker["ha_figli"]:
        return False, None
    return True, punteggio_distanza


def load_pool(cur):
    """Carica tutti gli utenti Attivi con i dati necessari al matching in un
    dizionario in memoria — usato sia per l'anteprima singola sia per il
    batch mensile, per evitare N query ripetute per candidato."""
    cur.execute("""
        SELECT u.user_id, u.nome, u.cognome, u.genere, u.orientamento_sessuale,
               EXTRACT(YEAR FROM age(u.data_nascita))::int AS eta, u.ha_figli,
               s.coordinate_gps[0] AS lon, s.coordinate_gps[1] AS lat,
               d.pref_genere_cercato, d.pref_eta_min, d.pref_eta_max, d.pref_accetta_figli,
               sc.pref_altezza_min, sc.pref_altezza_max, sc.pref_fumo, sc.pref_alcol,
               sc.pref_importanza_religione,
               p.altezza_cm, p.fumo, p.alcol, p.foto_profilo_url,
               p.embedding_visivo_profilo, p.embedding_visivo_partner_ideale,
               so.importanza_religione, so.importanza_vicinanza_geografica, so.lingue_parlate,
               ps.score_big5_estroversione, ps.score_big5_gradevolezza,
               ps.score_big5_coscienziosita, ps.score_big5_nevroticismo, ps.score_big5_apertura,
               ps.confidenza_big5_estroversione, ps.confidenza_big5_gradevolezza,
               ps.confidenza_big5_coscienziosita, ps.confidenza_big5_nevroticismo,
               ps.confidenza_big5_apertura,
               ps.score_maturita_emotiva, ps.ansia_score, ps.evitamento_score,
               ps.flag_profilo_per_revisione_dati,
               ps.profilo_valori_self, ps.profilo_valori_partner_ideale,
               ps.profilo_stile_vita_self, ps.profilo_stile_vita_partner_ideale,
               ps.profilo_dinamica_relazionale_self, ps.profilo_dinamica_relazionale_partner_ideale,
               ps.profilo_aspirazioni_self, ps.profilo_aspirazioni_partner_ideale,
               it.mi_piace_tags, it.non_sopporto_tags, it.partner_vorrei_tags, it.partner_non_vorrei_tags
        FROM users u
        JOIN socio_profile s ON s.user_id = u.user_id
        JOIN dealbreaker_criteria d ON d.user_id = u.user_id
        JOIN soft_criteria sc ON sc.user_id = u.user_id
        JOIN physical_profile p ON p.user_id = u.user_id
        JOIN socio_profile so ON so.user_id = u.user_id
        JOIN psychometric_scores ps ON ps.user_id = u.user_id
        LEFT JOIN interest_tags it ON it.user_id = u.user_id
        WHERE u.stato_account = 'Attivo'
    """)
    righe = cur.fetchall()

    # Punteggio_Tag_Liste (Ainima_Liste_Piace_Detesta_v1.md): tutti i tag di
    # tutto il pool si risolvono in un colpo solo dalla cache condivisa,
    # invece di una query per candidato — stesso principio delle altre
    # tabelle satellite caricate qui sopra.
    tutti_i_tag = set()
    for r in righe:
        for campo in ("mi_piace_tags", "non_sopporto_tags", "partner_vorrei_tags", "partner_non_vorrei_tags"):
            tutti_i_tag.update(r[campo] or [])
    embedding_per_tag = {}
    if tutti_i_tag:
        cur.execute(
            "SELECT tag_normalizzato, embedding_vector FROM tag_embedding_cache WHERE tag_normalizzato = ANY(%s)",
            (list(tutti_i_tag),),
        )
        embedding_per_tag = {row["tag_normalizzato"]: row["embedding_vector"] for row in cur.fetchall()}

    # Correzione anisotropia (v. CLAUDE.md 2026-08-20): si sottrae il
    # centroide UNA volta qui, non dentro cosine()/tag_overlap_score — così
    # ogni embedding entra già "centrato" in tutti i confronti a valle,
    # senza toccare la formula di similarità condivisa con altri usi
    # (self/ideal narrativi, embedding visivi) che non hanno questo problema
    # nella stessa misura. None (cache centroide non ancora calcolata) →
    # nessuna correzione, degrado a comportamento pre-esistente.
    centroide = tag_matching.get_centroide(cur)
    centroide_np = np.array(centroide) if centroide is not None else None

    # Bug reale di memoria trovato dal vivo (v. CLAUDE.md): _risolvi() veniva
    # chiamata 4 volte per utente (una per campo tag) e ri-centrava OGNI tag
    # da zero ad ogni chiamata — con un vocabolario di tag condiviso e
    # piccolo (~80-90 unici su ~1000 utenti), lo stesso tag veniva
    # ricalcolato migliaia di volte. Su Render (piano gratuito, 512MB)
    # questo da solo allocava ~880MB (28.8 milioni di float, misurato con
    # tracemalloc) e faceva andare il processo in OOM ad ogni chiamata di
    # find_best_match/run_monthly_batch. Centrato UNA sola volta per tag
    # unico qui sotto, poi solo un lookup — stesso risultato numerico,
    # ~100x meno allocazioni.
    embedding_per_tag_centrato = embedding_per_tag
    if centroide_np is not None:
        embedding_per_tag_centrato = {
            t: (np.array(v) - centroide_np).tolist() for t, v in embedding_per_tag.items()
        }

    def _risolvi(tags):
        # un tag non ancora in cache (dato non ancora elaborato) viene
        # semplicemente escluso da questo confronto, invece di far fallire
        # l'intero calcolo — difensivo, non dovrebbe succedere se
        # l'endpoint di salvataggio ha già calcolato l'embedding.
        return [embedding_per_tag_centrato[t] for t in (tags or []) if t in embedding_per_tag_centrato]

    pool = {}
    for r in righe:
        pool[r["user_id"]] = {
            "nome": r["nome"], "cognome": r["cognome"], "genere": r["genere"],
            "orientamento": r["orientamento_sessuale"], "eta": r["eta"], "ha_figli": r["ha_figli"],
            "lon": r["lon"], "lat": r["lat"],
            "pref_genere_cercato": r["pref_genere_cercato"],
            "pref_eta_min": r["pref_eta_min"], "pref_eta_max": r["pref_eta_max"],
            "pref_accetta_figli": r["pref_accetta_figli"],
            "pref_altezza_min": r["pref_altezza_min"], "pref_altezza_max": r["pref_altezza_max"],
            "pref_fumo": r["pref_fumo"], "pref_alcol": r["pref_alcol"],
            "pref_importanza_religione": r["pref_importanza_religione"],
            "altezza_cm": r["altezza_cm"], "fumo": r["fumo"], "alcol": r["alcol"],
            "foto_profilo_url": r["foto_profilo_url"],
            "emb_profilo": r["embedding_visivo_profilo"], "emb_pi": r["embedding_visivo_partner_ideale"],
            "importanza_religione": r["importanza_religione"],
            "importanza_vicinanza_geografica": r["importanza_vicinanza_geografica"],
            "lingue_parlate": r["lingue_parlate"],
            "estroversione": r["score_big5_estroversione"], "gradevolezza": r["score_big5_gradevolezza"],
            "coscienziosita": r["score_big5_coscienziosita"], "nevroticismo": r["score_big5_nevroticismo"],
            "apertura": r["score_big5_apertura"], "maturita": r["score_maturita_emotiva"],
            # Blocco C (v. CLAUDE.md): colonne NOT NULL DEFAULT 1.0 a schema,
            # il fallback qui è solo difensivo (stesso trattamento già
            # riservato ad ansia/evitamento sopra), non un caso atteso.
            "conf_estroversione": r["confidenza_big5_estroversione"] if r["confidenza_big5_estroversione"] is not None else 1.0,
            "conf_gradevolezza": r["confidenza_big5_gradevolezza"] if r["confidenza_big5_gradevolezza"] is not None else 1.0,
            "conf_coscienziosita": r["confidenza_big5_coscienziosita"] if r["confidenza_big5_coscienziosita"] is not None else 1.0,
            "conf_nevroticismo": r["confidenza_big5_nevroticismo"] if r["confidenza_big5_nevroticismo"] is not None else 1.0,
            "conf_apertura": r["confidenza_big5_apertura"] if r["confidenza_big5_apertura"] is not None else 1.0,
            "ansia": r["ansia_score"] if r["ansia_score"] is not None else 0.5,
            "evitamento": r["evitamento_score"] if r["evitamento_score"] is not None else 0.5,
            "flag_revisione": r["flag_profilo_per_revisione_dati"],
            # Test Profilo Relazionale (Blocco D — v. CLAUDE.md): dict già
            # deserializzati da psycopg2 (colonne JSONB), None se il test non
            # è stato ancora completato — punteggio_narrativo_strutturato()
            # gestisce il fallback neutro.
            "profilo_valori_self": r["profilo_valori_self"],
            "profilo_valori_partner_ideale": r["profilo_valori_partner_ideale"],
            "profilo_stile_vita_self": r["profilo_stile_vita_self"],
            "profilo_stile_vita_partner_ideale": r["profilo_stile_vita_partner_ideale"],
            "profilo_dinamica_relazionale_self": r["profilo_dinamica_relazionale_self"],
            "profilo_dinamica_relazionale_partner_ideale": r["profilo_dinamica_relazionale_partner_ideale"],
            "profilo_aspirazioni_self": r["profilo_aspirazioni_self"],
            "profilo_aspirazioni_partner_ideale": r["profilo_aspirazioni_partner_ideale"],
            "mi_piace_emb": _risolvi(r["mi_piace_tags"]),
            "non_sopporto_emb": _risolvi(r["non_sopporto_tags"]),
            "partner_vorrei_emb": _risolvi(r["partner_vorrei_tags"]),
            "partner_non_vorrei_emb": _risolvi(r["partner_non_vorrei_tags"]),
        }
    return pool


def load_config(cur):
    cur.execute("SELECT chiave, valore FROM system_config")
    return {row["chiave"]: row["valore"] for row in cur.fetchall()}


def load_config_floats(cur):
    """system_config è una tabella chiave-valore CONDIVISA con impostazioni
    non numeriche estranee al matching (es. Blocco E:
    giorno_invio_email_engagement='Martedì') — bug reale trovato dal vivo
    (v. CLAUDE.md): un float(v) incondizionato su ogni riga crashava
    l'intero motore di matching (run-cycle e il trigger singolo) appena
    quella riga non numerica è stata aggiunta, mai più notato perché il
    ciclo mensile non era stato rieseguito dopo il Blocco E. Le chiavi non
    numeriche non sono comunque parametri del motore di matching — si
    escludono, non si prova a "salvarle" in altro modo."""
    risultato = {}
    for k, v in load_config(cur).items():
        try:
            risultato[k] = float(v)
        except (TypeError, ValueError):
            continue
    return risultato


def media_visiva_bidirezionale(seeker, cand):
    sims = []
    if seeker["emb_pi"] is not None and cand["emb_profilo"] is not None:
        sims.append(cosine(seeker["emb_pi"], cand["emb_profilo"]))
    if cand["emb_pi"] is not None and seeker["emb_profilo"] is not None:
        sims.append(cosine(cand["emb_pi"], seeker["emb_profilo"]))
    if not sims:
        return None
    return sum(sims) / len(sims)


def seleziona_per_somiglianza_visiva(seeker, id_ordinati, pool, n, cfg):
    """RF-11a/RF-11b: shortlist dei primi n candidati per punteggio
    caratteriale, poi — SOLO se il seeker ha caricato la foto "partner
    ideale" — vince SEMPRE il candidato visivamente più simile tra questi
    (media bidirezionale sugli embedding volto), non solo in caso di
    quasi pareggio (v. decisione utente 2026-08-19, sostituisce il
    tie-break-tra-quasi-pari di stable_v1/v2 — v. CLAUDE.md). RNF-08:
    agisce solo dentro la shortlist già filtrata su compatibilità, mai
    per bypassare i filtri hard o la soglia minima.

    2026-08-20 (stable_v5, v. CLAUDE.md): la soglia minima non è più un
    valore assoluto fisso (0.20) inventato a occhio — verificato che il
    90° percentile delle similarità ArcFace tra coppie CASUALI del pool
    era già 0.334, ben sopra quella soglia: un valore assoluto basso
    lasciava che il tie-break scattasse su rumore statistico, non su una
    somiglianza reale. `soglia_similarita_visiva_minima` in system_config
    è ora un valore ricalcolato periodicamente (script dedicato, nessuno
    scheduler reale — stesso limite già accettato per il centroide tag)
    sul percentile target `soglia_percentile_similarita_visiva` (default
    0.90) della distribuzione reale del pool corrente. Se non ancora
    calcolato, fallback al vecchio valore 0.20 (degrado, non un errore).

    Ritorna (id_vincitore, selezionato_per_somiglianza_visiva: bool)."""
    if seeker["emb_pi"] is None:
        return id_ordinati[0], False  # RF-11b: fallback esplicito, nessuna foto caricata

    soglia = cfg.get("soglia_similarita_visiva_minima", 0.20)
    shortlist = id_ordinati[:n]
    medie = {cid: media_visiva_bidirezionale(seeker, pool[cid]) for cid in shortlist}
    migliore_media = max((m for m in medie.values() if m is not None), default=None)
    if migliore_media is None or migliore_media < soglia:
        return id_ordinati[0], False

    vincitore_id = max(shortlist, key=lambda cid: medie[cid] if medie[cid] is not None else -1)
    return vincitore_id, vincitore_id != id_ordinati[0]


def find_best_match(seeker_id, pool, cfg):
    """Applica STEP 0-4 + selezione visiva RF-11a/b per un singolo cercatore
    contro tutto il pool in memoria. Ritorna un dizionario con l'esito
    strutturato — non scrive nulla, usato sia per l'anteprima sia dal batch
    mensile."""
    seeker = pool[seeker_id]

    if seeker["flag_revisione"]:
        return {"esito": "revisione_umana"}

    candidati = []
    for cand_id, cand in pool.items():
        if cand_id == seeker_id:
            continue
        dist = haversine_km(seeker["lon"], seeker["lat"], cand["lon"], cand["lat"])
        passa, punteggio_distanza = hard_filters_ok(seeker, cand, dist, cfg)
        if not passa:
            continue
        bf = bigfive_score(seeker, cand)
        eq = eq_score(seeker, cand)
        narrativa, flag_asimmetria_narrativa = punteggio_narrativo_strutturato(seeker, cand)
        soft, flag_rifiuto_esplicito = combina_soft_e_distanza(seeker, cand, punteggio_distanza)
        final = (cfg["weight_bigfive"] * bf + cfg["weight_eq_attaccamento"] * eq +
                 cfg["weight_narrativa"] * narrativa + cfg["weight_preferenze_soft"] * soft)
        candidati.append({"id": cand_id, "cand": cand, "dist": dist, "bf": bf, "eq": eq,
                           "narrativa": narrativa, "soft": soft, "final": final,
                           "flag_rifiuto_esplicito": flag_rifiuto_esplicito,
                           "flag_asimmetria_narrativa": flag_asimmetria_narrativa})

    if not candidati:
        return {"esito": "nessun_candidato"}

    candidati.sort(key=lambda c: c["final"], reverse=True)
    migliore = candidati[0]

    if migliore["final"] < cfg["soglia_minima_proposta"]:
        return {"esito": "slow_matching", "top_score": migliore["final"]}

    per_id = {c["id"]: c for c in candidati}
    n = int(cfg.get("dimensione_shortlist_analisi_visiva", 5))
    vincitore_id, selezionato_per_somiglianza_visiva = seleziona_per_somiglianza_visiva(
        seeker, [c["id"] for c in candidati], pool, n, cfg)
    vincitore = per_id[vincitore_id]

    return {
        "esito": "proposta",
        "candidato_id": vincitore["id"],
        "final_score": vincitore["final"],
        "bf": vincitore["bf"], "eq": vincitore["eq"], "soft": vincitore["soft"],
        "distanza_km": vincitore["dist"],
        "selezionato_per_somiglianza_visiva": selezionato_per_somiglianza_visiva,
        "flag_rifiuto_esplicito": vincitore["flag_rifiuto_esplicito"],
        "flag_asimmetria_narrativa": vincitore["flag_asimmetria_narrativa"],
        "shortlist": [c["id"] for c in candidati[:n]],
    }


def load_recent_history_pairs(cur, mesi):
    """Coppie (frozenset di due user_id) con un match negli ultimi N mesi —
    caricate una volta in memoria invece di una query per candidato, per
    evitare N+1 query su un pool di 1000 utenti. V. feedback utente: lo
    storico deve scoraggiare la ripetizione ravvicinata, non essere una
    blacklist permanente (per questo la finestra è a N mesi, configurabile
    via system_config, non un'esclusione per sempre)."""
    cur.execute("""
        SELECT user_a_id, user_b_id FROM matches
        WHERE data_proposta >= now() - (%s || ' months')::interval
    """, (mesi,))
    return {frozenset((r["user_a_id"], r["user_b_id"])) for r in cur.fetchall()}


def build_preference_list(seeker_id, pool, cfg, history_pairs, gia_impegnati):
    """Lista di candidati ordinata per compatibilità dal punto di vista del
    SOLO seeker — usata come input dell'abbinamento stabile (v. sotto).
    RF-11a/RF-11b: la selezione per somiglianza visiva sposta in cima alla
    lista il vincitore della shortlist (dimensione_shortlist_analisi_visiva),
    non solo in caso di quasi pareggio — v. seleziona_per_somiglianza_visiva.

    Ritorna (lista_ordinata_di_id, motivo_se_vuota, selezionato_per_somiglianza_visiva:
    True se il primo elemento della lista è in quella posizione grazie alla
    somiglianza visiva e non al solo punteggio caratteriale)."""
    seeker = pool[seeker_id]
    if seeker["flag_revisione"]:
        return [], "revisione_umana", False
    if seeker_id in gia_impegnati:
        return [], "gia_impegnato", False

    candidati = []
    for cand_id, cand in pool.items():
        if cand_id == seeker_id or cand_id in gia_impegnati:
            continue
        if frozenset((seeker_id, cand_id)) in history_pairs:
            continue
        dist = haversine_km(seeker["lon"], seeker["lat"], cand["lon"], cand["lat"])
        passa, punteggio_distanza = hard_filters_ok(seeker, cand, dist, cfg)
        if not passa:
            continue
        bf = bigfive_score(seeker, cand)
        eq = eq_score(seeker, cand)
        narrativa, _ = punteggio_narrativo_strutturato(seeker, cand)
        soft, _ = combina_soft_e_distanza(seeker, cand, punteggio_distanza)
        final = (cfg["weight_bigfive"] * bf + cfg["weight_eq_attaccamento"] * eq +
                 cfg["weight_narrativa"] * narrativa + cfg["weight_preferenze_soft"] * soft)
        if final < cfg["soglia_minima_proposta"]:
            continue
        candidati.append((cand_id, final))

    if not candidati:
        return [], "nessun_candidato", False

    candidati.sort(key=lambda c: -c[1])
    id_ordinati = [cid for cid, _ in candidati]

    n = int(cfg.get("dimensione_shortlist_analisi_visiva", 5))
    vincitore_id, selezionato_visivo = seleziona_per_somiglianza_visiva(seeker, id_ordinati, pool, n, cfg)
    if vincitore_id != id_ordinati[0]:
        id_ordinati = [vincitore_id] + [cid for cid in id_ordinati if cid != vincitore_id]

    return id_ordinati, None, selezionato_visivo


def stable_match(preference_lists):
    """Abbinamento stabile generalizzato (propose-and-hold, variante non
    bipartita di Gale-Shapley — v. spiegazione data all'utente: qui non ci
    sono due gruppi distinti come nel problema classico, perché due uomini
    gay possono scegliersi a vicenda, quindi non è garantita in astratto
    l'esistenza di UNA soluzione stabile come nel caso bipartito, ma
    l'euristica converge sempre a un risultato ragionevole e termina).

    Ogni persona "propone" al primo nome libero della propria lista che non
    ha ancora provato; chi riceve la proposta la tiene se non ha nulla di
    meglio in corso, altrimenti la rifiuta. Il proponente respinto passa al
    successivo. Risultato: nessuno resta con un partner peggiore di uno che
    lo preferirebbe a sua volta — la persona molto richiesta ottiene una
    delle sue scelte migliori, chi non compare in alto in nessuna lista
    resta spesso senza abbinamento (Slow Matching), non per esclusione
    ma perché nessuno lo classifica abbastanza in alto.

    Ritorna un dict {user_id: partner_id} simmetrico (solo per chi ha
    trovato un partner)."""
    rango = {uid: {cid: i for i, cid in enumerate(lista)} for uid, lista in preference_lists.items()}
    puntatore = {uid: 0 for uid in preference_lists}
    partner = {}
    liberi = [uid for uid, lista in preference_lists.items() if lista]

    def preferisce(uid, nuovo, attuale):
        r = rango.get(uid, {})
        if nuovo not in r:
            return False
        if attuale not in r:
            return True
        return r[nuovo] < r[attuale]

    i = 0
    while i < len(liberi):
        p = liberi[i]
        if p in partner:
            i += 1
            continue
        lista_p = preference_lists.get(p, [])
        matched = False
        while puntatore[p] < len(lista_p) and not matched:
            c = lista_p[puntatore[p]]
            puntatore[p] += 1
            if c not in partner:
                partner[p] = c
                partner[c] = p
                matched = True
            elif preferisce(c, p, partner[c]):
                q = partner[c]
                del partner[q]
                partner[p] = c
                partner[c] = p
                matched = True
                liberi.append(q)  # q torna libero, riparte dal punto dove era rimasto
        i += 1

    return partner


def run_monthly_batch(conn, dry_run=True):
    """RF-11: genera una proposta al mese per ogni utente Attivo, calcolando
    le preferenze di TUTTI prima di decidere qualunque coppia (risolve il
    problema di reciprocità del ciclo greedy precedente — v. discussione
    con l'utente, 2026-08-13) e tenendo conto dello storico recente (non
    ripropone una coppia già tentata negli ultimi N mesi, senza escluderla
    per sempre — parametro system_config.mesi_esclusione_rimatch)."""
    cur = conn.cursor()
    pool = load_pool(cur)
    cfg = load_config_floats(cur)
    mesi_storico = int(cfg.get("mesi_esclusione_rimatch", 6))
    history_pairs = load_recent_history_pairs(cur, mesi_storico)

    cur.execute("SELECT user_a_id, user_b_id FROM matches WHERE stato IN ('Proposto','Accettato_A','Accettato_B')")
    gia_impegnati = set()
    for r in cur.fetchall():
        gia_impegnati.add(r["user_a_id"])
        gia_impegnati.add(r["user_b_id"])

    preference_lists = {}
    motivi_vuoti = {}
    top_selezionato_visivo = {}  # seeker_id -> True se il 1° elemento della sua lista è lì per RF-11a/b
    for seeker_id in pool:
        lista, motivo, selezionato_visivo = build_preference_list(seeker_id, pool, cfg, history_pairs, gia_impegnati)
        if lista:
            preference_lists[seeker_id] = lista
            top_selezionato_visivo[seeker_id] = selezionato_visivo
        elif motivo:
            motivi_vuoti[seeker_id] = motivo

    coppie = stable_match(preference_lists)

    risultati = []
    scritti = set()
    for uid in pool:
        if uid in scritti:
            continue
        if uid in coppie:
            cand_id = coppie[uid]
            scritti.add(uid)
            scritti.add(cand_id)
            bf = bigfive_score(pool[uid], pool[cand_id])
            eq = eq_score(pool[uid], pool[cand_id])
            narrativa, flag_asimmetria_narrativa = punteggio_narrativo_strutturato(pool[uid], pool[cand_id])
            dist = haversine_km(pool[uid]["lon"], pool[uid]["lat"], pool[cand_id]["lon"], pool[cand_id]["lat"])
            _, punteggio_distanza = valuta_distanza(pool[uid], pool[cand_id], dist, cfg)
            soft, flag_rifiuto_esplicito = combina_soft_e_distanza(pool[uid], pool[cand_id], punteggio_distanza)
            final_score = (cfg["weight_bigfive"] * bf + cfg["weight_eq_attaccamento"] * eq +
                           cfg["weight_narrativa"] * narrativa + cfg["weight_preferenze_soft"] * soft)
            # true se, per almeno uno dei due lati, questo partner è il suo
            # 1° in lista grazie alla somiglianza visiva (RF-11a/b) e non al
            # solo punteggio caratteriale
            selezionato_visivo = (
                (top_selezionato_visivo.get(uid) and preference_lists[uid][0] == cand_id) or
                (top_selezionato_visivo.get(cand_id) and preference_lists[cand_id][0] == uid)
            )
            esito = {"esito": "proposta", "seeker_id": uid, "candidato_id": cand_id, "final_score": final_score,
                      "flag_rifiuto_esplicito": flag_rifiuto_esplicito,
                      "flag_asimmetria_narrativa": flag_asimmetria_narrativa}
            risultati.append(esito)

            if not dry_run:
                scadenza = datetime.now() + timedelta(days=int(cfg.get("finestra_risposta_match_giorni", 7)))
                shortlist = [c["id"] if isinstance(c, dict) else c for c in
                             preference_lists[uid][:int(cfg.get("dimensione_shortlist_analisi_visiva", 5))]]
                cur.execute("""
                    INSERT INTO matches (user_a_id, user_b_id, stato, final_score,
                                         data_scadenza_risposta, algoritmo_versione, algoritmo_parametri,
                                         shortlist_candidati, selezionato_per_somiglianza_visiva,
                                         flag_rifiuto_esplicito, flag_asimmetria_narrativa)
                    VALUES (%s, %s, 'Proposto', %s, %s, %s, %s::jsonb, %s::uuid[], %s, %s, %s)
                """, (str(uid), str(cand_id), final_score, scadenza,
                      ALGORITMO_VERSIONE, json.dumps(cfg),
                      [str(c) for c in shortlist], bool(selezionato_visivo),
                      bool(flag_rifiuto_esplicito), bool(flag_asimmetria_narrativa)))
        elif uid in motivi_vuoti:
            risultati.append({"esito": motivi_vuoti[uid], "seeker_id": uid})
            scritti.add(uid)
        else:
            # aveva una lista di preferenze ma nessuno l'ha voluto (tutti i
            # suoi candidati preferivano qualcun altro) -> resta senza
            # proposta questo ciclo, coerente con lo spirito Slow Matching
            risultati.append({"esito": "non_abbinato_stabile", "seeker_id": uid})
            scritti.add(uid)

    if not dry_run:
        conn.commit()
    return risultati
