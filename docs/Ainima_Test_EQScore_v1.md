# Ainima — Test Psicometrico EQ Score (v1)
### Bozza di lavoro — a cura dello psicologo del progetto

---

## 1. Perché un test scritto invece della chat-intervista

Questo documento sostituisce la funzione che prima svolgeva la
chat-intervista (Documenti 2-3, ora superati) per il calcolo di
`score_maturita_emotiva` e dei 4 `eq_pilastro_*`. Nessun testo libero
in ingresso a un LLM: solo risposte Likert, calcolo deterministico —
coerente con la scelta di sicurezza già presa per l'attaccamento.

**Limite da tenere presente:** un test scritto su costrutti come
empatia o responsabilità relazionale è più vulnerabile alla
desiderabilità sociale rispetto al Big Five o all'attaccamento,
perché queste dimensioni sono percepite come "virtù" da mostrare, non
tratti neutri. Per attenuare il problema, tutti gli item sono scritti
in forma **comportamentale/situazionale** (cosa faccio in una
situazione specifica) invece che come giudizio diretto su di sé.

---

## 2. Le 4 dimensioni (stesse dei pilastri già definiti)

*(Revisione: accorciato da 32 a 24 item totali, riducendo gli item invertiti per pilastro da 4 a 2 — sufficienti per il controllo dell'acquiescenza, coerente con lo stesso taglio applicato a Big Five e Attaccamento.)*

**Scala di risposta:** 1 = Per nulla d'accordo · 5 = Completamente d'accordo (come i test precedenti). Item **(R)** = punteggio invertito.

### Autoconsapevolezza — 6 item

| # | Item | Rev. |
|---|------|------|
| AC1 | Quando sono di cattivo umore, di solito riesco a individuare cosa l'ha causato. | |
| AC2 | Spesso mi accorgo di essere arrabbiato/a solo quando qualcuno me lo fa notare. | (R) |
| AC3 | Riesco a distinguere tra emozioni simili (es. delusione e rabbia) invece di etichettarle tutte come "mi sento male". | |
| AC4 | Le mie reazioni emotive a volte mi sorprendono, come se arrivassero dal nulla. | (R) |
| AC5 | So riconoscere quando uno stato d'animo del passato influenza il mio modo di reagire oggi. | |
| AC6 | Dopo un momento di tensione, riesco a spiegarmi cosa mi ha davvero infastidito. | |

### Autoregolazione — 6 item

| # | Item | Rev. |
|---|------|------|
| AR1 | Quando sono molto arrabbiato/a, faccio fatica a controllare cosa dico. | (R) |
| AR2 | Riesco a prendermi una pausa prima di rispondere quando sono nervoso/a. | |
| AR3 | Un piccolo imprevisto può bastare a mandarmi in crisi per il resto della giornata. | (R) |
| AR4 | Anche sotto stress, riesco solitamente a mantenere un tono di voce calmo. | |
| AR5 | So aspettare il momento giusto per affrontare una discussione importante, invece di reagire a caldo. | |
| AR6 | Riesco a calmarmi da solo/a dopo un episodio di forte tensione, senza bisogno che qualcun altro intervenga. | |

### Empatia — 6 item

| # | Item | Rev. |
|---|------|------|
| EM1 | Mi accorgo facilmente quando una persona vicina a me è a disagio, anche se non lo dice apertamente. | |
| EM2 | Quando qualcuno mi racconta un problema, il mio primo istinto è offrire una soluzione più che ascoltare come si sente. | (R) |
| EM3 | Prima di giudicare il comportamento di qualcuno, provo a immaginare cosa potrebbe aver vissuto. | |
| EM4 | Fatico a capire perché le persone si arrabbiano per cose che a me sembrano poco importanti. | (R) |
| EM5 | Mi capita di modificare il mio comportamento dopo aver notato che ha ferito qualcuno, anche senza che me lo dicano. | |
| EM6 | Riesco a percepire quando una persona dice "va tutto bene" ma in realtà non è così. | |

### Responsabilità relazionale — 6 item

| # | Item | Rev. |
|---|------|------|
| RE1 | Quando sbaglio, ammetto l'errore anche se è scomodo farlo. | |
| RE2 | Se una discussione va male, di solito penso che sia soprattutto colpa dell'altra persona. | (R) |
| RE3 | Riesco a chiedere scusa senza aggiungere giustificazioni che scaricano la colpa sull'altro. | |
| RE4 | Preferisco lasciar perdere piuttosto che ammettere di aver sbagliato qualcosa. | (R) |
| RE5 | Dopo un conflitto, mi chiedo spesso cosa avrei potuto fare diversamente. | |
| RE6 | Sono disposto/a a cambiare il mio comportamento se capisco che sta danneggiando una relazione. | |

---

## 3. Algoritmo di scoring (identico in struttura ai test precedenti)

```
Step 1 — Ricodifica item (R): punteggio_ricodificato = 6 - punteggio_grezzo
Step 2 — Media per pilastro (6 item, 1-5)
Step 3 — Normalizzazione: eq_pilastro_x = (media_pilastro - 1) / 4

score_maturita_emotiva = (eq_pilastro_autoconsapevolezza * peso1)
                        + (eq_pilastro_autoregolazione * peso2)
                        + (eq_pilastro_empatia * peso3)
                        + (eq_pilastro_responsabilita * peso4)
```

**Nuovi campi Admin Console** (pesi dei 4 pilastri, default equi, ricalibrabili dopo il pilot):

| Campo | Default |
|---|---|
| `admin_config.weight_eq_autoconsapevolezza` | 0.25 |
| `admin_config.weight_eq_autoregolazione` | 0.25 |
| `admin_config.weight_eq_empatia` | 0.25 |
| `admin_config.weight_eq_responsabilita` | 0.25 |

---

## 4. Controllo qualità: varianza interna + coerenza incrociata con il Big Five

*(Correzione: questa sezione aveva due problemi trovati durante
l'implementazione del Blocco C. Primo, mancava del tutto un controllo
di varianza interna proprio dell'EQ (quello che Big Five e Attaccamento
hanno) — Autoconsapevolezza e Responsabilità relazionale non avevano
NESSUN meccanismo di controllo qualità, né interno né incrociato.
Secondo, la regola locale `flag_incoerenza_statistica >= 2` duplicava e
contraddiceva la regola unificata del Big Five §7 — **ritirata**, resta
solo il conteggio unificato su tutte le dimensioni dei 3 test.)*

### 4a. Controllo di varianza interna (stessa logica di Big Five e Attaccamento)

```
Per ciascuno dei 4 pilastri (Autoconsapevolezza, Autoregolazione, Empatia, Responsabilità):
    range_pilastro = max(punteggi ricodificati del pilastro) - min(punteggi ricodificati del pilastro)
    SE range_pilastro >= 3.5 (su scala 1-5): flag_pilastro_anomalo = true
    confidenza_dimensione[pilastro] = 0.6 se flag_pilastro_anomalo altrimenti 1.0
```

### 4b. Controllo di coerenza incrociata con il Big Five (resta, come meccanismo aggiuntivo — non più come regola decisionale a sé)

Confrontando le correlazioni attese tra facet teoricamente collegate:

| Facet Big Five | Pilastro EQ atteso correlato | Relazione attesa |
|---|---|---|
| Nevroticismo (basso = stabile) | Autoregolazione | Negativa: Nevroticismo alto + Autoregolazione dichiarata alta = incoerenza statistica |
| Gradevolezza | Empatia | Positiva: Gradevolezza molto bassa + Empatia dichiarata molto alta = incoerenza |
| Coscienziosità | Autoregolazione | Positiva: forte divergenza tra i due = incoerenza |

```
SE |Nevroticismo - (1 - Autoregolazione)| > 0.5:
    confidenza_dimensione[Autoregolazione] = min(confidenza_dimensione[Autoregolazione], 0.6)

SE |(1 - Gradevolezza) - (1 - Empatia)| > 0.5:
    confidenza_dimensione[Empatia] = min(confidenza_dimensione[Empatia], 0.6)

SE |Coscienziosità - Autoregolazione| > 0.5:
    confidenza_dimensione[Autoregolazione] = min(confidenza_dimensione[Autoregolazione], 0.6)
```

*(Nota: questo controllo riduce SOLO la confidenza dei pilastri EQ
coinvolti, mai quella delle dimensioni Big Five citate — Nevroticismo,
Gradevolezza e Coscienziosità hanno già il proprio controllo di
varianza interna, indipendente, nel Documento 1 §7. Nessuna dimensione
viene penalizzata due volte per lo stesso motivo.)*

### 4c. Un'unica regola per la revisione umana (non più regole locali per test)

**Ritirata la regola locale `flag_incoerenza_statistica >= 2`.** Il
conteggio è unico e attraversa tutti e 3 i test, contando **dimensioni
distinte a confidenza 0.6**, non controlli falliti — dettaglio
importante: se sia il controllo Nevroticismo↔Autoregolazione sia
Coscienziosità↔Autoregolazione fanno scattare Autoregolazione, questa
conta **una volta sola** nel set delle dimensioni anomale, non due.

```
insieme_confidenze = {
    confidenza_big5_estroversione, confidenza_big5_gradevolezza,
    confidenza_big5_coscienziosita, confidenza_big5_nevroticismo,
    confidenza_big5_apertura,
    confidenza_dimensione[autoconsapevolezza], confidenza_dimensione[autoregolazione],
    confidenza_dimensione[empatia], confidenza_dimensione[responsabilita],
    confidenza_attaccamento_ansia, confidenza_attaccamento_evitamento
}   // 11 valori totali, sommando i 3 test

SE count(v == 0.6 per v in insieme_confidenze) >= 2:
    flag_profilo_per_revisione_dati = true
```

Formula completa e autorevole in `Ainima_Algoritmo_Ranking_Finale_v1.md`,
sezione "Soglia per revisione umana" — questo paragrafo la richiama,
non la duplica.

`confidenza_dimensione` per ciascun pilastro EQ segue esattamente la
stessa logica di soglia e di utilizzo già formalizzata per il Big Five
(`Ainima_Test_Psicometrico_BigFive_v1.md` §7 Step 4): mai un redo del
test, mai una nota narrativa sulla persona, solo un peso ridotto nel
calcolo finale (Documento 7, Step 1-2).

Zero rischio di prompt injection: è puro confronto numerico tra due
test già raccolti, nessun testo libero coinvolto. Ti propongo questo
come sostituto diretto del vecchio `incongruenze_test_intervista` — fammi
sapere se vuoi che lo integri nello schema consolidato o se per ora
preferisci restare più semplice e rimandarlo a dopo il pilot.
