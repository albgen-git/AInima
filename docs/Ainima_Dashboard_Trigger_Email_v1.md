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
| T2 | Nuova pillola assegnata all'utente | Riferimento alla pillola |
| *(esistente, non nuovo)* | Proposta di abbinamento | Gestito dal flusso già definito, non tocca questa logica |

### 2.2 Regola anti-invadenza: coda e raggruppamento

Nessun trigger invia un'email immediatamente da solo. Ogni trigger
aggiunge contenuto a una coda per utente; l'invio avviene secondo un
ritmo fisso, raggruppando tutto ciò che si è accumulato:

```
Quando scatta T1 o T2 per un utente:
    aggiungi il contenuto a email_coda_prossimo_invio (user_id, tipo, contenuto_id)

SE non esiste già un invio schedulato per questo utente nella finestra corrente:
    schedula l'invio al prossimo "giorno fisso" configurato
    (default: ogni martedì mattina — prevedibilità per l'utente,
    batching lato sistema)

Al momento dell'invio schedulato:
    prendi TUTTO ciò che è in coda per quell'utente
    componi UNA sola email con tutti i contenuti pendenti
    svuota la coda
```

**Perché un giorno fisso e non "appena pronto":** rende il ritmo
prevedibile per l'utente (sa che il martedì può arrivare qualcosa,
non riceve email a orari casuali) e garantisce che trigger multipli
nella stessa settimana producano una sola email, non tre.

### 2.3 Tetto di frequenza (sicurezza aggiuntiva)

```
SE l'utente ha già ricevuto un'email di engagement negli ultimi
   admin_config.cadenza_email_engagement_giorni (default 7):
       non inviare, lascia tutto in coda per il prossimo giro
```

---

## 3. Contenuto dell'email

**Principio:** l'email è un teaser che riporta l'utente in dashboard,
non un sostituto della dashboard — il contenuto pieno (testo della
pillola, le domande stesse) si legge/risponde solo nell'app.

**Struttura:**
- Oggetto: varia in base a cosa contiene, esempi:
  - Solo domande: *"2 minuti per affinare il tuo profilo Ainima"*
  - Solo pillola: *"La tua pillola di questa settimana: [Titolo]"*
  - Entrambi: *"Novità sul tuo profilo Ainima"*
- Corpo: 2-3 righe, un CTA unico verso la dashboard, nessun elenco puntato di "cose da fare" (rischia di sembrare un compito, non un contenuto di valore)

---

## 4. Nuovi campi DB

| Campo | Tipo | Note |
|---|---|---|
| `email_coda_prossimo_invio` | Tabella | `user_id`, `tipo_contenuto` (domande/pillola), `contenuto_id`, `aggiunto_il` |
| `email_inviata_log` | Tabella | `user_id`, `data_invio`, `contenuti_inclusi` (array), `aperta` (bool), `cliccata` (bool) |
| `admin_config.cadenza_email_engagement_giorni` | Integer | Default 7 |
| `admin_config.giorno_invio_email_engagement` | Enum (giorno settimana) | Default Martedì |

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
