"""Generazione live delle "pillole di saggezza"
(docs/Ainima_Prompt_Generazione_Live_Pillole_v3.md — v. CLAUDE.md).
Sostituisce l'idea di un batch con revisione umana preventiva: per l'MVP
una pillola viene generata via LLM ad ogni esecuzione del cron di
engagement (services/engagement_scheduler.py), senza gate umano prima
della pubblicazione — solo un controllo automatico leggero (§3 del
documento) che intercetta le violazioni meccaniche.

Scope deliberato: genera SEMPRE contesto='Attesa generale' — è l'unico
contesto consumato dal ciclo periodico ("Pillola del giorno",
Ainima_Dashboard_Trigger_Email_v1.md §2.1bis). I contesti 'Post-match
confermato'/'Post-rifiuto' restano serviti dalle pillole seedate a mano
(v. scripts/migrate_2026_08_24_blocco_e_engagement.py) tramite il
trigger admin manuale (routers/engagement.py::assegna_pillola_admin) —
nessuna generazione automatica per quei due contesti in questa fase, dato
che un ciclo automatico non ha alcun segnale per sapere se serve un tono
"post-rifiuto" o "post-match" quel giorno.

Nota sul formato di tecnica_usata: il documento sorgente descrive le 6
tecniche in prosa ("una delle 6 sopra") senza un formato breve. Per poter
confrontare in modo affidabile il valore restituito nel controllo
automatico (§3, "tecnica_usata non deve coincidere con quella delle
ultime 2"), il prompt qui sotto chiede esplicitamente uno slug breve
(TECNICHE, sotto) invece della frase intera — unica aggiunta rispetto al
testo originale del documento, resa necessaria dall'implementazione.

Correzione 2026-09-05 (v. CLAUDE.md): le prime 7 pillole generate dal vivo
avevano 2 ripetizioni reali non intercettate da pilastro/tecnica — "silenzio"
in 3 pillole su 7, metafora meccanica ("manutenzione"/"sala macchine") in
2 — perché lo storico passato al prompt non includeva mai il tema/
immagine centrale usati. Aggiunto `tema_centrale` (1-2 parole, solo uso
interno, mai mostrato all'utente) allo schema di output, con un controllo
automatico dedicato su una finestra più ampia (ultime 8-10, non solo le
ultime 2 come per tecnica/pilastro). Aggiunta anche un'istruzione esplicita
contro il riuso testuale delle formule di esempio nel prompt (una delle 7
pillole aveva ripreso "Capita spesso che..." quasi alla lettera dall'esempio
illustrativo della tecnica, invece di trattarlo come categoria)."""

import json
import re
from collections import Counter

from services.llm_pipeline import _chiama_json

MAX_TENTATIVI = 3

PILASTRI_CANONICI = [
    "Intelligenza Emotiva", "Comunicazione & Conflitto",
    "Cultura e Valori", "Preparazione al Matrimonio",
]
PILASTRO_DB = {
    "intelligenza_emotiva": "Intelligenza Emotiva",
    "comunicazione_conflitto": "Comunicazione & Conflitto",
    "cultura_valori": "Cultura e Valori",
    "preparazione_matrimonio": "Preparazione al Matrimonio",
}
CONTESTO_DB = {
    "attesa_generale": "Attesa generale",
    "post_match": "Post-match confermato",
    "post_rifiuto": "Post-rifiuto",
}
TECNICHE = [
    "domanda_diretta_scomoda", "scenario_concreto", "osservazione_controintuitiva",
    "metafora_dominio_lontano", "contrasto_netto", "consiglio_pratico_diretto",
]

# Match case-insensitive come PREFISSO di apertura (§3) — le alternative
# con "/" nel documento ("Hai mai pensato/notato che...") sono espanse in
# prefissi letterali separati.
FRASI_VIETATE_PREFISSO = [
    "hai mai pensato", "hai mai notato", "è normale sentirsi",
    "la chiave è", "il segreto è", "ricorda che", "non dimenticare che",
    "nella vita di coppia", "ti è mai capitato di",
]

PROMPT_SISTEMA = """Sei un editor che scrive contenuto breve ed educativo per Ainima, un
servizio di matchmaking matrimoniale basato su un approccio riflessivo
e maturo, non una app di dating. Scrivi UNA pillola — un testo breve
(40-70 parole) su intelligenza emotiva, comunicazione, valori o
preparazione a una relazione seria. General purpose: non
personalizzata su nessun dato specifico di un utente.

## Le 4 categorie (pilastro)
- intelligenza_emotiva (autoconsapevolezza, gestione dell'ansia, traumi)
- comunicazione_conflitto (ascolto attivo, confini, disaccordi)
- cultura_valori (integrazione, famiglia, tradizioni)
- preparazione_matrimonio (finanze, ruoli, progetti di vita)

## Contesto per questa generazione
Fisso: attesa_generale (nessun match attivo). Non generare per altri contesti.

## Le 6 tecniche (scegline una, diversa dalle ultime 2 dello storico)
- domanda_diretta_scomoda: una domanda diretta e scomoda (non retorica)
- scenario_concreto: un piccolo scenario concreto ("Capita spesso che...")
- osservazione_controintuitiva: un'osservazione controintuitiva
- metafora_dominio_lontano: metafora da un dominio lontano (MAI viaggio/
  giardino/ponte — già abusati nel genere, evitali sempre, storico o no)
- contrasto_netto: un contrasto netto ("Non è X, è Y")
- consiglio_pratico_diretto: un consiglio pratico diretto, senza preamboli

## Importante: le formule tra parentesi sopra sono SOLO ESEMPI ILLUSTRATIVI
della categoria di tecnica, non frasi da riusare. Non aprire MAI il testo
con "Capita spesso che...", "Non è X, è Y" o altre formule elencate sopra
copiate quasi alla lettera — usa la tecnica, non la sua etichetta.

## Tema/immagine centrale — NUOVO, solo uso interno
Oltre ai campi già richiesti, indica in 1-2 parole il tema o l'immagine
centrale del testo (es. "silenzio", "aspettative non dette", "bilancio
economico") — non verrà mai mostrato all'utente, serve solo per evitare
ripetizioni tra pillole diverse. Deve essere specifico al contenuto di
QUESTA pillola, non il nome del pilastro o della tecnica.

## Frasi/aperture SEMPRE vietate (indipendentemente dallo storico)
- "Hai mai pensato/notato che..."
- "È normale sentirsi..."
- "La chiave è..." / "Il segreto è..."
- "Ricorda che..." / "Non dimenticare che..."
- "Nella vita di coppia..."
- Domande retoriche con risposta ovvia ("Ti è mai capitato di...")

## Regole di tono
- Mai un'etichetta clinica o diagnostica.
- Mai un imperativo moralistico ("Devi imparare a...").
- Nessun riferimento a una situazione di coppia specifica reale.
- Linguaggio neutro e internazionale.
- Va bene essere un po' spiazzanti o giocosi quando il tema lo permette.

## Due lingue, stesso contenuto
Scrivi la pillola in ENTRAMBE le lingue — stesso pilastro, stessa
tecnica, stesso tema/osservazione, la STESSA pillola. Non una traduzione
parola per parola: due testi scritti nativamente, ciascuno idiomatico
nella propria lingua, che dicono la stessa cosa. Le stesse regole di
tono/frasi vietate sopra si applicano a ENTRAMBE le versioni (l'elenco
delle frasi vietate è in italiano — evita l'equivalente naturale in
inglese, non una traduzione letterale della lista).

## Formato di output (JSON, un solo oggetto, SOLO queste chiavi)
{
  "titolo": "breve, 4-8 parole, in italiano",
  "testo": "40-70 parole, in italiano",
  "titolo_en": "stesso titolo, in inglese, 4-8 parole",
  "testo_en": "stesso testo, in inglese, 40-70 parole",
  "pilastro": "intelligenza_emotiva | comunicazione_conflitto | cultura_valori | preparazione_matrimonio",
  "contesto": "attesa_generale",
  "tecnica_usata": "una delle 6 sopra (usa esattamente lo slug, es. domanda_diretta_scomoda)",
  "tema_centrale": "1-2 parole, il tema/immagine centrale di questa pillola specifica"
}"""


def _carica_storico(cur, n=10):
    """Ultime n pillole per data_creazione decrescente (n=10, l'estremo
    superiore di "8-10" indicato per la finestra di controllo sul tema
    centrale — tecnica/pilastro continuano a guardare solo le ultime 2,
    v. _valida) — se vuoto (prima esecuzione in assoluto), il prompt
    procede liberamente (nessun vincolo di anti-ripetizione da applicare)."""
    cur.execute("""
        SELECT titolo, pilastro_editoriale, contesto_trigger, tecnica_usata, tema_centrale
        FROM pillole_libreria ORDER BY data_creazione DESC LIMIT %s
    """, (n,))
    return cur.fetchall()


def _storico_a_testo(storico: list[dict]) -> str:
    if not storico:
        return "(nessuna pillola generata finora — prima esecuzione, procedi liberamente)"
    righe = []
    for s in storico:
        righe.append(
            f"- Titolo: {s['titolo']!r} | Pilastro: {s['pilastro_editoriale']} | "
            f"Contesto: {s['contesto_trigger']} | Tecnica: {s['tecnica_usata'] or '(non registrata)'} | "
            f"Tema: {s['tema_centrale'] or '(non registrato)'}"
        )
    return "\n".join(righe)


def _normalizza_parola(p: str) -> str:
    return re.sub(r"[^a-zà-ù]", "", p.lower())


def _temi_simili(tema_a: str, tema_b: str) -> bool:
    """Confronto lessicale per radice comune (primi 6 caratteri, o parola
    intera se più corta) — cattura varianti grammaticali dirette
    ("silenzio"/"silenzioso", "temperatura emotiva"/"termostato emotivo"
    sulla parola condivisa "emotivo/emotiva", verificato su generazioni
    reali). NON è un confronto semantico completo: due temi sinonimi ma
    lessicalmente scollegati (es. "manutenzione" vs "sala macchine" — uno
    dei 2 casi reali che hanno motivato questo fix) non vengono
    intercettati se il modello sceglie parole del tutto diverse per lo
    stesso concetto. Il documento sorgente cita esplicitamente anche
    "sinonimo", non solo "variante grammaticale" — coprirlo per intero
    richiederebbe un confronto a embedding (stesso pattern già in uso per
    i tag piace/detesta, v. services/tag_matching.py); non implementato
    qui, segnalato come scelta da confermare esplicitamente."""
    parole_a = [_normalizza_parola(p) for p in tema_a.split()]
    parole_b = [_normalizza_parola(p) for p in tema_b.split()]
    for pa in parole_a:
        for pb in parole_b:
            if not pa or not pb:
                continue
            radice = min(len(pa), len(pb), 6)
            if radice >= 4 and pa[:radice] == pb[:radice]:
                return True
    return False


def _genera_candidato(storico: list[dict]) -> dict:
    contenuto_utente = (
        "## Storico delle ultime pillole generate (evita di ripeterle)\n"
        f"{_storico_a_testo(storico)}\n\n"
        "## Cosa evitare rispetto allo storico\n"
        "- Non usare la stessa tecnica delle ultime 2 pillole.\n"
        "- Non toccare lo stesso pilastro delle ultime 2, se possibile bilancia "
        "verso il pilastro meno rappresentato nello storico.\n"
        "- Se un dominio di metafora è già stato usato di recente, scegline uno diverso.\n"
        "- Non aprire con una struttura di frase simile a nessuna delle ultime 3.\n"
        "- IMPORTANTE: il tema/immagine centrale non deve coincidere (nemmeno come "
        "variante grammaticale, es. 'silenzio'/'silenzioso') con quello di NESSUNA "
        "delle pillole nello storico sopra, non solo le ultime 2.\n\n"
        "Genera ora una nuova pillola, in formato JSON come da istruzioni."
    )
    # Temperatura alta rispetto agli estrattori/scorer di llm_pipeline.py
    # (~0.15) — qui il problema principale è la monotonia su decine di
    # generazioni automatiche senza curatela umana, non la consistenza di
    # un giudizio; serve più varietà, non meno.
    return _chiama_json(PROMPT_SISTEMA, contenuto_utente, temperature=0.9)


def _valida(candidato: dict, storico: list[dict]) -> str | None:
    """Ritorna None se il candidato passa tutti i controlli (§3 del
    documento), altrimenti una stringa col motivo dello scarto."""
    for campo in ("titolo", "testo", "titolo_en", "testo_en", "pilastro", "contesto", "tecnica_usata", "tema_centrale"):
        if not candidato.get(campo):
            return f"campo mancante: {campo}"
    if candidato["pilastro"] not in PILASTRO_DB:
        return f"pilastro non valido: {candidato['pilastro']!r}"
    if candidato["contesto"] != "attesa_generale":
        return f"contesto non valido per questa generazione: {candidato['contesto']!r}"
    if candidato["tecnica_usata"] not in TECNICHE:
        return f"tecnica_usata non valida: {candidato['tecnica_usata']!r}"

    n_parole = len(candidato["testo"].split())
    if not (30 <= n_parole <= 90):
        return f"lunghezza fuori range: {n_parole} parole"

    n_parole_en = len(candidato["testo_en"].split())
    if not (30 <= n_parole_en <= 90):
        return f"lunghezza (EN) fuori range: {n_parole_en} parole"

    testo_normalizzato = candidato["testo"].strip().lower()
    for prefisso in FRASI_VIETATE_PREFISSO:
        if testo_normalizzato.startswith(prefisso):
            return f"apertura vietata: {prefisso!r}"

    ultimi_2 = storico[:2]
    tecniche_ultimi_2 = [s["tecnica_usata"] for s in ultimi_2 if s["tecnica_usata"]]
    if candidato["tecnica_usata"] in tecniche_ultimi_2:
        return f"tecnica ripetuta rispetto alle ultime 2: {candidato['tecnica_usata']!r}"

    pilastro_candidato_db = PILASTRO_DB[candidato["pilastro"]]
    pilastri_ultimi_2 = [s["pilastro_editoriale"] for s in ultimi_2]
    if pilastro_candidato_db in pilastri_ultimi_2:
        conteggi = Counter(s["pilastro_editoriale"] for s in storico)
        conteggio_candidato = conteggi.get(pilastro_candidato_db, 0)
        meno_rappresentati = [p for p in PILASTRI_CANONICI if conteggi.get(p, 0) < conteggio_candidato]
        if meno_rappresentati:
            return f"pilastro ripetuto rispetto alle ultime 2, con alternative meno rappresentate disponibili: {meno_rappresentati}"

    # Tema centrale: finestra più ampia delle ultime 2 (tutto lo storico
    # caricato, fino a 8-10 — v. _carica_storico) perché un tema può
    # ripetersi anche a distanza di più pillole, non solo consecutivamente.
    for s in storico:
        if s["tema_centrale"] and _temi_simili(candidato["tema_centrale"], s["tema_centrale"]):
            return f"tema centrale ripetuto rispetto allo storico: {candidato['tema_centrale']!r} ~ {s['tema_centrale']!r}"

    return None


def genera_pillola_del_giorno(cur) -> dict:
    """Genera UNA pillola (contesto fisso 'Attesa generale') con fino a
    MAX_TENTATIVI tentativi, scartando quelle che violano i controlli
    automatici (§3 — sostituiscono la revisione umana per l'MVP). Logga
    SEMPRE l'esito in pillole_generazione_log — pubblicata o fallita —
    incluso il dettaglio degli scarti, per accorgersi nel tempo se il
    numero medio di tentativi sale (segnale che il modello fatica sempre
    di più a rispettare i vincoli con uno storico che cresce)."""
    storico = _carica_storico(cur)
    scarti = []
    for tentativo in range(1, MAX_TENTATIVI + 1):
        try:
            candidato = _genera_candidato(storico)
        except Exception as e:
            scarti.append({"tentativo": tentativo, "motivo": f"errore_llm_o_json: {e}"})
            continue

        motivo_scarto = _valida(candidato, storico)
        if motivo_scarto:
            scarti.append({"tentativo": tentativo, "motivo": motivo_scarto, "candidato": candidato})
            continue

        cur.execute("""
            INSERT INTO pillole_libreria (titolo, testo, titolo_en, testo_en, pilastro_editoriale, contesto_trigger, tecnica_usata, tema_centrale)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING pillola_id
        """, (candidato["titolo"], candidato["testo"], candidato["titolo_en"], candidato["testo_en"],
              PILASTRO_DB[candidato["pilastro"]], CONTESTO_DB[candidato["contesto"]],
              candidato["tecnica_usata"], candidato["tema_centrale"]))
        pillola_id = cur.fetchone()["pillola_id"]
        cur.execute("""
            INSERT INTO pillole_generazione_log (pillola_id, tentativi, esito, dettaglio_scarti)
            VALUES (%s, %s, 'pubblicata', %s::jsonb)
        """, (str(pillola_id), tentativo, json.dumps(scarti)))
        return {"pubblicata": True, "pillola_id": str(pillola_id), "titolo": candidato["titolo"], "tentativi": tentativo}

    # Tutti i tentativi falliti — alert per revisione manuale (§3), mai
    # pubblicare un contenuto che ha fallito i controlli solo per "non
    # saltare il ciclo".
    print(f"[ALERT] generazione pillola del giorno fallita dopo {MAX_TENTATIVI} tentativi — revisione manuale necessaria. Dettaglio: {scarti}")
    cur.execute("""
        INSERT INTO pillole_generazione_log (pillola_id, tentativi, esito, dettaglio_scarti)
        VALUES (NULL, %s, 'fallita_tutti_tentativi', %s::jsonb)
    """, (MAX_TENTATIVI, json.dumps(scarti)))
    return {"pubblicata": False, "tentativi": MAX_TENTATIVI, "scarti": scarti}
