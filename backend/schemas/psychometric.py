"""RF-07: test psicometrici scritti (Big Five, Attaccamento, EQ Score) —
tutti a scoring deterministico, nessuna chat/LLM (v. CLAUDE.md 2026-08-19,
docs/Ainima_Test_Psicometrico_BigFive_v1.md,
docs/Ainima_Test_Attaccamento_v1.md, docs/Ainima_Test_EQScore_v1.md)."""

from typing import Dict

from pydantic import BaseModel, field_validator

# I 40 codici item Big Five, dal documento di riferimento v2 (8 per
# dimensione — accorciato da 50/10 per dimensione, v. CLAUDE.md).
ITEM_CODES = (
    [f"E{i}" for i in range(1, 9)] + [f"A{i}" for i in range(1, 9)] +
    [f"C{i}" for i in range(1, 9)] + [f"N{i}" for i in range(1, 9)] +
    [f"O{i}" for i in range(1, 9)]
)
REVERSE_ITEMS = {
    "E2", "E7", "A2", "A7", "C2", "C7", "N2", "N7",
    "O2", "O6", "O8",
}

# Attaccamento (Ainima_Test_Attaccamento_v1.md v2): 9 item per dimensione
# (accorciato da 12 — v. CLAUDE.md).
ITEM_CODES_ATTACCAMENTO = [f"AN{i}" for i in range(1, 10)] + [f"EV{i}" for i in range(1, 10)]
REVERSE_ITEMS_ATTACCAMENTO = {
    "AN2", "AN5", "AN8",
    "EV2", "EV5", "EV8",
}

# EQ Score (Ainima_Test_EQScore_v1.md v2): 6 item per pilastro
# (accorciato da 8 — v. CLAUDE.md).
ITEM_CODES_EQ = (
    [f"AC{i}" for i in range(1, 7)] + [f"AR{i}" for i in range(1, 7)] +
    [f"EM{i}" for i in range(1, 7)] + [f"RE{i}" for i in range(1, 7)]
)
REVERSE_ITEMS_EQ = {
    "AC2", "AC4",
    "AR1", "AR3",
    "EM2", "EM4",
    "RE2", "RE4",
}

# Test Profilo Relazionale (Ainima_Test_Profilo_Relazionale_v1.md): 13
# sotto-dimensioni in 4 categorie, 2 item ciascuna (Sé/Ideale), 26 item
# totali — nessun item invertito, nessuna domanda trappola (confermato
# esplicitamente in Ainima_00_Indice_Schema_Consolidato_v1.md: "non toccato").
SOTTODIMENSIONI_PROFILO_RELAZIONALE = {
    "valori": ["centralita_famiglia", "orientamento_carriera", "bisogno_stabilita", "crescita_personale"],
    "stile_vita": ["socialita", "organizzazione", "ritmo_vita"],
    "dinamica_relazionale": ["autonomia_fusione", "condivisione_ruoli", "espressivita_emotiva"],
    "aspirazioni": ["impegno_lungo_termine", "mobilita_geografica", "orizzonte_progettuale"],
}
# Codici item: 1 lettera categoria (V/S/D/A) + indice sotto-dimensione (1-4) +
# S(elf)/I(deale) — es. "V1S", "V1I". Ordine fisso, deriva da
# SOTTODIMENSIONI_PROFILO_RELAZIONALE (stesso ordine del documento).
PREFISSO_CATEGORIA_PROFILO_RELAZIONALE = {"valori": "V", "stile_vita": "S", "dinamica_relazionale": "D", "aspirazioni": "A"}
ITEM_CODES_PROFILO_RELAZIONALE = [
    f"{PREFISSO_CATEGORIA_PROFILO_RELAZIONALE[cat]}{i}{suffisso}"
    for cat, sottodim in SOTTODIMENSIONI_PROFILO_RELAZIONALE.items()
    for i in range(1, len(sottodim) + 1)
    for suffisso in ("S", "I")
]

# Domande trappola condivise (Ainima_00_Indice_Schema_Consolidato_v1.md,
# sezione dedicata) — 1 item indipendente da qualunque dimensione, inserito
# dentro ciascuno dei 3 test Likert. Non entra in ITEM_CODES_*/REVERSE_ITEMS_*
# (mai usato per lo scoring delle dimensioni), solo per il controllo
# separato di flag_trappola_fallita.
TRAPPOLA_RISPOSTA_ATTESA = {
    "T1": 2,  # Big Five — "seleziona 'Poco d'accordo'"
    "T2": 4,  # Attaccamento — "seleziona 'Abbastanza d'accordo'"
    "T3": 3,  # EQ Score — "seleziona 'Neutro / Dipende'"
}


def _valida_risposte_1_5(v: Dict[str, int], codici_attesi) -> Dict[str, int]:
    mancanti = set(codici_attesi) - set(v.keys())
    if mancanti:
        raise ValueError(f"Item mancanti: {sorted(mancanti)}")
    fuori_scala = {k: val for k, val in v.items() if not (1 <= val <= 5)}
    if fuori_scala:
        raise ValueError(f"Risposte fuori scala 1-5: {fuori_scala}")
    return v


class BigFiveSubmission(BaseModel):
    """Risposte grezze 1-5 per ciascuno dei 40 item, chiave = codice item (es.
    'E1'), + 1 item trappola ('T1', v. TRAPPOLA_RISPOSTA_ATTESA) — 41 chiavi totali."""
    risposte: Dict[str, int]

    @field_validator("risposte")
    @classmethod
    def valida_risposte(cls, v):
        return _valida_risposte_1_5(v, ITEM_CODES + ["T1"])


class BigFiveResult(BaseModel):
    score_big5_estroversione: float
    score_big5_gradevolezza: float
    score_big5_coscienziosita: float
    score_big5_nevroticismo: float
    score_big5_apertura: float


class AttaccamentoSubmission(BaseModel):
    """Risposte grezze 1-5 per i 18 item (AN1-9, EV1-9) + 1 item trappola
    ('T2') — 19 chiavi totali."""
    risposte: Dict[str, int]

    @field_validator("risposte")
    @classmethod
    def valida_risposte(cls, v):
        return _valida_risposte_1_5(v, ITEM_CODES_ATTACCAMENTO + ["T2"])


class AttaccamentoResult(BaseModel):
    ansia_score: float
    evitamento_score: float
    # SOLO per la UI (Ainima_Test_Attaccamento_v1.md §5 Step 4) — mai usato
    # nel calcolo di matching, che lavora sempre sulle due dimensioni sopra.
    stile_attaccamento: str


class EqSubmission(BaseModel):
    """Risposte grezze 1-5 per i 24 item (AC/AR/EM/RE 1-6) + 1 item trappola
    ('T3') — 25 chiavi totali."""
    risposte: Dict[str, int]

    @field_validator("risposte")
    @classmethod
    def valida_risposte(cls, v):
        return _valida_risposte_1_5(v, ITEM_CODES_EQ + ["T3"])


class EqResult(BaseModel):
    eq_pilastro_autoconsapevolezza: float
    eq_pilastro_autoregolazione: float
    eq_pilastro_empatia: float
    eq_pilastro_responsabilita: float
    score_maturita_emotiva: float


class ProfiloRelazionaleSubmission(BaseModel):
    """Risposte grezze 1-5 per i 26 item del Test Profilo Relazionale
    (Valori/Stile di Vita/Dinamica Relazionale/Aspirazioni, self + partner
    ideale) — nessun item trappola per questo test."""
    risposte: Dict[str, int]

    @field_validator("risposte")
    @classmethod
    def valida_risposte(cls, v):
        return _valida_risposte_1_5(v, ITEM_CODES_PROFILO_RELAZIONALE)


class ProfiloRelazionaleResult(BaseModel):
    profilo_valori_self: Dict[str, float]
    profilo_valori_partner_ideale: Dict[str, float]
    profilo_stile_vita_self: Dict[str, float]
    profilo_stile_vita_partner_ideale: Dict[str, float]
    profilo_dinamica_relazionale_self: Dict[str, float]
    profilo_dinamica_relazionale_partner_ideale: Dict[str, float]
    profilo_aspirazioni_self: Dict[str, float]
    profilo_aspirazioni_partner_ideale: Dict[str, float]


class ChatMessageIn(BaseModel):
    """Chat-intervista EQ (Prompt 1) — DISATTIVATA, v. CHAT_INTERVISTA_ATTIVA
    in routers/psychometric.py. Schema tenuto solo perché l'endpoint non è
    stato cancellato, non per uso attivo."""
    testo: str | None = None


class ChatMessageOut(BaseModel):
    testo: str
    conversazione_completata: bool = False


class NarrativeUpdate(BaseModel):
    """RF-07b: i due campi liberi che sostituiscono la chat-intervista —
    alimentano solo Prompt 3a/3b (estrazione profilo canonico) e mai
    direttamente lo score di compatibilità (RNF-11)."""
    descrizione_di_se: str | None = None
    descrizione_partner_ideale: str | None = None
