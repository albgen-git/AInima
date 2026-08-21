"""Embedding testuale deterministico dei profili canonici (self/ideal) —
sostituisce il Judge LLM Prompt 4 (eliminato, v. Ainima_Matching_Semantico_
Report_v1.md §5 e CLAUDE.md 2026-08-19): stesso principio già usato per le
foto (embedding + cosine similarity), zero "ragionamento" discorsivo o
punteggio deciso da un LLM generativo (RNF-11).

Usa lo stesso provider già collegato per il resto della pipeline (Gemini,
v. llm_pipeline.py) invece di aggiungere un nuovo servizio esterno — scelta
esplicita dell'utente per non introdurre un'altra integrazione da
configurare (v. CLAUDE.md)."""

import os

from google import genai
from google.genai import types

from services.llm_pipeline import _con_retry

_client = None

# Modello di embedding testuale corrente di Gemini — a differenza del
# modello generativo (MODELLO in llm_pipeline.py), qui non esiste un alias
# "-latest" documentato, quindi si fissa il nome stabile.
MODELLO_EMBEDDING = "gemini-embedding-001"


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def embed_testo(testo: str) -> list[float]:
    """Ritorna il vettore di embedding di un profilo canonico (testo a 4
    categorie prodotto da Prompt 3a/3b). Input trattato sempre come dato da
    vettorizzare, mai come istruzione — nessun system prompt coinvolto qui,
    a differenza delle chiamate generative altrove nella pipeline."""
    risposta = _con_retry(lambda: _get_client().models.embed_content(
        model=MODELLO_EMBEDDING,
        contents=testo,
    ))
    return list(risposta.embeddings[0].values)
