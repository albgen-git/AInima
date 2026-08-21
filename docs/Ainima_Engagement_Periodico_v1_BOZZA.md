# Ainima — Engagement Periodico: Domande di Affinamento + Pillole di Saggezza (v1 — bozza concettuale)
### Evoluzione futura — non parte dello sprint di implementazione corrente

---

## 0. Stato di questo documento

⚠️ **Bozza concettuale.** A differenza degli altri documenti della
cartella, questo non è pronto per l'implementazione diretta — manca
di prompt, schema dati definitivo e soglie calibrate. Va trattato come
materiale di discussione per una fase successiva, non come specifica
da passare a Claude Code insieme al resto.

---

## 1. Obiettivo e razionale

Il problema di partenza: dashboard vuota, accessi sporadici (solo
all'arrivo di un'email di abbinamento). L'obiettivo è dare all'utente
un motivo ricorrente per tornare, in due forme complementari:

1. **Domande di affinamento** — piccoli batch di item psicometrici
   aggiuntivi, distribuiti nel tempo invece che tutti all'onboarding.
2. **Pillole di saggezza** — contenuto breve ed educativo, coerente
   con i 4 pilastri editoriali già individuati in fase di brainstorming
   iniziale (Intelligenza Emotiva, Comunicazione & Conflitto, Cultura e
   Valori, Preparazione al Matrimonio).

**Collegamento diretto con il taglio degli item appena fatto:** questo
meccanismo è il posto naturale dove far atterrare le sotto-dimensioni
che abbiamo scartato o accorciato per lunghezza (es. facet minori del
Test Profilo Relazionale, o item invertiti tolti dal Big Five/EQ/Attaccamento)
— non buttati, ma spostati fuori dall'onboarding.

---

## 2. Domande di Affinamento

### 2.1 Due fonti di contenuto

| Fonte | Descrizione |
|---|---|
| **Item di riserva** | Contenuto psicometrico valido ma escluso dall'onboarding per lunghezza (es. facet minori) |
| **Re-somministrazione mirata** | Quando `confidenza_dimensione` di una dimensione è bassa (Documento 1 §7, Documento 3 §4), invece di un invito immediato ignorabile, un piccolo batch mirato arriva a distanza di qualche giorno — meno intrusivo, stesso obiettivo |

### 2.2 Meccanica di invio

- Batch piccoli: **2-3 domande per invio**, mai un test intero.
- Cadenza indicativa: 1 batch ogni 1-2 settimane (da calibrare — vedi §5).
- Ogni risposta **aggiorna** lo score esistente della dimensione coinvolta, non lo sostituisce: la media si ricalcola includendo il nuovo dato, coerente con l'idea che la personalità non cambia a scatti in poche settimane.

### 2.3 Bozza di nuovi campi DB

| Campo | Tipo | Note |
|---|---|---|
| `domande_affinamento_pool` | Tabella | Item di riserva disponibili, taggati per dimensione/facet di origine |
| `domande_affinamento_log` | Tabella | `user_id`, `item_id`, `data_posta`, `risposta` — evita di riproporre lo stesso item due volte allo stesso utente |

---

## 3. Pillole di Saggezza

### 3.1 Categorizzazione

Ogni pillola ha due assi, non uno solo:

| Asse | Valori |
|---|---|
| **Pilastro editoriale** | Intelligenza Emotiva · Comunicazione & Conflitto · Cultura e Valori · Preparazione al Matrimonio |
| **Contesto/trigger** | Attesa generale (nessun match attivo) · Post-match confermato (pre primo appuntamento) · Post-rifiuto (uno dei due ha declinato) |

### 3.2 Personalizzazione (senza LLM nel percorso critico)

Le pillole sono **contenuto statico, scritto una volta da un editor
umano** (eventualmente con l'aiuto di un LLM in fase di scrittura, mai
in tempo reale per l'utente) — la selezione di quale pillola mostrare
a chi è puro tag-matching sui dati già raccolti, stesso principio già
adottato altrove nel progetto:

| Dato utente | Tag di pillola suggerito |
|---|---|
| `ansia_score` alto | Contenuti su gestione dell'attesa, autoregolazione dell'ansia relazionale |
| `evitamento_score` alto | Contenuti su apertura graduale, vulnerabilità nei primi incontri |
| `eq_pilastro_empatia` basso | Contenuti su ascolto attivo |
| Nessun dato specifico rilevante | Contenuto generico del pilastro in rotazione |

### 3.3 Bozza di nuovi campi DB

| Campo | Tipo | Note |
|---|---|---|
| `pillole_libreria` | Tabella | Contenuto statico gestito da admin/editoriale: testo, pilastro, contesto/trigger, tag di personalizzazione |
| `pillole_inviate_log` | Tabella | `user_id`, `pillola_id`, `data_invio`, `aperta` (bool) — evita ripetizioni e permette di misurare l'engagement |

---

## 4. Come si intrecciano i due flussi

```
Utente attivo, nessun match in corso
        │
        ▼
Cadenza periodica (es. settimanale):
   Alterna 1 pillola di saggezza / 1 batch di affinamento
   (mai entrambi nello stesso invio — rischio di sembrare un
   questionario travestito da contenuto di valore)

Evento: match confermato
        │
        ▼
   Pillola dedicata "Preparazione al primo appuntamento"
   (fuori dalla cadenza regolare, trigger immediato)

Evento: rifiuto/match non confermato
        │
        ▼
   Pillola dedicata di supporto, tono diverso da quello informativo
   generico (qui serve più delicatezza, non un consiglio pratico)
```

---

## 5. Domande aperte per quando riprenderemo il tema

1. **Cadenza esatta:** settimanale rischia di diventare rumore se il contenuto non è sempre di valore; quindicinale è più sicuro ma più lento nell'affinare i profili. Da testare nel pilot.
2. **Canale:** email, notifica push, o badge nella dashboard? Probabilmente combinazione, ma l'ordine di priorità va deciso guardando i tassi di apertura reali, non a tavolino.
3. **Opt-out granulare:** un utente dovrebbe poter disattivare le pillole ma non le domande di affinamento (o viceversa)? Probabile sì, ma va progettato nelle impostazioni.
4. **Rischio di invadenza:** un servizio che si posiziona su "maturità relazionale" non può permettersi di generare la stessa ansia da notifica che vuole aiutare a gestire — la cadenza va tarata con più cautela di quanto farebbe una app di dating tradizionale.

---

## 6. Perché questo resta "bozza" e non specifica pronta

Mancano ancora, prima che questo documento possa affiancare gli altri
come pronto per Claude Code: i testi reali delle pillole (lavoro
editoriale, non tecnico), le soglie di cadenza calibrate, e una
decisione di prodotto su canale/opt-out. Consigliato riprenderlo dopo
il pilot dei test principali, quando avrai dati reali su quanto le
persone tornano spontaneamente nell'app.
