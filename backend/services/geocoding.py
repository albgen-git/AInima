"""Risoluzione di `comune_residenza` (testo libero inserito dall'utente in
onboarding) in coordinate GPS, per il filtro/punteggio di distanza dello
Stage matching (v. CLAUDE.md §3bis, `matching_engine.valuta_distanza`).

Tre fonti in ordine, la prima che trova una corrispondenza vince (v. CLAUDE.md,
decisione esplicita dell'utente 2026-09-02):
1. Dataset comuni italiani (`data/comuni_italiani.csv`, ~7983 comuni, fonte
   pubblica github.com/tripitakit) — copre l'MVP Milano/Italia senza alcuna
   chiamata esterna.
2. Dataset città/emirati UAE (`data/citta_uae.csv`, elenco ridotto scritto a
   mano) — coerente con la decisione 2026-08-12 di preparare lo schema per il
   mercato Dubai/GCC senza costruire la UI/localizzazione ora.
3. Geocoding esterno gratuito (Nominatim/OpenStreetMap) — solo se il testo
   non è in nessuno dei due dataset, per non lasciare senza coordinate un
   utente che vive fuori da Italia/UAE. Nessuna chiave richiesta, ma la
   policy d'uso di Nominatim impone uno User-Agent identificativo e un
   limite di 1 richiesta/secondo — accettabile qui perché la chiamata
   avviene al più una volta per utente, in fase di salvataggio del profilo,
   mai in un ciclo batch."""

import csv
import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "AinimaApp/1.0 (matchmaking platform; contatto: albgen@gmail.com)"

_comuni_it: dict[str, tuple[float, float]] | None = None
_citta_uae: dict[str, tuple[float, float]] | None = None


def _normalizza(testo: str) -> str:
    """Minuscolo, senza accenti, spazi/apostrofi normalizzati — per
    confrontare l'input libero dell'utente con i nomi nei dataset senza
    farsi bloccare da differenze di accentazione o punteggiatura."""
    testo = unicodedata.normalize("NFKD", testo.strip().lower())
    testo = "".join(c for c in testo if not unicodedata.combining(c))
    testo = testo.replace("'", " ").replace("’", " ")
    testo = re.sub(r"\s+", " ", testo).strip()
    return testo


def _carica_csv(nome_file: str, colonna_nome: str) -> dict[str, tuple[float, float]]:
    percorso = os.path.join(_DATA_DIR, nome_file)
    risultato: dict[str, tuple[float, float]] = {}
    with open(percorso, encoding="utf-8") as f:
        for riga in csv.DictReader(f):
            if not riga["latitudine"] or not riga["longitudine"]:
                # alcune righe del dataset pubblico (comuni di fusione recente)
                # non hanno ancora coordinate compilate — saltate, degradano
                # al fallback Nominatim invece di far fallire il caricamento
                continue
            chiave = _normalizza(riga[colonna_nome])
            if chiave not in risultato:  # prima occorrenza vince sui pochi duplicati (v. commento sopra)
                risultato[chiave] = (float(riga["latitudine"]), float(riga["longitudine"]))
    return risultato


def _dataset_comuni_it() -> dict[str, tuple[float, float]]:
    global _comuni_it
    if _comuni_it is None:
        _comuni_it = _carica_csv("comuni_italiani.csv", "Comune")
    return _comuni_it


def _dataset_citta_uae() -> dict[str, tuple[float, float]]:
    global _citta_uae
    if _citta_uae is None:
        _citta_uae = _carica_csv("citta_uae.csv", "citta")
    return _citta_uae


def _geocodifica_nominatim(testo: str) -> tuple[float, float] | None:
    query = urllib.parse.urlencode({"q": testo, "format": "json", "limit": 1})
    richiesta = urllib.request.Request(
        f"{_NOMINATIM_URL}?{query}",
        headers={"User-Agent": _USER_AGENT},
    )
    try:
        with urllib.request.urlopen(richiesta, timeout=5) as risposta:
            risultati = json.loads(risposta.read().decode("utf-8"))
    except Exception as e:
        print(f"[ERRORE] geocoding Nominatim per '{testo}' fallito: {e}")
        return None
    if not risultati:
        return None
    return float(risultati[0]["lat"]), float(risultati[0]["lon"])


def geocodifica_comune(comune_residenza: str) -> tuple[float, float] | None:
    """Ritorna (lat, lon) o None se non risolvibile da nessuna delle 3
    fonti — il chiamante (routers/profile.py) deve trattare None come
    'non aggiornare coordinate_gps', mai come un errore bloccante."""
    if not comune_residenza or not comune_residenza.strip():
        return None
    chiave = _normalizza(comune_residenza)

    match_it = _dataset_comuni_it().get(chiave)
    if match_it is not None:
        return match_it

    match_uae = _dataset_citta_uae().get(chiave)
    if match_uae is not None:
        return match_uae

    return _geocodifica_nominatim(comune_residenza.strip())
