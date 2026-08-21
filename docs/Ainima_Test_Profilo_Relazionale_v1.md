# Ainima — Test Profilo Relazionale (v1)
### Valori, Stile di Vita, Dinamica Relazionale, Aspirazioni — bozza di lavoro

---

## 1. Perché questo test sostituisce il confronto a embedding

Le 4 categorie (Valori, Stile di Vita, Dinamica Relazionale,
Aspirazioni) erano finora stimate da un LLM che leggeva i due campi
liberi ("Descrivi te stesso"/"Descrivi il tuo partner ideale") e ne
derivava un testo canonico, poi confrontato per similarità vettoriale.
Questo test le rende **misurabili direttamente con item chiusi**,
raddoppiati — una versione su di sé, una sul partner desiderato — così
il confronto tra due profili diventa aritmetica diretta, non più
similarità testuale. I 2 campi liberi restano nel prodotto, ma solo
per alimentare il report narrativo (Documento 4, Prompt 5): non
entrano più nel calcolo del match.

**Struttura:** 13 sotto-dimensioni (4+3+3+3), ciascuna con 2 item
(Sé + Partner ideale) = **26 item totali**. Scala Likert 1-5, stessa
convenzione dei test precedenti.

---

## 2. CATEGORIA 1 — Valori e Priorità di Vita (4 sotto-dimensioni, 8 item)

| Sotto-dimensione | Item su di sé | Item sul partner ideale |
|---|---|---|
| Centralità della famiglia | La famiglia (attuale o futura) è una delle massime priorità della mia vita. | Cerco un partner per cui la famiglia sia una priorità centrale. |
| Orientamento alla carriera | Investo molte energie nella mia carriera e nei miei obiettivi professionali. | Mi piacerebbe un partner ambizioso, orientato alla crescita professionale. |
| Bisogno di stabilità | La stabilità (economica, abitativa, di routine) è per me un valore fondamentale. | Cerco un partner che dia valore alla stabilità e alla sicurezza quanto me. |
| Crescita personale | Dedico tempo ed energie alla mia crescita personale (introspezione, spiritualità, sviluppo di sé). | Vorrei un partner interessato al proprio percorso di crescita personale. |

## 3. CATEGORIA 2 — Stile di Vita Quotidiano (3 sotto-dimensioni, 6 item)

| Sotto-dimensione | Item su di sé | Item sul partner ideale |
|---|---|---|
| Socialità quotidiana | Nella vita di tutti i giorni, cerco spesso occasioni di socialità e stare con altre persone. | Mi piacerebbe un partner con un forte bisogno di socialità e vita di gruppo. |
| Organizzazione/pianificazione | Organizzo le mie giornate con largo anticipo, seguendo una routine strutturata. | Cerco un partner organizzato/a, che pianifica piuttosto che improvvisare. |
| Ritmo di vita | Preferisco un ritmo di vita dinamico e pieno di impegni piuttosto che tranquillo. | Mi piacerebbe condividere la vita con un partner dal ritmo dinamico e attivo. |

## 4. CATEGORIA 3 — Dinamica Relazionale (3 sotto-dimensioni, 6 item)

| Sotto-dimensione | Item su di sé | Item sul partner ideale |
|---|---|---|
| Autonomia vs Fusione | Nella coppia, ho bisogno di mantenere spazi e tempi indipendenti dal partner. | Cerco un partner che rispetti e condivida il mio bisogno di autonomia personale. |
| Condivisione dei ruoli/decisioni | Nella coppia preferisco decisioni condivise piuttosto che ruoli fissi e definiti. | Cerco un partner con cui costruire una dinamica paritetica nelle decisioni di coppia. |
| Espressività emotiva nella coppia | Nei momenti di tensione o vicinanza, esprimo apertamente ciò che provo al partner. | Cerco un partner che sappia esprimere apertamente le proprie emozioni nella coppia. |

## 5. CATEGORIA 4 — Aspirazioni e Progettualità (3 sotto-dimensioni, 6 item)

| Sotto-dimensione | Item su di sé | Item sul partner ideale |
|---|---|---|
| Impegno a lungo termine | Il matrimonio o un impegno formale a lungo termine è un obiettivo chiaro per me. | Cerco un partner orientato a un impegno serio e a lungo termine. |
| Mobilità geografica/apertura al cambiamento | Sono aperto/a a trasferirmi o cambiare vita in modo significativo per una relazione importante. | Mi piacerebbe un partner disposto a considerare un trasferimento o un grande cambiamento per la coppia. |
| Orizzonte progettuale | Pianifico attivamente il mio futuro a lungo termine (5-10 anni), non solo il presente. | Cerco un partner che condivida una visione di lungo termine per la vita insieme. |

---

## 6. Scoring

**Step 1 — Normalizzazione per item (nessun reverse in questo test):**
`punteggio_normalizzato = (punteggio_grezzo - 1) / 4`

**Step 2 — Salvataggio come JSON per categoria (self e partner ideale separati):**

```json
profilo_valori_self: {
  centralita_famiglia: 0.0-1.0,
  orientamento_carriera: 0.0-1.0,
  bisogno_stabilita: 0.0-1.0,
  crescita_personale: 0.0-1.0
}
profilo_valori_partner_ideale: { ...stesse chiavi... }

profilo_stile_vita_self / _partner_ideale: {
  socialita: 0.0-1.0, organizzazione: 0.0-1.0, ritmo_vita: 0.0-1.0
}

profilo_dinamica_relazionale_self / _partner_ideale: {
  autonomia_fusione: 0.0-1.0, condivisione_ruoli: 0.0-1.0,
  espressivita_emotiva: 0.0-1.0
}

profilo_aspirazioni_self / _partner_ideale: {
  impegno_lungo_termine: 0.0-1.0, mobilita_geografica: 0.0-1.0,
  orizzonte_progettuale: 0.0-1.0
}
```

**Step 3 — Compatibilità per sotto-dimensione, tra due utenti A e B:**

```
Per ogni sotto-dimensione d in ogni categoria:
    coerenza_A→B(d) = 1 - |A_self(d) - B_partner_ideale(d)|
    coerenza_B→A(d) = 1 - |B_self(d) - A_partner_ideale(d)|
    compatibilita(d) = (coerenza_A→B(d) + coerenza_B→A(d)) / 2
```

**Step 4 — Aggregazione a livello di categoria e complessivo:**

```
Punteggio_Categoria = media delle compatibilita(d) delle sotto-dimensioni di quella categoria

Punteggio_Narrativo_Strutturato =
      media dei 4 Punteggio_Categoria
      (o media pesata, se in futuro si vuole dare più peso a una categoria)

SE per una qualunque sotto-dimensione |coerenza_A→B(d) - coerenza_B→A(d)| > 0.5:
    flag_asimmetria_narrativa = true
    // stessa logica di penalità già usata altrove nel progetto
```

`Punteggio_Narrativo_Strutturato` sostituisce `compatibilita_narrativa_complessiva`
nella formula finale di ranking (Documento 5, Step 3) — stesso ruolo,
stesso peso `w3`, calcolo ora interamente numerico.

---

## 7. Nota metodologica

**Assunzione semplificativa dichiarata:** questo test tratta tutte le
13 sotto-dimensioni con la stessa logica di "somiglianza/coerenza"
(quanto il sé di uno combacia con l'ideale dell'altro). Per alcune
sotto-dimensioni — in particolare "Condivisione dei ruoli/decisioni"
— una logica di complementarità potrebbe essere più realistica di una
di pura coerenza diretta (due persone molto diverse su questo asse
possono comunque incastrarsi bene). È una semplificazione dichiarata,
da rivedere se i dati del pilot lo suggeriscono, sullo stesso modello
già usato per le facet Big Five (Documento 1) dove somiglianza e
complementarità sono state distinte esplicitamente.

**Rischio di "straight-lining":** con 26 item, alcuni utenti
potrebbero rispondere in modo poco differenziato (es. sempre "4" a
tutto). Consiglio di aggiungere, lato data quality, un controllo
statistico che segnali se la deviazione standard delle risposte di un
utente è troppo bassa — utile per il pilot, non blocca l'uso del dato.

---

## 8. Cosa diventa superato nei documenti esistenti

- **Documento 4** (`Ainima_Matching_Semantico_Report_v1.md`): il
  confronto a embedding (`self_embedding_vector`, `ideal_embedding_vector`,
  `compatibilita_narrativa_complessiva`) non entra più nel calcolo del
  matching. Restano validi solo Prompt 3a/3b (estrazione canonica) e
  Prompt 5 (report), ora usati esclusivamente per il testo che l'utente
  legge — mai per un punteggio.
- **Documento 5** (`Ainima_Algoritmo_Ranking_Finale_v1.md`), Step 3: va
  aggiornato per usare `Punteggio_Narrativo_Strutturato` al posto di
  `compatibilita_narrativa_complessiva`.
- **Documento 00** (indice): va aggiornato con i nuovi campi
  `profilo_*_self` / `profilo_*_partner_ideale` (8 campi JSON).
