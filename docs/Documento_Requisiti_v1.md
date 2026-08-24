# Documento dei Requisiti — v1.0
## Progetto: Agenzia Matrimoniale Low-Cost basata su IA

**Stato:** Bozza v1 — da validare con il team prima dello sviluppo
**Data:** 12 agosto 2026

---

## 1. Visione e obiettivi

Piattaforma web di matchmaking matrimoniale **mass market e low-cost** — la prima nel suo genere a portare un modello economico accessibile in un settore tradizionalmente costoso (agenzie boutique) o superficiale (app di dating generaliste).

- **Lancio:** Milano, con lingue **Italiano e Inglese** fin dal Day 1.
- **Posizionamento:** matrimonio/relazione seria, non dating casuale.
- **Differenziatore:** matching automatico guidato da LLM esterno + modello di pricing a basso attrito (pay-per-match invece di abbonamenti costosi).
- **Espansione futura:** compatibilità concettuale con mercati arabi/GCC (nome e comunicazione neutrali), non nello scope dell'MVP.

---

## 2. Panorama competitivo

Dall'analisi preliminare condotta emerge che il mercato del matching relazionale si muove su uno **spettro a quattro dimensioni**, tra approccio psicometrico/deterministico e comportamentale/IA da un lato, e tra accessibilità di massa e filtro umano/status dall'altro:

| Categoria | Player di riferimento | Filosofia chiave |
|---|---|---|
| Psicometria tradizionale | eHarmony, EliteSingles | Algoritmi deterministici su test lunghi (Big Five); nessuna IA generativa nel matching |
| Comportamentale / ML | Hinge | Apprende dalle azioni reali dell'utente più che dalle preferenze dichiarate; IA generativa solo per spunti di conversazione |
| Sociale / dinamica di potere | Bumble | Regola d'interazione (iniziativa alla donna) invece di un algoritmo psicologico |
| Volume / geo-based | Tinder | Accessibilità di massa, nessun filtro qualitativo profondo |
| Network esclusivo | Raya | Accesso su invito, selezione umana, nessun test né algoritmo aperto |
| Culturale/religioso | Muzz, JSwipe | Filtri rigidi su fede e valori familiari, priorità alla comunità sull'individuo |
| Boutique offline | Parship, Berkeley International | Consulenti umani, verifica background, riservatezza totale, nessuna app |

**Posizionamento del progetto rispetto ai competitor:** l'obiettivo dichiarato è colmare uno spazio oggi scoperto — un servizio **mass market e low-cost** ma orientato al matrimonio/relazione seria (non al volume puro alla Tinder), con matching **automatico via LLM** (a differenza della psicometria deterministica di eHarmony/EliteSingles) ma **senza i costi di un'agenzia boutique** (Parship, Berkeley International) né la barriera dell'invito esclusivo (Raya). Il vincolo di un solo abbinamento al mese e l'assenza di chat interna rafforzano il posizionamento "serio, a basso attrito, non da scrolling compulsivo".

---

## 3. Attori del sistema

| Attore | Descrizione |
|---|---|
| **Utente** | Persona iscritta in cerca di un partner |
| **Sistema di Matching** | Componente automatico (algoritmo + LLM esterno) che genera le proposte |
| **Amministratore/Staff** | Gestisce il pannello di back-office (verifiche, dispute, monitoraggio) |
| **Gateway di pagamento** | Servizio esterno per pre-autorizzazioni e addebiti |
| **Servizio Email/OTP** | Servizio esterno per invio codici OTP via email (autenticazione) |

---

## 4. Requisiti funzionali

### 4.1 Registrazione e onboarding
- RF-01: L'utente si registra con email, password, nome, cognome, data di nascita.
- RF-02: **Autenticazione via email OTP.** L'utente si autentica tramite un codice OTP inviato via email (no password permanente da ricordare, o in alternativa OTP come fattore aggiuntivo alla password — da definire in fase tecnica). Questo sostituisce, per questa prima fase, la verifica del numero di telefono via SMS.
- RF-02b: **Numero di telefono opzionale.** L'utente può facoltativamente inserire un numero di telefono in fase di registrazione, ma **non è un dato obbligatorio né verificato in questa fase**. Il contatto principale scambiato dopo un match confermato è l'**email** (già verificata via OTP, v. RF-02) — v. RF-20/RF-21. Il telefono, se presente, viene comunque incluso nella vCard come informazione aggiuntiva ma resta un dato secondario e non affidabile ai fini della verifica identità.
- RF-03: L'utente registra un metodo di pagamento (carta di credito/debito).
- RF-04: Il sistema esegue una **pre-autorizzazione** sulla carta (blocco temporaneo di un importo simbolico, es. 1€) per verificarne la validità; l'importo viene **rilasciato automaticamente** e non addebitato. Nessun documento d'identità è richiesto in questa fase.
- RF-05: Lo stato civile è dichiarato dall'utente stesso (**autodichiarazione**, nessuna verifica attiva in questa fase).
- RF-06: Completata la verifica carta, l'utente compila il **profilo anagrafico e fisico** (v. modello dati §7).
- RF-06b: **Moderazione automatica dei contenuti fotografici.** Ogni immagine caricata dall'utente — sia la **foto profilo** che l'eventuale **foto del "partner ideale"** (v. RF-08b) — viene analizzata automaticamente da un servizio di rilevamento contenuti per adulti/pornografici al momento del caricamento. Se un'immagine viene segnalata come potenzialmente inappropriata, l'account passa (o resta) nello stato **"In attesa — verifica moderazione"** (v. §7.1) e **non può completare l'iscrizione né entrare nel pool di matching finché un operatore umano non ha revisionato ed esplicitamente approvato o rifiutato il contenuto** dal pannello di amministrazione (v. RF-25c). L'utente riceve una notifica generica sullo stato di verifica in corso, senza dettagli tecnici sul motivo del blocco.
- RF-07: L'utente compila il **test di profilazione psicometrico** (Big Five + eventuali dimensioni aggiuntive, es. stile di attaccamento tramite scale validate a scelta forzata — v. nota in §10). *(Nota: le domande specifiche del test sono da definire in una sessione ad hoc dedicata — fuori scope di questo documento, ma il sistema deve prevedere una struttura dati flessibile per accoglierle, v. §7.5)*
- RF-07b: L'utente compila due **campi descrittivi liberi**: "Descrivi te stesso" e "Descrivi il tuo partner ideale" (testo libero, lunghezza massima da definire). Questi campi **non alimentano direttamente lo scoring di compatibilità** (che resta basato su ML/psicometria, v. RF-10): vengono usati esclusivamente come input per la generazione IA di contenuti testuali leggibili dall'utente (sintesi caratteriale, report di abbinamento — v. RNF-11). *Nota di processo: si è scelto di non implementare un colloquio conversazionale con un LLM (originariamente previsto per estrarre stile di attaccamento ed EQ) per ridurre la superficie di attacco a prompt injection su dati sensibili; l'opzione resta comunque valutabile come sviluppo futuro (v. §9).*
- RF-08: L'utente definisce i **criteri di ricerca** del partner ideale, distinti in due categorie con peso diverso nell'algoritmo (v. §7.4):
  - **Criteri non negoziabili (dealbreaker)**: condizioni che devono essere soddisfatte per considerare un profilo compatibile — es. genere/orientamento sessuale cercato, range di età, presenza/desiderio di figli, range di distanza massima. Un profilo che non rispetta anche un solo criterio non negoziabile viene **escluso a priori** dal pool di match, indipendentemente dallo score di compatibilità.
  - **Criteri graditi (preferenze soft)**: caratteristiche desiderabili ma non escludenti — es. titolo di studio, corporatura, abitudini (fumo/alcol), interessi. Il loro grado di corrispondenza **contribuisce allo score di compatibilità** ma non esclude un profilo se non soddisfatto.
- RF-08b: L'utente può caricare una **foto del proprio "partner ideale"** (immagine di riferimento estetico, non un profilo reale). Il campo è opzionale in questa fase e distinto dalla foto profilo dell'utente stesso (v. §7.2). Questa immagine alimenta la fase di analisi visiva descritta in RF-11b.
- RF-09: L'account resta in stato "In attesa" finché onboarding (email verificata via OTP + carta verificata + profilo minimo, telefono opzionale + test) non è completo **e nessuna immagine caricata risulta in attesa di verifica moderazione (v. RF-06b)**; solo allora passa ad "Attivo" ed entra nel pool di matching.

### 4.2 Matching
- RF-10: Il matching è **completamente automatico** e basato su **Machine Learning/embedding deterministici** (non su ragionamento conversazionale di un LLM generativo): punteggio di compatibilità calcolato da similarity search su vettori (Big Five + eventuali dimensioni aggiuntive del test psicometrico, embedding testuale dei campi descrittivi RF-07b) combinato con filtri deterministici sui criteri "non negoziabili" (età, distanza, genere/orientamento cercato, figli, ecc.). Un modello di embedding può essere usato per convertire il testo in vettori, ma non genera testo né prende decisioni discorsive: il suo output è unicamente numerico/vettoriale — v. RNF-11 per il vincolo di separazione tra questo strato e quello generativo.
- RF-11: Il sistema genera **una proposta di abbinamento al mese** per utente attivo (cadenza configurabile lato admin per iterazioni future). La generazione avviene in due fasi, descritte in RF-11a e RF-11b.
- RF-11a: **Fase 1 — Shortlist di affinità.** Applicati i filtri sui criteri non negoziabili e calcolato lo score di compatibilità (criteri graditi + psicometria), il sistema seleziona una **shortlist di N profili candidati** (parametro configurabile dal pannello admin, default 5, valore alternativo tipico 10 — v. RF-25b) con lo score più alto.
- RF-11b: **Fase 2 — Selezione per somiglianza visiva.** Se l'utente ha caricato una foto del "partner ideale" (RF-08b), il sistema esegue un'**analisi di somiglianza visiva** tra tale immagine e le foto profilo dei candidati della shortlist, e seleziona come proposta finale il profilo **visivamente più simile**. Se l'utente non ha caricato la foto del partner ideale, la proposta finale è semplicemente il candidato con lo score di compatibilità più alto della shortlist (fallback a RF-11a).
- RF-12: La proposta è mostrata **in forma anonima** (nessun nome/cognome/contatto), con foto profilo, caratteristiche principali e sintesi dell'analisi caratteriale generata dall'algoritmo/LLM.
- RF-13: Ogni utente può **accettare** o **rifiutare** la proposta.
- RF-14: L'abbinamento diventa "ufficiale" solo se **entrambe** le parti accettano entro una finestra temporale definita (es. 7 giorni).
- RF-15: Se una delle due parti rifiuta, l'abbinamento decade; il sistema pianifica una nuova proposta al ciclo successivo (non è previsto "ripescaggio" immediato nell'MVP).
- RF-16: Non è prevista **nessuna importazione massiva** di profili/anagrafiche esterne nell'MVP (funzionalità rimandata a fase 2). Il pool iniziale si popola solo tramite registrazioni organiche.

### 4.3 Pagamento e conferma match
- RF-17: Quando entrambe le parti accettano, il sistema **addebita la fee di match confermato** a entrambi (tramite pre-autorizzazione → cattura, per evitare l'addebito "a vuoto" discusso in fase di analisi).
- RF-18: È prevista **un'unica offerta di pricing**, senza differenziazione geografica nell'MVP (pricing dinamico rimandato a fase successiva).
- RF-19: Il modello di abbonamento (Basic/Premium/eventuali livelli superiori) è gestito tramite un **singolo campo estendibile** nel profilo utente (v. §7.1), attivabile dal lancio ma senza logiche di differenziazione funzionale complesse nell'MVP — permette di aggiungere tier futuri senza modifiche strutturali al DB.

### 4.4 Scambio contatto e chiusura task
- RF-20: A seguito della **conferma e del pagamento di entrambe le parti**, il sistema sblocca lo scambio dei contatti tra i due utenti. Il **contatto principale è l'indirizzo email** (già verificato via OTP in fase di autenticazione, v. RF-02); il numero di telefono, se l'utente lo ha inserito (RF-02b), viene incluso come informazione aggiuntiva ma non verificata.
- RF-21: I contatti vengono condivisi ad entrambi gli utenti sotto forma di **vCard scaricabile**, con azione nativa "Aggiungi ai contatti" (nome del match come da profilo, email verificata come campo principale, telefono se disponibile). Prima della conferma finale dello scambio, la UI mostra una **nota informativa sulla privacy**: l'indirizzo email verrà visibile all'altra persona, e si consiglia di usarne uno che l'utente non colleghi ad altri profili online personali/professionali (per limitare il rischio che l'altra parte risalga a informazioni aggiuntive tramite ricerche sull'indirizzo).
- RF-22: Al completamento dello scambio contatto, il "task" di abbinamento si considera **concluso con successo**. Non è prevista alcuna funzionalità di chat interna alla piattaforma — la conversazione prosegue sui canali privati degli utenti (es. telefono/WhatsApp).
- RF-22b: La GUI utente espone una sezione **"Rubrica"** con l'elenco degli abbinamenti conclusi (nome, foto, data del match, eventuale stato del feedback lasciato). Da qui l'utente può riscaricare la vCard del contatto in qualsiasi momento, senza dover ripetere lo scambio iniziale.

### 4.5 Feedback e miglioramento continuo
- RF-23: Trascorsi **15 giorni** dalla chiusura del task, il sistema invia automaticamente una richiesta di feedback a entrambi gli utenti (es. via email/notifica in-app).
- RF-24: Il feedback raccolto (es. esito dell'incontro, qualità percepita della compatibilità) viene salvato e collegato al profilo per **affinare i criteri di matching successivi** dello stesso utente e, in prospettiva, ritarare i pesi dell'algoritmo.

### 4.6 Pannello di amministrazione
- RF-25: È previsto un **pannello di back-office** per lo staff, con funzionalità minime:
  - Ricerca/consultazione profili utente
  - Monitoraggio stato abbinamenti (proposti, accettati, rifiutati, confermati)
  - Gestione dispute/segnalazioni tra utenti
  - Visualizzazione metriche chiave (iscrizioni, tasso di conversione match, rapporto di genere nel pool utenti)
  - Gestione manuale dello stato account (sospensione, riattivazione)
- RF-25b: Il pannello espone un **parametro di configurazione** "dimensione shortlist per analisi visiva" (v. §7.8), modificabile dallo staff senza richiedere una nuova release del software, con valore di default impostato a 5.
- RF-25c: Il pannello include una **coda di moderazione contenuti**, che elenca le immagini segnalate dal sistema automatico (v. RF-06b) in attesa di revisione. Per ciascuna, l'operatore può: visualizzare l'immagine, **approvare** (l'account prosegue l'onboarding/torna Attivo) o **rifiutare** (l'utente viene invitato a ricaricare una nuova immagine conforme; l'account resta bloccato finché non lo fa). Ogni decisione viene tracciata con timestamp e operatore, per audit.
- RF-25d: Il pannello include una **coda di richieste di recupero accesso** (v. RF-26b/26c), che elenca le richieste in attesa con i dati identificativi forniti dall'utente affiancati a quelli del profilo esistente, per facilitare il confronto. L'operatore approva o rifiuta; ogni decisione è tracciata con timestamp e operatore, per audit.

### 4.7 Gestione dell'account e recupero accesso
- RF-26: **Cambio email da account autenticato (self-service).** Un utente loggato può richiedere la modifica del proprio indirizzo email dalla schermata "Modifica profilo". Il nuovo indirizzo deve essere verificato tramite OTP (stesso meccanismo di RF-02) prima di diventare effettivo. Al completamento, il vecchio indirizzo riceve una **email di notifica di sicurezza** che informa del cambiamento avvenuto (non richiede azione, è solo un avviso).
- RF-26b: **Richiesta di recupero accesso (utente bloccato fuori dalla vecchia email).** È disponibile un modulo pubblico, non autenticato, in cui l'utente dichiara: l'email con cui si era registrato (se la ricorda), l'email nuova a cui vuole passare, e alcuni **dati identificativi del profilo** utili alla verifica manuale (es. nome, cognome, data di nascita, città, ultime 4 cifre della carta usata per la pre-autorizzazione — mai il numero completo). La richiesta non concede alcun accesso automatico all'account.
- RF-26c: Ogni richiesta di recupero entra nella **coda di revisione umana** del pannello admin (v. RF-25d). Un operatore confronta i dati forniti con quelli del profilo esistente e **approva o rifiuta** la richiesta. Il rifiuto non fornisce dettagli specifici sul perché (per non aiutare un eventuale tentativo di furto d'identità a correggere il tiro).
- RF-26d: Se approvata, il sistema avvia il cambio email con un **periodo di sicurezza (grazia)** configurabile (default 48 ore, v. §7.8): viene inviata una notifica alla **vecchia** email (se ancora accessibile) con un link per **annullare** l'operazione, e alla **nuova** email un link per completarla con OTP. Se nessuno annulla entro la finestra, il cambio si conferma automaticamente e il nuovo indirizzo diventa l'email di login e di contatto.

### 4.8 Modifica profilo
- RF-27: L'utente può rivedere e aggiornare in qualsiasi momento i dati inseriti in onboarding (profilo fisico, socio-economico, criteri di ricerca, foto profilo, foto partner ideale). Le nuove foto caricate passano nuovamente dalla moderazione automatica (v. RF-06b).

---

## 5. Requisiti non funzionali

- RNF-01: **GDPR compliance** — il sistema tratta dati appartenenti a "categorie particolari" (art. 9 GDPR: orientamento sessuale, fede religiosa) e richiede pertanto **consenso esplicito e granulare** in fase di registrazione, con possibilità di revoca, esportazione e cancellazione dei dati (diritto all'oblio).
- RNF-02: I dati sensibili devono essere **cifrati at-rest** e l'accesso da parte dello staff deve essere tracciato (audit log) e limitato secondo il principio del minimo privilegio.
- RNF-03: **Localizzazione** — l'interfaccia deve supportare Italiano e Inglese fin dal lancio, con architettura pronta per aggiungere lingue (es. arabo) in futuro senza refactoring.
- RNF-04: **Scalabilità e portabilità** — l'infrastruttura di produzione deve essere facilmente migrabile tra provider cloud (evitare vendor lock-in stretto), robusta e sicura (v. §8).
- RNF-05: **Performance** — generazione batch mensile delle proposte di matching deve poter scalare a decine di migliaia di utenti attivi senza degrado significativo dei tempi di elaborazione.
- RNF-06: **Sicurezza pagamenti** — nessun dato di carta transita o è salvato su server proprietari (PCI-DSS compliance delegata al gateway di pagamento, es. tokenizzazione).
- RNF-07: **Affidabilità Email/OTP** — il servizio di invio OTP via email deve garantire consegna rapida e alta deliverability (attenzione a configurazione SPF/DKIM/DMARC per evitare finire in spam), su mercato IT ed EN/internazionale.
- RNF-08: **Equità dell'analisi visiva** — il modulo di similarity visiva (RF-11b) opera esclusivamente come criterio di ordinamento all'interno di una shortlist già filtrata su compatibilità caratteriale (RF-11a); non deve mai bypassare i criteri non negoziabili né sostituire lo score di compatibilità come criterio primario, per evitare che il matching si riduca a un giudizio puramente estetico.
- RNF-09: **Moderazione contenuti in tempo utile** — la scansione automatica di cui a RF-06b deve completarsi in pochi secondi dal caricamento, per non introdurre attriti percepibili nell'onboarding; solo le immagini effettivamente segnalate generano il blocco in attesa di revisione umana. L'accesso alle immagini in coda di moderazione (v. §7.9) è riservato allo staff autorizzato e tracciato come gli altri dati sensibili (v. RNF-02).
- RNF-10: **Sicurezza dell'account email-centrico** — poiché l'email è sia il fattore di login (RF-02) sia il contatto condiviso col match (RF-20/21), un accesso non autorizzato alla casella email dell'utente comprometterebbe entrambi gli aspetti. Il sistema deve quindi applicare rate limiting rigoroso sulla richiesta OTP, notificare l'utente via email ad ogni nuovo login da dispositivo non riconosciuto, e prevedere un meccanismo di autenticazione a due fattori come possibile hardening futuro (v. §10).
- RNF-11: **Separazione architetturale tra scoring ML e strato generativo IA (contenimento prompt injection).** L'uso di IA generativa nel sistema è limitato esclusivamente alla produzione di testo leggibile dall'utente (sintesi caratteriale, report "Prontezza Relazionale", spiegazione dell'abbinamento) a partire da dati **già calcolati** dal motore ML/psicometrico. In nessun caso l'output di un LLM generativo (incluso qualunque contenuto derivato dai campi liberi RF-07b) può scrivere, modificare o influenzare direttamente uno score di compatibilità, un campo `match_preferences`, o lo stato di un `match`. Questo vincolo va applicato a livello di codice (i moduli di scoring e i moduli di generazione testo devono essere componenti separati, con il secondo in sola lettura rispetto ai punteggi), non solo di prompt, in modo che un tentativo di prompt injection nei campi testuali possa al più degradare la qualità del report di un singolo utente, mai alterare il matching reale con altre persone.

---

## 6. Ambienti: test, collaudo e produzione

| | **Test (DB Actor)** | **Collaudo** | **Produzione** |
|---|---|---|---|
| Scopo | Sandbox locale per validare la logica di matching su anagrafiche fittizie (con foto profilo, foto partner ideale, foto "somiglianza") | Ambiente cloud pubblico con dati demo, usato per mostrare l'MVP e per collaudo funzionale prima del lancio reale | Dati reali degli utenti, dopo il lancio |
| Motore DB | MySQL o PostgreSQL (locale) | PostgreSQL gestito su Render (piano Free, con scadenza — v. nota sotto) | Da definire in fase di infrastruttura — **si raccomanda PostgreSQL** (v. §8), piano a pagamento con backup |
| Storage immagini | Locale/filesystem | Object Storage cloud S3-compatibile (Cloudflare R2) | Object Storage cloud (S3-compatibile), stesso servizio o equivalente scalato |
| Hosting backend/frontend | — (solo DB, nessuna app in esecuzione) | Render (backend) + Vercel (frontend) | Da definire, eventualmente stesso stack scalato o migrato |
| Stato attuale | Repository Git personale, ambiente locale | **In allestimento** — database Render creato (piano Free, scadenza 20 settembre 2026, da rinnovare/aggiornare se il collaudo prosegue oltre) | Da progettare |

Il DB Actor va considerato come **banco di prova per l'algoritmo di matching**, non come base dati definitiva: lo schema dovrà essere adattato al modello dati definito in §7 prima della migrazione verso l'ambiente di collaudo. Le foto "partner ideale" e "somiglianza" già presenti nel DB Actor confermano che il set di test è già predisposto per validare il flusso descritto in RF-11b.

L'ambiente di **collaudo** su Render/Vercel/R2 (piani gratuiti) serve a mostrare l'MVP e validare il funzionamento end-to-end con dati fittizi, ma **non va usato con dati reali di utenti**: non ha le garanzie di backup, durata e sicurezza necessarie per la produzione (v. §9, punti fuori scope). Il passaggio a un vero ambiente di produzione — con piani a pagamento, backup, e revisione di sicurezza — resta un passo separato, da affrontare quando il prodotto sarà pronto per il lancio reale.

---

## 7. Modello dati (schema logico di riferimento)

### 7.1 Identità e Account (`users`)
`user_id` (UUID, PK) · `nome` · `cognome` · `email` (unique) · `email_verificata` (bool) · `password_hash` (se previsto un fattore aggiuntivo oltre a OTP — da confermare in fase tecnica) · `telefono` (opzionale, non verificato — v. RF-02b) · `data_nascita` · `genere` · `orientamento_sessuale` · `stato_civile` (autodichiarato) · `ha_figli` · `stato_account` (Enum: In attesa, **In attesa - verifica moderazione**, Attivo, Sospeso, Chiuso) · `livello_abbonamento` (Enum estendibile, default `Free`) · `data_scadenza_abbonamento` · `metodo_pagamento_token` (riferimento tokenizzato al gateway, mai dati carta in chiaro) · `consenso_dati_sensibili` (bool + timestamp) · `data_creazione`

### 7.2 Profilo fisico (`physical_profile`)
`altezza_cm` · `peso_kg` (opzionale) · `corporatura` · `colore_capelli` · `colore_occhi` · `fumo` · `alcol` · `stile_vita_sport` · `foto_profilo_url` (Object Storage) · `foto_partner_ideale_url` (Object Storage, opzionale — v. RF-08b) · `embedding_visivo_partner_ideale` (Vector, calcolato una tantum al caricamento della foto, per efficienza in fase di matching — v. §8)

### 7.3 Profilo socio-economico (`socio_profile`)
`comune_residenza` · `coordinate_gps` · `titolo_studio` · `settore_occupazionale` · `fede_religiosa` · `importanza_religione`

### 7.4 Criteri di ricerca (`match_preferences`)

**Non negoziabili (dealbreaker — usati come filtro di esclusione, non come score):**
`pref_genere_cercato` · `pref_orientamento_compatibile` · `pref_eta_min/max` · `pref_distanza_max_km` · `pref_accetta_figli` (Sì/No/Indifferente) · `pref_desidera_figli_futuri` (Sì/No/Da valutare)

**Graditi (preferenze soft — contribuiscono allo score di compatibilità, non escludono):**
`pref_altezza_min/max` · `pref_stato_civile_accettato` · `pref_titolo_studio` · `pref_corporatura` · `pref_fumo` · `pref_alcol` · `pref_fede_religiosa` · `pref_importanza_religione`

*Nota implementativa:* i due gruppi vanno modellati come campi/tabelle distinti (es. `dealbreaker_criteria` e `soft_criteria`) in modo che il motore di matching possa applicare prima il filtro rigido sui dealbreaker e solo successivamente calcolare lo score pesato sui criteri graditi + score psicometrico (§7.5).

### 7.5 Test e scoring psicometrico (`psychometric_scores`)
`score_big5_*` (5 tratti, Float) · `score_maturita_emotiva` · `stile_attaccamento` (da popolare tramite scale validate a scelta forzata nel test strutturato, non tramite colloquio conversazionale — v. RF-07 e nota in §10) · `vettore_embedding_profilo` (Vector — richiede PostgreSQL + estensione `pgvector` per similarity search efficiente, calcolato dai campi descrittivi di §7.5b) · struttura dati aperta per accogliere le domande/risposte del test una volta definite nella sessione dedicata

### 7.5b Campi descrittivi liberi (`profile_narrative`)
`descrizione_te_stesso` (Text) · `descrizione_partner_ideale` (Text) · `data_ultima_modifica`. Alimentano esclusivamente lo strato generativo (report, sintesi — v. RNF-11) e il calcolo dell'embedding testuale in `vettore_embedding_profilo`; non sono mai passati direttamente a un LLM generativo insieme a istruzioni di sistema modificabili, per limitare la superficie di prompt injection (v. RF-07b).

### 7.6 Abbinamenti (`matches`)
`match_id` (PK) · `user_a_id` · `user_b_id` · `stato` (Enum: Proposto, Accettato_A, Accettato_B, Confermato, Rifiutato, Scaduto) · `data_proposta` · `data_scadenza_risposta` · `pagamento_a_stato` · `pagamento_b_stato` · `data_conferma` · `contatto_scambiato` (bool) · `shortlist_candidati` (riferimento ai profili valutati in RF-11a, per audit/tracciabilità della selezione) · `selezionato_per_somiglianza_visiva` (bool — indica se RF-11b ha influenzato la scelta finale)

### 7.7 Feedback (`match_feedback`)
`match_id` (FK) · `user_id` (FK) · `data_richiesta` (conferma + 15gg) · `data_risposta` · `esito` · `note_libere` · `usato_per_ritaratura` (bool)

### 7.8 Parametri di configurazione (`system_config`)
`chiave` (PK, es. `dimensione_shortlist_analisi_visiva`) · `valore` · `descrizione` · `data_ultima_modifica` · `modificato_da` (riferimento all'admin). Tabella generica chiave-valore editabile dal pannello admin (v. RF-25b), pensata per ospitare in futuro altri parametri di tuning dell'algoritmo (es. cadenza dei match, finestra di risposta) senza richiedere modifiche allo schema.

### 7.9 Moderazione contenuti (`content_moderation_log`)
`moderation_id` (PK) · `user_id` (FK) · `tipo_immagine` (Enum: Foto profilo, Foto partner ideale) · `immagine_url` · `esito_automatico` (Enum: OK, Sospetta, In errore) · `score_confidenza` (Float, output del servizio di rilevamento) · `data_scansione` · `esito_revisione_umana` (Enum: In attesa, Approvato, Rifiutato) · `revisionato_da` (riferimento all'admin) · `data_revisione`. Alimenta la coda di moderazione del pannello admin (RF-25c) e determina lo stato "In attesa - verifica moderazione" su `users` (v. §7.1).

### 7.10 Richieste di recupero accesso (`email_change_requests`)
`request_id` (PK) · `user_id` (FK, se identificabile) · `email_attuale_dichiarata` · `email_nuova_richiesta` · `dati_identificativi_forniti` (JSON: nome, cognome, data di nascita, città, ultime 4 cifre carta) · `origine` (Enum: Self-service da account autenticato, Modulo pubblico recupero accesso) · `stato` (Enum: In attesa revisione, Approvata, Rifiutata, In periodo di grazia, Completata, Annullata) · `revisionato_da` (riferimento all'admin, nullo per il self-service) · `data_richiesta` · `data_decisione` · `data_scadenza_grazia` · `token_annullamento` (per il link inviato alla vecchia email in RF-26d). Alimenta la coda di recupero accesso del pannello admin (RF-25d).

---

## 8. Proposta di stack tecnico (da validare col team)

Vista la richiesta di robustezza, sicurezza, scalabilità e **facile migrabilità**, la proposta è:

- **Backend:** **Python (FastAPI)** — scelta confermata. Ottima integrazione con SDK Python per API LLM/embedding, ecosistema maturo per data processing (numpy/pandas se servisse per il tuning dei pesi dell'algoritmo), performance async adeguate al carico previsto, facilmente containerizzabile.
- **Database:** **PostgreSQL** anziché MySQL — supporto nativo a JSON/JSONB (utile per le risposte flessibili del test psicometrico) e all'estensione **pgvector**, indispensabile per la similarity search sugli embedding testuali (RF-10) e visivi (RF-11b).
- **Matching (RF-10):** modello di **embedding testuale** (non generativo) per convertire test psicometrico + campi descrittivi liberi in vettori, confrontati via similarity search in pgvector; nessuna generazione di testo né "ragionamento" discorsivo in questo strato.
- **Strato generativo IA (RF-07b, report):** chiamate a un LLM generativo **isolate in un servizio/modulo dedicato**, separato dal motore di matching (v. RNF-11), usato solo per produrre testo leggibile (sintesi caratteriale, report di abbinamento) a partire da dati già calcolati; input utente (campi liberi) trattato come dato non fidato nel prompt (delimitazione esplicita, mai concatenato a istruzioni di sistema modificabili), output validato/filtrato prima di essere mostrato.
- **Analisi di somiglianza visiva (RF-11b):** modello di embedding immagini pre-addestrato (es. famiglia CLIP o equivalente) per convertire foto profilo e foto "partner ideale" in vettori confrontabili via cosine similarity in pgvector; l'embedding della foto partner ideale va calcolato una sola volta al caricamento (v. §7.2) per non appesantire il ciclo di matching mensile.
- **Moderazione contenuti (RF-06b):** servizio dedicato di rilevamento contenuti per adulti (es. le API di content-moderation dei provider cloud principali — AWS Rekognition, Google Cloud Vision SafeSearch, Azure Content Safety — o servizi specializzati terzi), invocato in modo sincrono/asincrono al momento dell'upload; il risultato alimenta la tabella `content_moderation_log` (v. §7.9) e la coda di revisione del pannello admin.
- **Storage immagini:** Object Storage compatibile S3 (es. Amazon S3, Cloudflare R2, Backblaze B2) — standard de facto, garantisce portabilità tra provider senza lock-in.
- **Infrastruttura:** containerizzazione Docker fin dal principio, per garantire **migrabilità** tra provider cloud (AWS, GCP, Azure, o hosting gestito tipo Render/Railway per un MVP più snello) senza riscritture.
- **Autenticazione/OTP:** servizio email transazionale con buon tier gratuito (es. Resend, Amazon SES, Postmark, SendGrid) per l'invio dei codici OTP via email; verifica telefonica via SMS **non prevista in questa fase** (v. RF-02b) — la voce resta come possibile evoluzione futura (es. Twilio Verify) se si deciderà di introdurre la verifica del numero in fase 2.
- **Pagamenti:** gateway con supporto a pre-autorizzazione/cattura differita (es. Stripe).
- **Frontend:** Web app responsive (framework React/Next.js), niente app nativa nell'MVP come da requisito.
- **Pannello admin:** applicazione separata (o modulo protetto della stessa web app) con autenticazione dedicata per lo staff.

*Questa è una proposta iniziale: la scelta definitiva dello stack va confermata con il team tecnico in base a competenze disponibili e vincoli di budget.*

---

## 9. Fuori scope per l'MVP (rimandato a fasi successive)

- Verifica identità tramite documento
- Verifica attiva dello stato civile
- **Verifica del numero di telefono via SMS OTP** (in questa fase il numero resta autodichiarato — v. RF-02b; possibile reintroduzione futura, eventualmente limitata al solo momento del match confermato per contenere i costi)
- Pricing dinamico per area geografica
- Importazione massiva di profili da agenzie partner
- App mobile nativa
- Chat interna alla piattaforma
- Logiche funzionali differenziate per i tier Premium/VIP (il campo esiste già a DB, ma senza feature dedicate)
- Espansione a mercati arabi/GCC
- **Colloquio conversazionale con un LLM per la profilazione** (originariamente previsto per estrarre EQ e stile di attaccamento tramite 5-7 scambi dialogici). Sostituito nell'MVP da test psicometrico strutturato + due campi descrittivi liberi (v. RF-07/RF-07b), scelta guidata da considerazioni di sicurezza (superficie di prompt injection su dati sensibili). Resta un possibile sviluppo futuro, da rivalutare quando il sistema avrà meccanismi di contenimento più maturi (sandboxing del modulo generativo, validazione strutturata dell'output, eventuale fine-tuning dedicato).

---

## 10. Punti aperti da definire prima dello sviluppo

1. **Contenuto del test psicometrico**: domande, numero, scala di risposta — richiede sessione di studio dedicata con un esperto (psicologo/consulente relazionale) prima dell'implementazione di RF-07.
2. **Finestra temporale** di validità di una proposta di match (ipotizzata 7 giorni in RF-14, da confermare).
3. **Importo esatto** della fee di match confermato (era stato discusso un riferimento indicativo di 10€, da validare come prezzo definitivo per l'MVP).
4. **Provider cloud e hosting** definitivo per l'ambiente di produzione (da scegliere in fase di infrastruttura).
5. **Policy su segnalazioni/dispute** tra utenti dopo lo scambio contatto (es. utente che segnala comportamento scorretto) — funzionalità minima nel pannello admin, ma il processo va definito.
6. **Valore di default definitivo del parametro N** (dimensione shortlist per l'analisi visiva, RF-11a/RF-25b): 5 o 10 come da richiesta — da confermare in base ai primi test sul DB Actor, valutando il compromesso tra qualità della selezione e tempo di elaborazione del batch mensile.
7. **Testo esatto della nota informativa sulla privacy dell'email** (v. RF-21) da mostrare in UI prima dello scambio contatto, e valutazione se raccogliere un consenso esplicito dell'utente su questo punto in fase di onboarding.
8. **Meccanismo di autenticazione email**: OTP come unico fattore, o OTP come secondo fattore accanto a una password tradizionale — impatta UX di login e scelta del provider email transazionale.
9. **Autenticazione a due fattori (2FA)** per l'account: da valutare come hardening futuro (v. RNF-10), dato che l'email è ora sia canale di login sia contatto condiviso col match — un'eventuale compromissione della casella email dell'utente avrebbe un impatto maggiore rispetto a un sistema con verifica telefonica separata.
10. **Set minimo di dati identificativi** da richiedere nel modulo di recupero accesso (RF-26b) perché sia sufficiente per una verifica manuale affidabile senza essere troppo invasivo, e **durata esatta del periodo di grazia** (RF-26d, ipotizzato 48 ore) da validare con l'esperienza reale dei primi casi.
11. **Voci sullo stile di attaccamento nel test psicometrico strutturato**: da includere nella sessione di studio con l'esperto (v. punto 1), valutando scale validate a scelta forzata (es. tipo ECR-R) come sostituto del colloquio conversazionale rimosso, per non perdere il segnale usato nella formula di compatibilità (attualmente il fattore pesato di più).

---

*Documento da considerarsi bozza di lavoro (v1). Suggerisco di validarlo in team e poi passare alla progettazione dettagliata dello schema fisico del DB e dei flussi UX.*
