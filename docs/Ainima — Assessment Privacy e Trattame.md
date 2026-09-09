# Ainima — Assessment Privacy e Trattamento dei Dati

**Versione:** 2 — 9 settembre 2026 *(v1: 6 settembre)*
**Fase del progetto:** studio di fattibilità, ambiente di collaudo attivo, produzione da costruire
**Fonti esaminate:** `CLAUDE.md`, `Documento_Requisiti_v1.md`, i quattro test psicometrici, `Ainima_Algoritmo_Ranking_Finale_v1.md`, `Ainima_00_Indice_Schema_Consolidato_v1.md`, configurazione dell'ambiente di collaudo

**Natura del documento:** analisi tecnica e di conformità, **non un parere legale**. È scritto per essere messo in mano a un legale privacy e accorciargli il lavoro, non per sostituirlo. Sul fronte Emirati serve un legale locale.

**Novità della v2:** §1.6 (disallineamento fra repo e copia locale), §2.6 (il flag di trauma relazionale, che rafforza la qualificazione come dato sanitario), §4.6/4.7/4.8 (età non verificata, feedback su terzi, sicurezza dopo lo scambio contatti), §4.11/4.12 (recesso, art. 15).

---

## 0. Sintesi per chi ha poco tempo

Il progetto è messo meglio della media su questi temi. La separazione fra scoring e strato generativo (RNF-11), lo spostamento dell'orientamento sessuale dopo lo step di consenso, il flag `is_demo` per non spedire email a mille profili finti, il passaggio da inferenza LLM a test con calcolo deterministico: sono scelte che di solito si vedono solo dopo il primo incidente. Il grosso di quello che segue è completamento, non recupero.

Le cose che contano davvero:

1. **Il repository è indietro rispetto alla copia locale** (§1.6). Finché non si allineano, la squadra legge una fotografia vecchia e i riferimenti RF di questo documento non corrispondono.
2. **Dove si apre la società e dove stanno i dati sono decisioni separate** e si ottimizzano indipendentemente.
3. **La foto del "partner ideale" è il punto più esposto del prodotto**, e per misurazione interna il segnale che produce è indistinguibile dal rumore. Esiste un ridisegno che chiude il problema alla radice.
4. **La regola che segnala il quadrante ansia-alta/evitamento-alto come «associato a storie di trauma relazionale» è un'inferenza clinica** (§2.6). È l'elemento che più di ogni altro rende difficile sostenere che i dati psicometrici non siano dati sanitari.
5. **L'età non è verificata in alcun modo** (§4.6). È il rischio più serio che questo documento contenga, e non è un rischio privacy: è di sicurezza.

---

## 1. Giurisdizione, sede societaria e collocazione dei dati

### 1.1 Sono tre decisioni distinte, non una

1. **Dove si costituisce la società** — determina la legge che si applica come stabilimento, su *tutti* i trattamenti.
2. **Dove stanno gli interessati** — il GDPR si applica a chi offre servizi a persone nell'UE anche senza presenza europea (art. 3(2)).
3. **Dove risiedono fisicamente i dati** — questione di trasferimento e sicurezza, non di giurisdizione.

Una società di Dubai può tenere i dati a Francoforte senza alcun problema.

### 1.2 Il principio che risolve la domanda "utenti da tutto il mondo"

**La legge segue le persone, non i server.** Il database in Italia non lascia con il solo GDPR: se ci sono utenti in Brasile si applica la legge brasiliana, a Dubai quella emiratina.

La conseguenza pratica è però leggera, perché il GDPR è il regime generale più severo e le leggi arrivate dopo ne sono in larga parte modellate:

> **Progettare sul GDPR e applicarlo a tutti gli utenti, di qualunque nazionalità. Nessuna logica differenziata per paese.**

Quel che resta, mercato per mercato, è quasi sempre amministrativo: un rappresentante locale, un paragrafo nell'informativa, tempi diversi per le richieste di accesso.

**Non si apre al mondo il primo giorno.** Si parte da uno o due mercati fatti bene e si aggiungono paesi deliberatamente, ognuno con un controllo di mezza giornata.

### 1.3 L'unica eccezione che rompe l'architettura

La **localizzazione forzata**. Per Ainima ne esiste una rilevante: **gli Emirati impongono la conservazione locale dei dati sanitari** (Federal Law 2/2019). Vedi §2.

### 1.4 Aprire a Dubai non toglie il GDPR

Due motivi indipendenti, basta uno: il fondatore vive e lavora a Milano (stabilimento ≠ sede legale, conta l'attività reale e stabile); e il prodotto è costruito per il mercato italiano. Lo scenario reale è **GDPR più Emirati**.

*Nota fiscale, fuori competenza, da verificare con un commercialista:* imposta societaria del 9% sopra i 375.000 AED, 0% nelle free zone solo sul *qualifying income* e a condizioni precise. Non è più "zero tasse".

### 1.5 Dove mettere il database di produzione

**Raccomandazione: region UE, specificamente Francoforte (`eu-central-1`).** Motivo concreto: **AWS Rekognition non è disponibile a Milano** (`eu-south-1`). Scegliere Milano costringerebbe a spezzare di nuovo l'architettura.

**"Italia o AWS" non è un'alternativa:** AWS ha una region in Italia, e comunque tutte le foto passano già da AWS. O si accetta AWS e lo si usa bene (region UE, chiavi proprie, opt-out dai servizi AI a livello di organizzazione), o si sostituisce anche il riconoscimento facciale.

**Da progettare subito:** un campo di **residenza del dato** sul record utente, distinto dal campo mercato/valuta previsto per il pricing.

### 1.6 ⚠️ Il repository è indietro rispetto alla copia locale — *nuovo in v2*

Il `Documento_Requisiti_v1.md` sincronizzato da GitHub **non coincide** con la copia locale usata come riferimento. Nella versione del repo:

- §7.2 ha ancora `embedding_visivo_partner_ideale` (Vector), rimosso in locale col passaggio a Rekognition
- RF-11b dice ancora «seleziona come proposta finale il profilo **visivamente più simile**», non la versione a tie-break
- mancano `is_demo`, RNF-12, RF-14b/c/d, RF-25e-i, le pillole, l'engagement log, §7.9-7.15
- §10 punto 2 è «da confermare» invece che confermato a 7 giorni
- lo stack cita ancora CLIP e pgvector per l'analisi visiva, non Rekognition

**Conseguenze pratiche.** Chiunque legga il repo — la squadra, un consulente, un futuro sviluppatore — vede una fotografia vecchia. I riferimenti RF di questo assessment non corrispondono a quelli del repo. E non è verificabile dall'esterno quali modifiche siano effettivamente state applicate.

Da sistemare **prima** di ogni altra cosa in questa lista, perché rende inaffidabile tutto il resto.

---

## 2. I punteggi psicometrici sono dati sanitari?

### 2.1 Tre test su quattro: no

**Big Five, EQ Score e Profilo Relazionale** misurano personalità, competenze relazionali e preferenze di vita. Il passaggio da inferenza LLM a item chiusi con calcolo deterministico ha ridotto l'esposizione: un punteggio calcolato con un'aritmetica mostrabile a un'autorità è molto più difendibile di uno dedotto da una conversazione.

### 2.2 Il Test Attaccamento è l'eccezione

- Le dimensioni si chiamano **ansia da abbandono** ed **evitamento dell'intimità**: costrutti clinici.
- Il documento dichiara che il modello è quello dell'**ECR-R**, strumento della ricerca clinica.
- Lo Step 4 produce e **salva un'etichetta** che può valere **"Timoroso/Disorganizzato"**, e il documento cita «la pratica clinica reale».

### 2.3 Due item del Big Five tirano nella stessa direzione

Gli unici due su quaranta che chiedono sintomi anziché tratti:

- **N4** — «Sotto pressione, avverto facilmente sintomi fisici come tensione o mal di testa.»
- **N8** — «Ci sono giorni in cui mi sento giù senza un motivo preciso.»

### 2.4 Perché conta poco sotto GDPR e moltissimo negli Emirati

**Sotto GDPR cambia poco:** il sistema tratta già orientamento sessuale e fede religiosa, quindi è dentro l'art. 9 comunque.

**Sotto la legge emiratina cambia tutto:** se è dato sanitario, quello degli utenti negli Emirati deve restare negli Emirati e il database si spezza.

### 2.5 Modifiche che rafforzano la posizione

**Stato: prompt di implementazione consegnato.**

1. **Non persistere l'etichetta `stile_attaccamento`.** Conservare solo `ansia_score` ed `evitamento_score`, calcolando l'etichetta al volo. *Sblocco confermato:* `Ainima_Algoritmo_Ranking_Finale_v1.md` §4b ha già sostituito la matrice 4x4 con la formula continua sui due punteggi, quindi il matching non dipende più dall'etichetta.
2. **Riscrivere N4 e N8**, mantenendo facet, polarità e scala. Da validare con lo psicologo.
3. **Dichiarare la limitazione di finalità** in un nuovo RNF e nell'informativa. *Attenzione:* la regola di §2.6 la contraddice allo stato attuale — va risolta prima, o la dichiarazione sarebbe falsa.

**Sottopunto:** mostrare l'etichetta di quadrante all'utente contraddice un principio già scritto in CLAUDE.md («mai un numero, una percentuale o un'etichetta clinica»).

**Sottopunto tecnico:** versionare il questionario. Cambiare il testo di un item rende le risposte raccolte prima e dopo non confrontabili. Oggi è gratis, fra sei mesi è irrecuperabile. Stessa disciplina già applicata a `algoritmo_versione`.

### 2.6 ⚠️ Il flag di trauma relazionale — *nuovo in v2, e cambia la conclusione*

`Ainima_Algoritmo_Ranking_Finale_v1.md` §10 contiene questa regola:

```
SE ansia_score > 0.7 E evitamento_score > 0.7: flag_profilo_per_revisione_dati = true
```

motivata nel documento come: *«è il profilo più associato a storie di trauma relazionale»*.

**Il merito della scelta è giusto e va difeso.** Un servizio serio dà *più* attenzione umana a un profilo fragile, non meno. L'intuizione dello psicologo è corretta e va conservata.

Il problema è come è implementata, ed è doppio.

**Primo — è un'inferenza clinica su una storia di trauma.** Non è un dato dichiarato dall'utente: è una deduzione che il sistema compie da due punteggi. È l'elemento singolo che più di ogni altro rende difficile sostenere che questi dati non siano dati relativi alla salute — più del nome delle dimensioni, più dell'etichetta di quadrante. E **contraddice frontalmente la dichiarazione di limitazione di finalità di §2.5 punto 3**: quella regola *è* uno screening.

**Secondo — è confluita in `flag_profilo_per_revisione_dati`**, campo nato come flag di *qualità del dato* (risposte incoerenti fra loro, controllo di varianza interna). Lo stesso campo significa ora due cose radicalmente diverse: «l'utente ha risposto a caso» e «l'utente potrebbe avere una storia di trauma». Ereditano la stessa conservazione, gli stessi permessi di accesso, lo stesso trattamento operativo.

**Raccomandazione:**

- **Separare i due flag.** Uno di qualità dei dati, uno di attenzione umana, con retention, controllo accessi e giustificazione distinti.
- **Riformulare la motivazione nel documento** senza il riferimento al trauma. Non per nasconderla, ma perché la formulazione attuale è ciò che verrebbe letto in un'ispezione e afferma più di quanto il sistema possa sapere. *«Profilo che merita una lettura umana prima della proposta»* descrive la stessa regola senza asserire una diagnosi.
- **Documentare la revisione umana come garanzia ex art. 22(3)**: chi la esegue, con quale competenza, in quanto tempo, come la persona può contestarla.

---

## 3. La foto del "partner ideale" (RF-08b / RF-11b)

### 3.1 Il problema

La foto è, quasi sempre, il volto di una persona reale che non è utente, non ha visto l'informativa, viene sottoposta a elaborazione biometrica da AWS Rekognition, e non può sapere di esistere nei sistemi né chiederne la cancellazione.

Non c'è esenzione domestica: quella vale per l'utente che tiene la foto sul telefono, non per la società che la elabora a fini commerciali. Precedente italiano: **Clearview AI, 20 milioni di euro dal Garante**.

**Il consenso non risolve:** è personale e non delegabile. L'utente acconsente per sé, non per la persona ritratta.

### 3.2 Suggerire un personaggio famoso peggiora la posizione

- **Copyright** — la foto è quasi sempre un'opera protetta di un fotografo o un'agenzia.
- **Diritto all'immagine** (artt. 10 c.c., 96-97 L. 633/1941) — la notorietà ammette la pubblicazione senza consenso ma **esclude l'uso commerciale**.
- **GDPR** — l'eccezione dei «dati resi manifestamente pubblici dall'interessato» (art. 9(2)(e)) non copre il passaggio decisivo: la persona ha reso pubblica *una fotografia*, non un *template biometrico*. Il template lo crea Ainima. È la difesa che Clearview ha tentato in cinque paesi, perdendo ovunque.

### 3.3 Contraddizione con una decisione di prodotto già presa

CLAUDE.md registra la decisione di **non** avere campi strutturati per colore capelli o aspetto etnico, perché costruirebbero «un filtro estetico/razziale nel matching». RF-11b costruisce quel filtro in forma implicita e non ispezionabile.

### 3.4 E per misurazione interna il segnale non funziona

Verifica del team, 3 settembre 2026, su 60 coppie casuali: mediana del rumore **3,51**, 75° percentile **12,49**. I vincitori nei test reali — **5,79 / 6,88 / 8,26** — cadono dentro quella distribuzione. In `stable_v9` non esiste soglia minima.

Con i nuovi test strutturati i quasi-pareggi diventano più rari: **misurare quante volte il tie-break scatta davvero** sul nuovo impianto.

### 3.5 Il ridisegno proposto

Mostrare una **griglia di volti sintetici** e far scegliere tre o quattro. Giuridicamente **non esiste alcun interessato**: nessun terzo, nessun consenso mancante, nessun diritto d'immagine, nessun copyright.

Il passo che completa: **non conservare un embedding**. Derivare pochi attributi strutturati (fascia d'età apparente, corporatura, colore capelli) e salvare solo quelli. L'aspetto etnico non è fra loro — non nascosto, non costruito — e la scelta diventa verificabile guardando l'elenco dei campi.

Benefici di prodotto: niente clustering da personaggio famoso; diversità della griglia controllata; nessun upload da moderare (nel dataset attuale 112 foto di minori su 1000).

**Costo: una settimana** contro mezza giornata della rimozione secca.

**Conseguenza strategica:** eliminato `CompareFaces`, l'unico uso residuo di Rekognition è il rilevamento volto (non biometrico: nessun template) e la moderazione. Il rilevamento si fa in-process con MediaPipe. Rekognition esce dall'architettura e si apre la porta della **AWS European Sovereign Cloud** (lanciata il 15 gennaio 2026, Brandenburg, con RDS/Aurora e S3 ma senza Rekognition).

---

## 4. Altre criticità aperte

### 4.1 Il consenso ai dati particolari è un booleano — *Alto*

RNF-01 promette consenso «esplicito e granulare»; §7.1 lo implementa come `consenso_dati_sensibili`, un bool più timestamp. Serve una tabella dedicata: una riga per finalità, con versione del testo mostrato, timestamp e timestamp di revoca. È la prima cosa che un'autorità chiede e non è ricostruibile a posteriori.

### 4.2 Non esiste un modello di cancellazione — *Alto*

Il modello dati §7 non ha nulla che supporti il diritto all'oblio promesso. Nodo strutturale: `matches` referenzia due utenti, e cancellare A distrugge lo storico di B, che ha pagato 15€ per quel contatto. Da decidere ora perché determina come si cifra: cancellazione reale, tombstone anonimo nei match, retention separata per le foto, **crypto-shredding con chiave per utente** per i backup.

### 4.3 Il bucket delle foto è pubblico — *Alto, confermato*

`R2_PUBLIC_BASE_URL` punta a un dominio `pub-*.r2.dev`, che Cloudflare attiva solo con accesso pubblico abilitato. Le foto sono servite da URL pubblico, non autenticato e **senza scadenza**: ogni URL che esce una volta resta valido per sempre e sopravvive alla cancellazione dell'account.

Per la produzione: bucket privato, **URL firmati a scadenza breve** generati dal backend. L'app serve le foto, non il bucket. Rende concreto il rischio di **RF-25h**, che prevede il JSON completo dell'onboarding «nello stesso spazio già usato per le foto».

### 4.4 Rekognition gira su `us-east-1` — *Alto, confermato*

Ogni volto esce dall'UE ed è elaborato in Virginia. Il database è a Francoforte: le immagini prendono un'altra strada. Cambiare region è una riga di configurazione. Da verificare anche l'opt-out dall'uso dei contenuti per il miglioramento dei servizi AI.

### 4.5 Gestione dei segreti — *Alto*

Le credenziali vivono in `.env`. Per la produzione: **Secrets Manager** o SSM Parameter Store, e **due account AWS distinti** (collaudo e produzione) sotto Organizations.

### 4.6 ⚠️ L'età non è verificata in alcun modo — *Critico, nuovo in v2*

Data di nascita autodichiarata; la verifica dell'identità è esplicitamente fuori scope (§9). Una piattaforma matrimoniale, con foto, dove un minorenne può iscriversi compilando un campo.

**È il rischio più serio contenuto in questo documento, e non è un rischio privacy: è di sicurezza.** Le conseguenze di un minore nel pool sono di ordine diverso da tutto il resto. Il fatto che il dataset sintetico contenesse 112 foto di minori mostra che il tema si presenta anche quando nessuno lo cerca.

Non serve la verifica documentale completa per l'MVP. Serve però qualcosa di più di un campo: la carta di credito già richiesta è un filtro debole ma reale, e va dichiarato esplicitamente che serve anche a questo; va aggiunta una dichiarazione di maggiore età separata e registrata; e va definito cosa succede quando un utente viene segnalato come minorenne.

### 4.7 Il feedback parla di un'altra persona — *Alto, nuovo in v2*

RF-23/24: A racconta in testo libero com'è andato l'incontro con B. Quel testo è **dato personale di B**, conservato da Ainima, che B non ha mai visto. Se B esercita l'accesso ex art. 15 ha diritto di leggerlo — e A l'ha scritto ritenendolo riservato.

Da decidere ora, non alla prima richiesta: o il feedback diventa strutturato e non narrativo (scale, non racconti), o si avvisa A che il contenuto è ostensibile all'altra parte.

### 4.8 Dopo lo scambio contatti non è più possibile intervenire — *Alto, nuovo in v2*

Consegnata la vCard, l'email è fuori in modo irreversibile. L'assenza di chat interna significa nessuna possibilità di rilevare una molestia, e «sospendere l'account» a quel punto non recupera nulla.

La policy su segnalazioni e dispute è ancora aperta (§10 punto 5) e va trattata come **requisito di lancio**, non come dettaglio del pannello admin — tanto più che il sistema sa già quali profili sono più fragili (§2.6).

### 4.9 DPIA e DPO — *Medio, entrambi probabilmente obbligatori*

La **DPIA** (art. 35) è dovuta su due presupposti indipendenti, entrambi soddisfatti. Va fatta *prima* di scegliere il provider. Se il rischio residuo resta alto scatta la consultazione preventiva del Garante (art. 36), con tempi di settimane.

Il **DPO** (art. 37) è dovuto quando l'attività principale consiste in monitoraggio sistematico su larga scala o trattamento su larga scala di categorie particolari. Per una piattaforma il cui core business è profilare orientamento, fede e psicometria la risposta è quasi certamente sì. Non compare in nessun documento.

### 4.10 L'esclusione automatica per red flag — *Medio*

Decisione automatizzata (art. 22) su inferenze relative allo stato psicologico. La garanzia — revisione umana prioritaria — è già prevista ma va documentata come tale. Vedi §2.6.

### 4.11 Diritto di recesso — *Medio, nuovo in v2*

I 15€ addebitati alla conferma ricadono nella vendita a distanza: servono il consenso espresso all'esecuzione immediata e la dichiarazione di perdita del recesso, raccolti nel flusso di pagamento. Non è privacy, ma è un blocco al lancio in Italia.

### 4.12 «Mai un numero» contro l'art. 15 — *Medio, nuovo in v2*

Il principio di non mostrare mai punteggi è giusto sul piano etico, ma l'utente ha diritto a informazioni significative sulla logica dell'abbinamento automatizzato (art. 15(1)(h)). Le due cose si conciliano — si spiega la logica senza esibire il voto — ma va progettato apposta.

### 4.13 Due record reali nel collaudo — *Medio*

Gli account reali sono due, del fondatore e di sua figlia: persone della stessa famiglia che possono acconsentire per sé, quindi il punto è contenuto. Restano l'incoerenza con §6 («non va usato con dati reali di utenti») e la scadenza del database Render.

*Nota: CLAUDE.md contiene una riga («account reali, solo Alberto/Patrizia») che induce a credere che Patrizia sia reale. È uno dei mille profili sintetici. Da correggere.*

---

## 5. Decisioni aperte

| # | Decisione | Chi decide | Blocca |
|---|---|---|---|
| 1 | I punteggi psicometrici sono dati sanitari per la legge emiratina? | Legale emiratino | Se il DB può restare unico |
| 2 | RF-08b/RF-11b: ridisegno con volti sintetici, rimozione, o status quo? | Prodotto (Alberto + psicologo + marketing) | Sprint successivo |
| 3 | Come separare il flag di qualità dati dal flag di attenzione umana (§2.6) | Psicologo + Alberto | La dichiarazione di limitazione di finalità |
| 4 | Che filtro di età adottare nell'MVP (§4.6) | Alberto | Lancio |
| 5 | Il feedback post-match resta narrativo o diventa strutturato? (§4.7) | Prodotto | Primo utente reale |
| 6 | Sede societaria: Italia o free zone emiratina | Alberto + commercialista | Nulla sul piano dati |
| 7 | Provider e region di produzione | Alberto | Migrazione |
| 8 | Le nuove formulazioni di N4 e N8 sono psicometricamente valide? | Psicologo | Chiusura di §2.5 punto 2 |
| 9 | Il frontend Next.js fa SSR di dati utente o è un client che chiama l'API? | Verifica tecnica | Se Vercel è responsabile del trattamento |

---

## 6. Sequenza consigliata

1. **Allineare il repository alla copia locale** (§1.6) — *prima di tutto il resto*
2. Separare il flag di trauma da quello di qualità dati (§2.6) — *prima di scrivere la limitazione di finalità*
3. Decidere il filtro di età (§4.6) — *è la decisione con le conseguenze peggiori se rimandata*
4. Riscrivere RF-08b e RF-11b secondo il ridisegno — *prima di scrivere altro codice attorno*
5. Fissare sede societaria e region UE, aggiungendo il campo di residenza del dato
6. Avviare la DPIA — *dopo i punti 2, 3 e 4, che ne cambiano l'oggetto*
7. Rifare consensi e cancellazione nello schema — *prima del primo utente reale*
8. Definire la policy su segnalazioni e dispute (§4.8) — *requisito di lancio*
9. Chiudere i contratti con i responsabili verificando region e uso dei dati per l'addestramento
10. Far validare l'impianto da un legale privacy italiano

---

## 7. Cosa non è stato esaminato

Non sono stati visti il codice, lo schema fisico, la configurazione di Render, i permessi dei bucket, i documenti sui prompt LLM, `Ainima_Liste_Piace_Detesta_v1.md`.

Tre cose che meriterebbero un secondo giro, in ordine di probabile impatto: la configurazione di accesso dei bucket; il testo effettivo dell'informativa e degli step di consenso nel wizard; i permessi AWS in uso, dato che CLAUDE.md segnala che l'account non ha nemmeno i permessi per leggere le proprie quote di servizio — un segnale che i ruoli non sono stati progettati, ma accumulati.

**Limite di visibilità da tenere presente:** le versioni dei documenti lette per la v2 provengono dal repository, che è più vecchio della copia locale (§1.6). Alcune osservazioni potrebbero riferirsi a punti già risolti localmente e non ancora pubblicati.