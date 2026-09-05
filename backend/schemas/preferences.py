"""RF-08: criteri di ricerca, split esplicito dealbreaker/soft (§7.4)."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

Genere = Literal["Maschile", "Femminile", "Non binario", "Altro"]
SiNoIndifferente = Literal["Si", "No", "Indifferente"]
SiNoDaValutare = Literal["Si", "No", "Da valutare"]

# Specchio di stato_civile (v. StepCivilStatus.tsx) — le 4 opzioni selezionabili
# per "stato civile gradito nel partner" (2026-09-05, multi-selezione).
STATO_CIVILE_VALORI = ["Celibe/Nubile", "Separato/a", "Divorziato/a", "Vedovo/a"]


class DealbreakerCriteriaIn(BaseModel):
    """Filtro di esclusione — mai un input dello score pesato (v. CLAUDE.md).
    pref_distanza_max_km RIMOSSO (SUPERATO, v. Ainima_00_Indice_Schema_Consolidato_v1.md
    §3.2) — sostituito da importanza_vicinanza_geografica/lingue_parlate,
    campi del profilo (v. ProfileUpdate in schemas/users.py), non dei criteri."""
    pref_genere_cercato: Optional[Genere] = None
    pref_eta_min: int = Field(ge=18, le=99)
    pref_eta_max: int = Field(ge=18, le=99)
    pref_accetta_figli: SiNoIndifferente = "Indifferente"
    pref_desidera_figli_futuri: SiNoDaValutare = "Da valutare"


class SoftCriteriaIn(BaseModel):
    """Contribuiscono allo score di compatibilità, non escludono."""
    pref_altezza_min: Optional[int] = None
    pref_altezza_max: Optional[int] = None
    # Multi-selezione (2026-09-05, richiesta esplicita dell'utente): un
    # filtro vuoto non ha senso operativo ("non accetto nessuno stato
    # civile") — se il campo è presente nel payload, deve contenere almeno
    # un valore canonico. None resta ammesso (campo non ancora compilato).
    pref_stato_civile_accettato: Optional[List[str]] = None
    pref_titolo_studio: Optional[str] = None
    pref_corporatura: Optional[str] = None
    pref_fumo: Optional[bool] = None
    pref_alcol: Optional[bool] = None
    pref_fede_religiosa: Optional[str] = None
    pref_importanza_religione: Optional[int] = Field(default=None, ge=1, le=5)

    @field_validator("pref_stato_civile_accettato")
    @classmethod
    def _valida_stato_civile_accettato(cls, v):
        if v is None:
            return v
        if len(v) == 0:
            raise ValueError("pref_stato_civile_accettato non può essere una lista vuota")
        non_validi = [x for x in v if x not in STATO_CIVILE_VALORI]
        if non_validi:
            raise ValueError(f"valori non validi in pref_stato_civile_accettato: {non_validi}")
        return v
