"""Rilevamento e confronto volti (RF-08c, RF-11b) via AWS Rekognition —
sostituisce il precedente piano basato su ArcFace + embedding vettoriale
precalcolato (v. CLAUDE.md, Documento_Requisiti_v1.md §8/§10 punto 13,
decisione dell'utente 2026-09-03). Nessun modello ML nel backend, nessun
embedding da calcolare/salvare a lungo termine: confronto on-demand via
chiamata API, sia in fase di upload (validazione) sia in fase di
generazione proposta (confronto di somiglianza).

Le due funzioni pubbliche hanno policy di errore DIVERSE, deliberatamente:
- rileva_volto() SOLLEVA un'eccezione se la chiamata AWS stessa fallisce
  (rete/credenziali/timeout) — stesso principio già usato in
  services/email_provider.py ("deve sollevare un'eccezione se l'invio
  fallisce — il chiamante decide come reagire, non questo layer"). È
  routers/profile.py a decidere se degradare aperto (non bloccare
  l'upload) o meno, non questo modulo.
- confronta_foto() NON solleva mai: cattura qualunque fallimento (rete,
  nessun volto rilevabile in una delle due foto, errore AWS) e ritorna
  None — perché RF-11b (v. CLAUDE.md, richiesta esplicita dell'utente)
  vuole che un confronto fallito su UN candidato specifico non blocchi
  mai la generazione dell'intera proposta, comportamento che deve valere
  per costruzione dentro il loop di matching_engine.py, non per
  disciplina di chi la chiama."""

import os

# RF-08c: soglia minima di confidenza perché un volto rilevato da
# DetectFaces sia considerato valido per accettare l'upload. 90% è lo
# stesso ordine di grandezza raccomandato da AWS per use-case "verifica
# che ci sia un volto reale" (non identificazione/matching, dove si
# userebbero soglie più alte) — abbastanza alto da scartare foto
# sfocate/di spalle/volto minuscolo o parzialmente coperto, non così
# alto da rifiutare foto normali con illuminazione non perfetta.
SOGLIA_CONFIDENZA_VOLTO = 90.0

_client = None


def _get_client():
    global _client
    if _client is None:
        import boto3

        _client = boto3.client(
            "rekognition",
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
        )
    return _client


class ValidazioneVolto:
    """RF-08c. `volto_rilevato`: almeno un volto sopra SOGLIA_CONFIDENZA_VOLTO.
    `volti_multipli`: più di un volto valido — non blocca l'upload (si usa
    comunque il volto con l'area maggiore al momento del confronto, v.
    _viso_piu_grande sotto), ma routers/profile.py lo espone nella risposta
    perché il frontend mostri l'avviso di RF-08c."""

    def __init__(self, volto_rilevato: bool, volti_multipli: bool):
        self.volto_rilevato = volto_rilevato
        self.volti_multipli = volti_multipli


def rileva_volto(immagine_bytes: bytes) -> ValidazioneVolto:
    """RF-08c: DetectFaces sui byte grezzi dell'immagine appena caricata —
    va chiamata PRIMA di salvare il file su storage (v. routers/profile.py):
    un upload senza volto valido non deve mai arrivare a scrivere un file
    né una riga DB. Solleva l'eccezione originale di boto3 se la chiamata
    AWS stessa fallisce (v. commento in cima al file)."""
    risposta = _get_client().detect_faces(Image={"Bytes": immagine_bytes}, Attributes=["DEFAULT"])
    volti_validi = [v for v in risposta.get("FaceDetails", []) if v["Confidence"] >= SOGLIA_CONFIDENZA_VOLTO]
    return ValidazioneVolto(
        volto_rilevato=len(volti_validi) > 0,
        volti_multipli=len(volti_validi) > 1,
    )


def _leggi_bytes_foto(riferimento: str) -> bytes | None:
    """Legge i byte di una foto già salvata (path locale relativo o URL
    assoluto R2 — stesso formato ritornato da PhotoStorage.salva(), v.
    services/photo_storage.py) tramite la stessa astrazione di storage già
    usata per il salvataggio — funziona identicamente per i profili demo
    (anche le loro foto vivono su R2, stesso formato URL, v. CLAUDE.md
    punto 3 della richiesta) e per gli utenti reali, nessun percorso di
    calcolo separato per i due casi. None se il file non esiste/non è
    leggibile (dato mancante, non un errore da propagare qui)."""
    from services.photo_storage import get_photo_storage

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    storage_dir = os.path.join(base_dir, "storage", "photos")
    try:
        return get_photo_storage(storage_dir).leggi(riferimento)
    except Exception as e:
        print(f"[ERRORE] lettura foto '{riferimento}' fallita: {e}")
        return None


def confronta_foto(riferimento_sorgente: str, riferimento_target: str) -> float | None:
    """RF-11b: CompareFaces tra due foto già salvate, identificate dal
    riferimento di storage (stesso valore in foto_profilo_url/
    foto_partner_ideale_url), non da byte già in memoria — la lettura
    dal backend di storage (locale o R2) avviene qui dentro. Ritorna la
    similarity 0-100 del miglior match, o None per QUALUNQUE fallimento
    (foto illeggibile, nessun volto rilevabile in una delle due, errore
    di rete/servizio AWS, timeout) — mai un'eccezione: chi chiama questa
    funzione (matching_engine.seleziona_per_somiglianza_visiva) deve
    poter trattare un singolo confronto fallito come "candidato escluso
    dal confronto visivo", senza logica di try/except propria, per
    costruzione e non per disciplina (v. commento in cima al file)."""
    bytes_sorgente = _leggi_bytes_foto(riferimento_sorgente)
    bytes_target = _leggi_bytes_foto(riferimento_target)
    if bytes_sorgente is None or bytes_target is None:
        return None
    try:
        risposta = _get_client().compare_faces(
            SourceImage={"Bytes": bytes_sorgente},
            TargetImage={"Bytes": bytes_target},
            SimilarityThreshold=0,
        )
    except Exception as e:
        print(f"[ERRORE] CompareFaces fallita: {e}")
        return None
    corrispondenze = risposta.get("FaceMatches", [])
    if not corrispondenze:
        return None
    migliore = max(corrispondenze, key=lambda m: m["Similarity"])
    return migliore["Similarity"]
