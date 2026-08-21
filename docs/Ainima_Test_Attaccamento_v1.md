# Ainima — Test Psicometrico sull'Attaccamento (v1)
### Bozza di lavoro — a cura dello psicologo del progetto

---

## 1. Perché un test scritto invece di un'inferenza LLM

Questo documento sostituisce la componente di attaccamento che prima
veniva dedotta dall'IA durante la chat-intervista (`attaccamento_probabilita`,
Documento 2-3). Il cambio è positivo su più fronti:

- **Sicurezza:** zero testo libero dell'utente in ingresso a un LLM per
  calcolare un dato sensibile — solo risposte Likert, calcolo
  deterministico.
- **Validità scientifica:** il modello a 2 dimensioni continue (Ansia /
  Evitamento) è quello su cui si basa l'ECR-R, lo strumento più
  utilizzato e validato nella ricerca sull'attaccamento adulto — più
  solido di 4 etichette categoriali dedotte da una conversazione breve.
- **Costo e latenza:** nessuna chiamata LLM per questo calcolo, solo
  aritmetica.

---

## 2. Le 2 dimensioni

| Dimensione | Cosa misura | Polo alto | Polo basso |
|---|---|---|---|
| **Ansia da abbandono** | Paura del rifiuto, bisogno di rassicurazione, ipervigilanza sulla disponibilità del partner | Forte timore di abbandono | Sicurezza nel legame |
| **Evitamento dell'intimità** | Disagio con la vicinanza emotiva, preferenza per l'indipendenza, riluttanza ad aprirsi | Forte disagio con l'intimità | Agio nella vicinanza emotiva |

**Scala di risposta (per tutti gli item):**
1 = Per nulla d'accordo · 2 = Poco d'accordo · 3 = Neutro/Dipende · 4 = Abbastanza d'accordo · 5 = Completamente d'accordo

Gli item marcati **(R)** sono a punteggio invertito.

---

## 3. ANSIA DA ABBANDONO — 9 item

*(Revisione: accorciato da 12 a 9 item, riducendo gli item invertiti da 6 a 3 — sufficienti per il controllo dell'acquiescenza senza raddoppiare ogni concetto.)*

| # | Item | Rev. |
|---|------|------|
| AN1 | Ho spesso paura che la persona che amo smetta di provare interesse per me. | |
| AN2 | Non mi preoccupo se il mio partner non mi contatta per un po'. | (R) |
| AN3 | Ho bisogno di frequenti rassicurazioni sul fatto di essere amato/a. | |
| AN4 | Temo che le persone a cui tengo possano allontanarsi da me senza preavviso. | |
| AN5 | Anche nei momenti di silenzio prolungato da parte del partner, resto tranquillo/a. | (R) |
| AN6 | Mi capita di controllare spesso se il partner mi ha risposto o mi sta pensando. | |
| AN7 | Temo che piccoli disaccordi possano mettere a rischio la relazione. | |
| AN8 | Riesco a stare bene anche quando la relazione attraversa un momento di distanza. | (R) |
| AN9 | Mi capita di interpretare un tono neutro del partner come un segnale che qualcosa non va. | |

---

## 4. EVITAMENTO DELL'INTIMITÀ — 9 item

| # | Item | Rev. |
|---|------|------|
| EV1 | Preferisco non dipendere troppo dal mio partner per il mio benessere emotivo. | |
| EV2 | Mi viene naturale condividere pensieri e paure profonde con chi amo. | (R) |
| EV3 | Mi sento a disagio quando qualcuno cerca troppa vicinanza emotiva con me. | |
| EV4 | Preferisco gestire da solo/a i momenti difficili piuttosto che appoggiarmi al partner. | |
| EV5 | Mi piace condividere apertamente le mie vulnerabilità con chi amo. | (R) |
| EV6 | Mantenere una certa distanza mi fa sentire più sicuro/a in una relazione. | |
| EV7 | Tendo a minimizzare i problemi di coppia piuttosto che parlarne apertamente. | |
| EV8 | Parlare apertamente dei miei sentimenti con il partner mi viene naturale. | (R) |
| EV9 | Mi infastidisce quando il partner cerca troppo contatto fisico o emotivo. | |

---

## 5. Algoritmo di scoring

**Step 1 — Ricodifica item invertiti:**
`punteggio_ricodificato = 6 - punteggio_grezzo`

**Step 2 — Media per dimensione (9 item, 1-5):**
`media_dimensione = Σ(punteggi ricodificati dove necessario) / 9`

**Step 3 — Normalizzazione 0.0-1.0:**
```
ansia_score      = (media_ANSIA - 1) / 4
evitamento_score = (media_EVITAMENTO - 1) / 4
```

Questi due campi (non un'etichetta singola) sono il dato primario da
salvare e usare nel matching.

**Step 4 — Etichetta di quadrante (SOLO per la UI, mai per il calcolo)**

```
SE ansia_score < 0.5  E  evitamento_score < 0.5:  → "Sicuro"
SE ansia_score >= 0.5 E  evitamento_score < 0.5:  → "Ansioso"
SE ansia_score < 0.5  E  evitamento_score >= 0.5: → "Evitante"
SE ansia_score >= 0.5 E  evitamento_score >= 0.5: → "Timoroso/Disorganizzato"
```

*(Soglia 0.5 come punto di partenza; nella pratica clinica reale si
userebbero soglie calibrate sulla distribuzione della popolazione —
da rivedere dopo il pilot con i primi dati reali.)*

---

## 6. Impatto sui documenti esistenti (da aggiornare)

Questo test sostituisce la fonte di `attaccamento_probabilita`
(prima dedotta dalla chat-intervista). Campi DB da modificare nello
schema consolidato (Documento 00):

| Campo | Stato |
|---|---|
| `attaccamento_probabilita` (JSON, 4 valori) | **Superato** — non più derivato da LLM |
| `ansia_score` | **Nuovo** — Float 0.0-1.0 |
| `evitamento_score` | **Nuovo** — Float 0.0-1.0 |
| `stile_attaccamento` | Resta, ma ora calcolato con la regola dello Step 4 sopra (deterministica), non più come argmax di una distribuzione LLM |

La **matrice di compatibilità di attaccamento** nel documento
dell'algoritmo di ranking (Documento 5, §4b) andrebbe anch'essa
riscritta: da tabella 4x4 su etichette categoriali a **formula
continua** sui due punteggi, molto più precisa — ad esempio penalizzando
in modo specifico la combinazione "ansia alta in un partner +
evitamento alto nell'altro" (il pattern "inseguimento-fuga" di cui
avevamo parlato), invece di usare una cella fissa della matrice.

---

## Prossimi passi

1. **Decisione da confermare:** vuoi che riscriva anche la Chat-Intervista EQ (Documenti 2-3) eliminandola del tutto, sostituendola con i due campi liberi "Descrivi te stesso" / "Descrivi il partner ideale"? Questo tocca anche `score_maturita_emotiva` ed `eq_pilastro_*`, che finora venivano dedotti dalla stessa conversazione — vanno ripensati o rimossi.
2. **Coerenza con "tutto ML":** lo Stage 2 del matching (Documento 4, Prompt 4 — il Judge LLM bidirezionale) oggi usa un LLM per assegnare il punteggio di compatibilità narrativa, non solo per generare report. Se l'obiettivo è tenere l'IA generativa fuori dal calcolo dell'abbinamento, andrebbe sostituito con similarità vettoriale pura (embedding) o un modello ML addestrato — vuoi che lo riprogetti di conseguenza?
3. Aggiornare la formula finale di ranking (Documento 5) con la nuova componente continua di attaccamento.
