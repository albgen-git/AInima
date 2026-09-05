# Ainima — Dashboard Engagement + Trigger Email (v1)
### Bozza di lavoro — a cura dello psicologo del progetto

*(Sostituisce lo stato "solo concettuale" di `Ainima_Engagement_Periodico_v1_BOZZA.md` §5 sui punti canale e meccanica — quel documento resta valido per la parte editoriale/personalizzazione, questo copre dashboard e trigger.)*

---

## 1. Stati della Dashboard

La dashboard non deve mai sembrare "vuota" nel senso letterale — anche
senza contenuto pendente, deve comunicare che il sistema sta lavorando.

| Stato | Cosa mostra | Priorità di visualizzazione |
|---|---|---|
| **Proposta di abbinamento attiva** | Card prioritaria, sempre in cima | 1 (massima) |
| **Domande di affinamento pendenti** | Card "2-3 domande per affinare il tuo profilo" + CTA | 2 |
| **Pillola da leggere** | Card col titolo della pillola + teaser di una riga | 3 |
| **Nessun contenuto pendente** | Messaggio rassicurante, non un vuoto: *"Il tuo profilo è aggiornato. Ti scriveremo appena ci sarà qualcosa di nuovo."* | — |

Se più stati coesistono (es. pillola + domande pendenti insieme), si
impilano nell'ordine di priorità sopra — mai un solo blocco unico che
li confonde.

---

## 2. Logica dei trigger email

### 2.1 Eventi che generano un trigger

| ID Trigger | Evento | Contenuto |
|---|---|---|
| T1 | Nuovo batch di domande di affinamento generato per l'utente | Riferimento al batch |
| T2 | Nuova pillola assegnata all'utente | Riferimento alla pillola — vedi §2.1bis per la logica di scelta |
| *(esistente, non nuovo)* | Proposta di abbinamento | Gestito dal flusso già definito, non tocca questa logica |

### 2.1bis Logica di selezione della pillola: "Pillola del giorno" (chiarita dopo una domanda diretta di Alberto — mancava una specifica esplicita)

*(Nota: le versioni precedenti del progetto menzionavano un "tag-matching"
per la selezione, pensato quando le pillole erano personalizzate su
`ansia_score`/`evitamento_score`. Con le pillole general purpose
(decisione successiva), quel meccanismo non ha più nulla da abbinare
— resta nello schema come possibile uso futuro, ma inerte. La logica
di selezione effettiva oggi è quella sotto.)*

```
Al momento in cui un utente risulta idoneo a ricevere un'email
(§2.2 sotto, intervallo scorrevole individuale):

    pillola_da_inviare = la pillola con data_creazione più recente
                          presente in pillole_libreria in quel momento

    // NON la più vecchia non ancora letta da quell'utente
    // NON selezionata per tag o dato personale
    // SEMPRE la stessa identica pillola per chiunque venga
    // controllato lo stesso giorno di calendario
```

**Perché questa scelta, esplicitamente:** Alberto ha bisogno di poter
rispondere con certezza e semplicità a un'eventuale contestazione
("cosa ci avete mandato quel giorno?") — con "Pillola del giorno" la
risposta è un solo testo per ogni data, non una risposta diversa per
ogni utente da ricostruire individualmente. La tracciabilità per
singolo invio resta comunque garantita da `pillole_inviate_log`
(user_id, pillola_id, data_invio) indipendentemente da questa scelta,
ma la scelta rende più semplice ragionare sulla cronologia a livello
aggregato, non solo per singolo utente.

### 2.2 Regola anti-invadenza: coda e raggruppamento (revisionata — intervallo scorrevole per utente, non più giorno fisso globale)

*(Correzione: la versione precedente usava un giorno fisso della
settimana, uguale per tutti gli utenti — pensato per una cadenza
settimanale. Con una cadenza di 2 giorni, un giorno fisso comune non
ha più senso (2 giorni non ricade mai sullo stesso giorno della
settimana). Il principio di fondo — mai un'email per singolo trigger,
sempre raggruppare — resta identico, cambia solo il meccanismo di
schedulazione: da "stesso giorno per tutti" a "intervallo individuale
dalla propria ultima ricezione".)*

Nessun trigger invia un'email immediatamente da solo. Ogni trigger
aggiunge contenuto a una coda per utente; un controllo periodico (es.
CRON giornaliero) verifica, per ciascun utente con contenuto in coda,
se è il suo momento di ricevere:

```
Quando scatta T1 o T2 per un utente:
    aggiungi il contenuto a email_coda_prossimo_invio (user_id, tipo, contenuto_id)
    // nessun invio immediato, solo accumulo

Ad ogni esecuzione del controllo periodico (es. giornaliero), per ogni
utente con almeno un elemento in coda:
    ultimo_invio = MAX(data_invio) da email_inviata_log per questo utente
    // NULL se l'utente non ha mai ricevuto un'email di engagement

    SE ultimo_invio è NULL OPPURE oggi >= ultimo_invio + admin_config.cadenza_email_engagement_giorni:
        prendi TUTTO ciò che è in coda per quell'utente
        componi UNA sola email con tutti i contenuti pendenti
        svuota la coda
        registra data_invio in email_inviata_log
    ALTRIMENTI:
        non inviare, lascia tutto in coda per il prossimo controllo
```

**Perché questo continua a raggruppare bene anche senza un giorno
comune:** l'intervallo si misura dalla ricezione precedente **di quello
specifico utente**, non da un calendario condiviso — se T1 e T2
scattano entrambi nella finestra di attesa di un utente, arrivano
comunque in una sola email, esattamente come prima. Cambia solo che
utenti diversi ricevono in giorni della settimana diversi tra loro,
in base a quando si sono iscritti o hanno ricevuto l'ultima email.

### 2.3 Tetto di frequenza — ora ridondante con la logica sopra, ma lasciato come commento

*(La condizione `oggi >= ultimo_invio + cadenza_email_engagement_giorni`
al punto 2.2 incorpora già il tetto di frequenza — non serve più un
controllo separato come nella versione precedente. Lo lascio annotato
solo per continuità con la vecchia numerazione del documento.)*

---

## 3. Contenuto dell'email

**Principio:** l'email è un teaser che riporta l'utente in dashboard,
non un sostituto della dashboard — il contenuto pieno (testo della
pillola, le domande stesse) si legge/risponde solo nell'app.

**Struttura:**
- Oggetto: varia in base a cosa contiene, esempi:
  - Solo domande: *"2 minuti per affinare il tuo profilo Ainima"*
  - Solo pillola: *"La tua nuova pillola: [Titolo]"* *(corretto da "di questa settimana" — non più accurato con cadenza di 2 giorni)*
  - Entrambi: *"Novità sul tuo profilo Ainima"*
- Corpo: 2-3 righe, un CTA unico verso la dashboard, nessun elenco puntato di "cose da fare" (rischia di sembrare un compito, non un contenuto di valore)

---

## 4. Nuovi campi DB

| Campo | Tipo | Note |
|---|---|---|
| `email_coda_prossimo_invio` | Tabella | `user_id`, `tipo_contenuto` (domande/pillola), `contenuto_id`, `aggiunto_il` |
| `email_inviata_log` | Tabella | `user_id`, `data_invio`, `contenuti_inclusi` (array), `aperta` (bool), `cliccata` (bool) |
| `admin_config.cadenza_email_engagement_giorni` | Integer | **2** *(era 7 — cambiato per la decisione di Alberto di usare un intervallo scorrevole più fitto; ricalibrabile guardando i tassi di apertura reali, come già previsto)* |
| ~~`admin_config.giorno_invio_email_engagement`~~ | ~~Enum~~ | **Superato — non serve più.** Il meccanismo a giorno fisso comune a tutti gli utenti è stato sostituito dall'intervallo scorrevole per utente (§2.2). Se il campo esiste già in schema da un'implementazione precedente, può restare inutilizzato o essere rimosso — non è più letto da nessuna logica. |

---

## 5. Cosa manca ancora (non tecnico, editoriale/prodotto)

Questo documento copre il meccanismo. Restano fuori, come già
segnalato nel documento precedente: i testi reali delle pillole,
l'opt-out granulare nelle impostazioni utente, e la calibrazione del
tetto di frequenza — quest'ultima soprattutto da guardare sui dati
reali di apertura/click una volta live, non da indovinare ora.

## Prossimi passi

1. Disegnare il wireframe delle card di dashboard (visual, non in questo documento).
2. Decidere se l'apertura di una card in dashboard debba anche azzerare eventuali badge/notifiche altrove (es. icona app).
3. Passare alla scrittura effettiva delle prime pillole editoriali, quando pronti a testare il meccanismo end-to-end.
