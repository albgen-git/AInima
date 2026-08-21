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

# Attaccamento (Ainima_Test_Attaccamento_v1.md): 12 item per dimensione.
ITEM_CODES_ATTACCAMENTO = [f"AN{i}" for i in range(1, 13)] + [f"EV{i}" for i in range(1, 13)]
REVERSE_ITEMS_ATTACCAMENTO = {
    "AN2", "AN4", "AN6", "AN8", "AN10", "AN12",
    "EV2", "EV4", "EV6", "EV8", "EV10", "EV12",
}

# EQ Score (Ainima_Test_EQScore_v1.md): 8 item per pilastro.
ITEM_CODES_EQ = (
    [f"AC{i}" for i in range(1, 9)] + [f"AR{i}" for i in range(1, 9)] +
    [f"EM{i}" for i in range(1, 9)] + [f"RE{i}" for i in range(1, 9)]
)
REVERSE_ITEMS_EQ = {
    "AC2", "AC4", "AC6", "AC8",
    "AR1", "AR3", "AR5", "AR7",
    "EM2", "EM4", "EM6", "EM8",
    "RE2", "RE4", "RE6", "RE8",
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
    """Risposte grezze 1-5 per ciascuno dei 40 item, chiave = codice item (es. 'E1')."""
    risposte: Dict[str, int]

    @field_validator("risposte")
    @classmethod
    def valida_risposte(cls, v):
        return _valida_risposte_1_5(v, ITEM_CODES)


class BigFiveResult(BaseModel):
    score_big5_estroversione: float
    score_big5_gradevolezza: float
    score_big5_coscienziosita: float
    score_big5_nevroticismo: float
    score_big5_apertura: float


class AttaccamentoSubmission(BaseModel):
    """Risposte grezze 1-5 per i 24 item (AN1-12, EV1-12)."""
    risposte: Dict[str, int]

    @field_validator("risposte")
    @classmethod
    def valida_risposte(cls, v):
        return _valida_risposte_1_5(v, ITEM_CODES_ATTACCAMENTO)


class AttaccamentoResult(BaseModel):
    ansia_score: float
    evitamento_score: float
    # SOLO per la UI (Ainima_Test_Attaccamento_v1.md §5 Step 4) — mai usato
    # nel calcolo di matching, che lavora sempre sulle due dimensioni sopra.
    stile_attaccamento: str


class EqSubmission(BaseModel):
    """Risposte grezze 1-5 per i 32 item (AC/AR/EM/RE 1-8)."""
    risposte: Dict[str, int]

    @field_validator("risposte")
    @classmethod
    def valida_risposte(cls, v):
        return _valida_risposte_1_5(v, ITEM_CODES_EQ)


class EqResult(BaseModel):
    eq_pilastro_autoconsapevolezza: float
    eq_pilastro_autoregolazione: float
    eq_pilastro_empatia: float
    eq_pilastro_responsabilita: float
    score_maturita_emotiva: float


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
