# Ainima — Chat-Intervista EQ Score (v1)
### Bozza di lavoro — a cura dello psicologo del progetto

---

## 1. Obiettivo e vincoli di design

**Obiettivo:** produrre `score_maturita_emotiva` (0.0-1.0), `stile_attaccamento` (Sicuro/Ansioso/Evitante/Disorganizzato) e un set di indicatori linguistici, partendo da una conversazione libera — non da un questionario.

**Obiettivo aggiuntivo (cross-validazione):** la chat non serve solo a raccogliere nuovo materiale, ma anche a **verificare la coerenza tra ciò che la persona ha dichiarato nel test Big Five e ciò che emerge nel racconto libero**. È una pratica psicometrica standard: nessun test scritto è immune dalla desiderabilità sociale (la tendenza, spesso inconsapevole, a rispondere come si vorrebbe essere piuttosto che come si è davvero), e un'incongruenza tra test e narrazione è essa stessa un dato prezioso — non un errore da ignorare.

**Vincoli approvati:**
- Conduzione: conversazione libera, follow-up generati dinamicamente dall'IA in tempo reale (non uno script fisso).
- Lunghezza: 5-7 scambi totali, ~10 minuti. Budget stretto → ogni turno deve avere uno scopo preciso.
- Output: l'utente riceve un report personale visibile ("La tua Prontezza Relazionale").

Con un budget così corto, la scelta architetturale chiave è: **non fare 2-3 domande fisse per ognuna delle 3 aree** (passato sentimentale, gestione conflitti, partner ideale) — non ci sta. Serve invece **un'unica domanda-ancora per area (3 in totale) + un budget flessibile di 2-4 follow-up dinamici** che l'IA spende dove serve davvero, cioè dove la prima risposta è superficiale, difensiva o incoerente.

**Nuovo input necessario:** prima di iniziare, l'IA intervistatrice deve ricevere in contesto i punteggi Big Five già calcolati per quell'utente (in particolare le facet più estreme, non l'intero test) — non per citarli mai all'utente, ma per riconoscere in tempo reale se il racconto libero conferma o contraddice quanto dichiarato nel test scritto.

---

## 2. Architettura conversazionale

```
Turno 1 → ANCORA: Passato sentimentale
Turno 2 → [Follow-up dinamico SE necessario] oppure passa oltre
Turno 3 → ANCORA: Gestione dei conflitti
Turno 4 → [Follow-up dinamico SE necessario] oppure passa oltre
Turno 5 → ANCORA: Partner ideale / proiezione futura
Turno 6-7 → [Follow-up dinamico residuo, se il budget lo consente]
```

Il "motore" che decide se spendere un follow-up non è casuale: si attiva secondo **trigger clinici precisi**, non secondo l'umore della conversazione.

### Trigger che attivano un follow-up (uno o più insieme):

| Trigger | Cosa indica | Esempio di risposta che lo attiva |
|---|---|---|
| **Attribuzione unilaterale** | Racconto "in bianco e nero", colpa 100% all'altro | "È finita perché lui/lei era tossico/a" |
| **Risposta troppo breve/evasiva** | Possibile evitamento o disagio col tema | Una frase secca, nessun dettaglio |
| **Linguaggio assoluto** | Rigidità cognitiva, generalizzazione | "Sempre", "mai", "tutti/e gli uomini/le donne" |
| **Incoerenza interna** | Ciò che dice non torna con ciò che ha appena detto | Si contraddice tra due frasi vicine |
| **Assenza di introspezione** | Nessun accenno al proprio ruolo/vissuto interno | Solo fatti esterni, zero emozioni proprie |
| **Incongruenza col test Big Five** | Il racconto contraddice una facet estrema dichiarata nel test | Test: Nevroticismo molto basso ("gestisco tutto con calma") → Racconto: forte ansia da abbandono nella storia sentimentale |

Se **nessun trigger** si attiva (la risposta è già riflessiva, bilanciata, con un minimo di autoconsapevolezza, e coerente col test), l'IA **non insiste** e passa all'area successiva — questo è ciò che tiene la conversazione dentro i 5-7 scambi anche con utenti già emotivamente maturi, che altrimenti verrebbero "interrogati" inutilmente.

**Priorità tra trigger:** se in uno stesso turno si attivano più segnali insieme (es. sia "attribuzione unilaterale" sia "incongruenza col test"), il trigger di incongruenza test-intervista ha la precedenza — non perché sia "più grave", ma perché il suo valore informativo per la qualità del dato complessivo è più alto: non riguarda solo quell'episodio, ma la affidabilità dell'intero test già raccolto.

**Principio importante:** un'incongruenza rilevata NON equivale a una menzogna. Se l'utente offre una spiegazione plausibile (es. "ho letto male quella domanda del test"), l'incongruenza va neutralizzata, non penalizzata — il dettaglio di come questo viene classificato e trattato a valle è nel documento dei prompt tecnici (Prompt 2, sezione incongruenze).

---

## 3. Le 3 domande-ancora

### Area 1 — Passato sentimentale
*Alimenta: Autoconsapevolezza + Responsabilità relazionale*

**Ancora:**
> "Raccontami della tua ultima relazione importante: com'era, e cosa pensi abbia contribuito alla fine?"

**Logica del follow-up dinamico (se scatta un trigger):**
- Se attribuzione unilaterale → *"Capisco. E tu, guardando indietro, c'è qualcosa che avresti fatto diversamente?"*
- Se risposta troppo breve → *"Cosa ricordi di come ti sei sentito/a nei mesi dopo la fine?"*

### Area 2 — Gestione dei conflitti
*Alimenta: Autoregolazione + Empatia*

**Ancora:**
> "Pensa a un disaccordo importante avuto con un partner. Cosa è successo, e come hai reagito nel momento più teso?"

**Logica del follow-up dinamico:**
- Se emerge solo la propria reazione, mai quella dell'altro → *"E secondo te, lui/lei come ha vissuto quel momento?"*
- Se linguaggio assoluto/rigido → *"È successo altre volte in modo simile, o è stato un episodio isolato?"*

### Area 3 — Partner ideale / proiezione futura
*Alimenta: Valori + coerenza tra bisogni dichiarati e bisogni reali*

**Ancora:**
> "Se dovessi descrivere la persona giusta per te non con aggettivi, ma con una situazione concreta di vita quotidiana insieme — che immagine ti viene in mente?"

*(Nota: la scelta di chiedere una "scena" invece di aggettivi è intenzionale — riduce la lista da catalogo, tipica del dating online, e produce materiale linguistico molto più ricco da analizzare.)*

**Logica del follow-up dinamico:**
- Se la risposta è solo una lista di qualità astratte ("gentile, intelligente, divertente") → *"Prova a immaginare una giornata qualsiasi tra tre anni, insieme a questa persona: cosa state facendo?"*
- Se emergono aspettative molto rigide/dealbreaker → *"Cosa succederebbe secondo te se qualcosa di importante non coincidesse esattamente con questa immagine?"*

---

## 4. Cosa estrarre dal testo: doppio livello di analisi

Per restare robusti (e non dipendere da un solo giudizio automatico), l'algoritmo dovrebbe combinare **due livelli** di analisi sullo stesso transcript:

### Livello A — Scoring semantico via LLM (rubric-based)

Un passaggio dedicato in cui un modello linguistico valuta il transcript rispetto a una rubrica esplicita — non "che ne pensi di questa persona" in modo libero, ma un punteggio 0-1 per ciascuno dei 4 pilastri già definiti, con criteri scritti:

| Pilastro | Cosa cerca il rubric-scorer |
|---|---|
| Autoconsapevolezza | La persona nomina proprie emozioni/pattern, non solo fatti esterni? |
| Autoregolazione | Nel racconto di conflitto, c'è una pausa tra stimolo e reazione, o escalation immediata? |
| Empatia | La prospettiva dell'altro viene mai nominata spontaneamente? |
| Responsabilità relazionale | C'è ammissione di un proprio contributo, anche minimo, senza essere sollecitata? |

`score_maturita_emotiva` = media pesata dei 4 pilastri (pesi calibrabili dopo il pilot).

### Livello B — Indicatori linguistici (stile LIWC, quantitativo)

Feature calcolabili indipendentemente dal giudizio semantico, utili sia come segnale autonomo sia come controllo di coerenza rispetto al Livello A:

| Feature linguistica | Cosa segnala |
|---|---|
| Rapporto pronomi "Io" vs "Noi/Lui/Lei" | Focus egocentrico vs relazionale |
| Densità di parole assolute ("sempre", "mai", "tutti") | Rigidità cognitiva |
| Presenza di lessico emotivo specifico (non solo "bene/male" ma "deluso", "in colpa", "sollevato/a") | Granularità emotiva — un marcatore forte di maturità |
| Domande spontanee poste durante la chat verso l'IA/il tema | Curiosità, apertura al confronto |
| Lunghezza e struttura delle frasi su temi emotivi vs neutri | Evitamento tematico (frasi che si accorciano bruscamente sul tema doloroso) |

### Inferenza dello stile di attaccamento

Non è un'area a sé nella conversazione: si deduce trasversalmente dai pattern nelle 3 aree, secondo la mappa già stabilita nella fase precedente del progetto:

| Pattern osservato nel transcript | Stile inferito |
|---|---|
| Racconto bilanciato, ammette il proprio ruolo, non drammatizza né minimizza | Sicuro |
| Linguaggio di paura dell'abbandono, bisogno di conferme, gelosia narrata come "normale" | Ansioso |
| Minimizza l'intensità emotiva propria e altrui, chiude presto il discorso su temi intimi | Evitante |
| Racconto incoerente, altalenante tra estremi opposti nello stesso turno | Disorganizzato |

Questa classificazione va trattata come **probabilistica**, non come etichetta rigida (es. `{sicuro: 0.6, ansioso: 0.3, evitante: 0.1}`), da semplificare in un'unica etichetta prevalente solo per la UI/DB.

---

## 5. Il report visibile all'utente: "La tua Prontezza Relazionale"

Punto delicato dal punto di vista etico e di prodotto: l'utente **non deve mai vedere** un'etichetta clinica cruda ("Nevroticismo alto", "Attaccamento ansioso", "Maturità emotiva: 0.4"). Sarebbe non solo scortese, ma clinicamente scorretto — nessuno strumento di questo tipo ha valore diagnostico, e presentarlo così rischia di ferire o etichettare ingiustamente una persona sulla base di una chat di 10 minuti.

Il report deve essere:
- **Orientato ai punti di forza**, non ai deficit.
- **Descrittivo, non giudicante** — mai un voto secco.
- **Propositivo**: ogni osservazione porta a uno spunto di crescita, coerente con la logica "newsletter/contenuti durante il mese di attesa" già definita nel progetto.

**Esempio di tono (non testo definitivo, solo per calibrare il registro):**

> *"Dal modo in cui racconti le tue esperienze emerge una persona che riflette con onestà su ciò che ha vissuto. Un'area su cui potresti lavorare: nei momenti di tensione, prova a nominare anche il punto di vista dell'altra persona — è un piccolo gesto che spesso fa la differenza più grande in una coppia."*

Internamente, dietro questo report, restano i punteggi numerici veri (`score_maturita_emotiva`, `stile_attaccamento`, i 4 sotto-punteggi) che alimentano l'algoritmo di matching — ma quelli non escono mai in forma di numero verso l'utente.

---

## 6. Nuovi campi DB derivati da questa fase

Ad integrazione dei campi già definiti (`score_maturita_emotiva`, `stile_attaccamento`):

- `eq_pilastro_autoconsapevolezza` (Float 0-1)
- `eq_pilastro_autoregolazione` (Float 0-1)
- `eq_pilastro_empatia` (Float 0-1)
- `eq_pilastro_responsabilita` (Float 0-1)
- `attaccamento_probabilita` (JSON: distribuzione probabilistica sui 4 stili)
- `red_flags_rilevati` (Array/Enum: es. `attribuzione_unilaterale_ricorrente`, `linguaggio_assoluto`, `evitamento_tematico`) — per uso interno, mai esposto
- `incongruenze_test_intervista` (Array di oggetti: `{facet, punteggio_test, evidenza_intervista}`) — ogni incongruenza rilevata tra Big Five e narrazione, per uso interno; utile sia per pesare meno quella specifica facet nel matching, sia per ricalibrare il test stesso nel tempo se un pattern di incongruenza si ripete su molti utenti
- `transcript_id` (FK) — riferimento alla conversazione grezza, per audit/ricalibrazione futura del rubric-scorer
- `chat_eq_completata_il` (Timestamp)

---

## 7. Nota di cautela metodologica

Un'intervista di 10 minuti non è una valutazione clinica e non va trattata come tale — nemmeno internamente. Ti consiglio due accorgimenti prima del lancio:

1. **Calibrazione umana iniziale:** su un campione pilota (30-50 conversazioni), far rileggere i transcript a un professionista reale (psicologo/counselor) e confrontare il suo giudizio con quello del rubric-scorer, per tarare pesi e soglie prima di fidarsi ciecamente dell'output automatico.
2. **Nessuna decisione binaria basata solo su questo score.** Va sempre usato come *uno* dei segnali nel matching (insieme a Big Five e criteri dichiarati), mai come filtro di esclusione secco — il rischio di falsi negativi in una singola chat breve è reale.

## Prossimi passi

1. Validare insieme la formulazione esatta delle 3 domande-ancora (tono, lunghezza, eventuale adattamento per il mercato arabo/internazionale).

*(Il prompt di sistema dell'IA intervistatrice e il prompt del rubric-scorer sono definiti in `Ainima_Prompt_Intervistatrice_RubricScorer_v1.md`. Il template del report utente è definito in `Ainima_Matching_Semantico_Report_v1.md`, Prompt 5.)*
