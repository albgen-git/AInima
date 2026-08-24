# Ainima — Indice e Schema Consolidato (v2)
### Documento di ingresso per l'implementazione — leggere per primo

Questo file esiste per dare una visione d'insieme prima di entrare nel
dettaglio dei singoli documenti. **Versione 2:** aggiornata dopo la
decisione di eliminare qualunque sessione di chat libera con un LLM
(rischio di prompt injection su dati sensibili). Test scritti al posto
del colloquio conversazionale, similarità vettoriale pura al posto del
giudizio LLM nel matching.

---

## 1. Ordine di lettura consigliato

| # | Documento | Stato | Cosa contiene |
|---|---|---|---|
| 1 | `Ainima_Test_Psicometrico_BigFive_v1.md` | Attivo | Test dei 5 fattori di personalità (50 item) |
| 2 | `Ainima_Test_Attaccamento_v1.md` | Attivo | Test scritto sull'attaccamento (24 item, 2 dimensioni continue) |
| 3 | `Ainima_Test_EQScore_v1.md` | Attivo | Test scritto sui 4 pilastri EQ (32 item) + controllo statistico di coerenza con il Big Five |
| 4 | `Ainima_Test_Profilo_Relazionale_v1.md` | Attivo | Test strutturato su Valori, Stile di Vita, Dinamica Relazionale, Aspirazioni (26 item, self + partner ideale) — sostituisce il confronto a embedding nel matching |
| 5 | `Ainima_Liste_Piace_Detesta_v1.md` | Attivo | 4 campi lista libera (mi piace/non sopporto/partner vorrei/partner non vorrei), matching a similarità vettoriale per tag con cache condivisa |
| 6 | `Ainima_Matching_Semantico_Report_v1.md` | Attivo (aggiornato) | Estrazione profili canonici dai 2 campi liberi (ora solo per il report), prompt del report finale |
| 7 | `Ainima_Algoritmo_Ranking_Finale_v1.md` | Attivo (aggiornato) | Formula di ranking finale; logica sulla distanza geografica; include Punteggio_Tag_Liste |
| 8 | `Ainima_Dashboard_Trigger_Email_v1.md` | Attivo | Stati della dashboard, logica di trigger e raggruppamento email per domande di affinamento e pillole di saggezza |

### Fuori dallo sprint corrente (evoluzione futura)

| Documento | Stato | Cosa contiene |
|---|---|---|
| `Ainima_Engagement_Periodico_v1_BOZZA.md` | ⚠️ Parzialmente superato — vedi nota | Il meccanismo di dashboard/email descritto qui è ora specificato nel Documento 8 (attivo). Restano da questo documento solo le parti ancora aperte: personalizzazione editoriale delle pillole, pool di domande di riserva, e le domande aperte di prodotto (opt-out granulare, testi editoriali). |
| ~~2 vecchio~~ | ~~`Ainima_Chat_Intervista_EQScore_v1.md`~~ | **SUPERATO — non implementare** | Architettura del colloquio conversazionale, sostituita dai Documenti 2-3 sopra |
| ~~3 vecchio~~ | ~~`Ainima_Prompt_Intervistatrice_RubricScorer_v1.md`~~ | **SUPERATO — non implementare** | Prompt dell'IA intervistatrice e del rubric-scorer da conversazione libera. Eliminato per motivi di sicurezza (superficie di prompt injection su dati sensibili) |

---

## 2. Perché questo cambio (contesto per chi implementa)

La versione 1 prevedeva una chat-intervista libera con un LLM per
dedurre EQ Score e stile di attaccamento da una conversazione. È stata
sostituita per una decisione di sicurezza esplicita: **nessuna sessione
di chat in cui l'utente può scrivere liberamente testo che finisce
dentro un prompt LLM**, per eliminare la superficie di prompt injection
su un servizio che tratta dati relazionali sensibili.

Cosa resta dell'IA generativa nel progetto (invariato nel principio,
ristretto nell'ambito):
- **Riassunti/estrazioni singole**, non conversazionali: i due campi
  liberi "Descrivi te stesso" e "Descrivi il tuo partner ideale"
  vengono trasformati in profili canonici da un prompt stateless
  (Documento 6, Prompt 3a/3b) — input trattato sempre come dato da
  riassumere, mai come istruzione. Usato solo per il report, non per
  il calcolo del match.
- **Generazione di report**, a valle di punteggi già calcolati, mai per
  calcolarli (Documento 6, Prompt 5).

Cosa NON usa più un LLM (ora puro calcolo/ML):
- Punteggi di personalità, attaccamento, EQ → test scritti, aritmetica.
- Compatibilità testuale tra profili (Valori, Stile di Vita, Dinamica
  Relazionale, Aspirazioni) → Test Profilo Relazionale, confronto
  numerico diretto per sotto-dimensione, non più similarità di
  embedding.

**Revisione anti-duplicazione (importante per chi ha già codice in corso):**
Un controllo incrociato tra tutti i banchi di item ha rilevato
sovrapposizioni quasi letterali tra `Ainima_Test_Psicometrico_BigFive_v1.md`
e gli altri test, costruiti in sessioni separate senza verifica
incrociata. Sono stati riscritti nel Documento 1: l'intera dimensione
Nevroticismo (duplicava Attaccamento ed EQ Autoregolazione),
7 dei 10 item originari di Gradevolezza (duplicavano EQ Empatia e
Responsabilità), e 1 item di Coscienziosità (duplicava il Test Profilo
Relazionale).

**Revisione di lunghezza (taglio degli item invertiti):** i 3 test
psicometrici a scala Likert sono stati accorciati riducendo il numero
di item invertiti per facet (mantenuti solo quelli necessari al
controllo dell'acquiescenza, non più uno per ogni singolo facet). Il
controllo di coerenza fine per-facet è stato semplificato a livello di
dimensione. Conteggio item aggiornato:

| Test | Item (v1 originale) | Item (dopo il taglio) |
|---|---|---|
| Big Five | 50 | 40 |
| Attaccamento | 24 | 18 |
| EQ Score | 32 | 24 |
| Profilo Relazionale | 26 | 26 *(nessun item invertito, non toccato)* |
| **Totale item chiusi** | **132** | **108** |

**Correzione post-implementazione (Blocco C, scoperta da Claude Code —
due passate):**

*Prima passata:* la formula di `confidenza_dimensione` (Documento 1 §7,
Documento 6 §10) produce solo due valori (`0.6`/`1.0`), non un continuo
— le soglie a valle erano rimaste tarate su una versione graduata
precedente. Corrette (`== 0.6`, non `< 0.6`). Colmato un buco:
mancava la formula di `confidenza_dimensione` per l'Attaccamento —
ora in `Ainima_Test_Attaccamento_v1.md` §5 Step 3bis.

*Seconda passata:* l'implementazione del Blocco C ha rivelato tre
problemi più profondi. (1) Il contatore per `flag_profilo_per_revisione_dati`
contava **controlli falliti**, non **dimensioni distinte** — se 2
controlli diversi puntavano sulla stessa dimensione EQ (Autoregolazione),
il conteggio si gonfiava artificialmente. (2) `confidenza_big5_*` (dalla
varianza interna) non entrava mai nel conteggio unificato, nonostante
la regola dichiarasse esplicitamente "Big Five + EQ + Attaccamento".
(3) Il documento EQ Score §4 aveva ancora una **regola locale separata**
(`flag_incoerenza_statistica >= 2`) mai allineata alla regola unificata
del Big Five — le due entravano in conflitto, e il codice era fedele
alla regola vecchia dell'EQ, non a quella nuova del Big Five. Corretto
tutto: la regola locale dell'EQ è **ritirata** (il meccanismo dei 3
controlli incrociati resta, ma alimenta il conteggio unico, non decide
da solo); il conteggio ora è esplicitamente su un **insieme di 11
dimensioni distinte** (5 Big Five + 4 EQ + 2 Attaccamento), formula
completa in `Ainima_Algoritmo_Ranking_Finale_v1.md`. Aggiunto anche un
controllo di varianza interna proprio dell'EQ (`Ainima_Test_EQScore_v1.md`
§4a) che prima mancava del tutto per Autoconsapevolezza e Responsabilità
relazionale — questi due pilastri non avevano alcun controllo qualità,
né interno né incrociato.

**Domande trappola condivise (nuove, sostituiscono parte del controllo perso col taglio):**
3 item di attenzione, indipendenti da qualunque dimensione, inseriti uno
ciascuno dentro Big Five, Attaccamento ed EQ Score (posizione
consigliata: a metà test, non nei primi o negli ultimi item):

| ID | Testo | Risposta attesa |
|---|---|---|
| T1 | "Per mostrare che stai leggendo con attenzione, seleziona 'Poco d'accordo' per questa domanda." | 2 |
| T2 | "Domanda di controllo: seleziona 'Abbastanza d'accordo' per continuare." | 4 |
| T3 | "Domanda di controllo: seleziona 'Neutro / Dipende' per questa affermazione." | 3 |

```
SE |risposta_data - risposta_attesa| >= 2: flag_trappola_fallita += 1
SE flag_trappola_fallita >= 1: flag_profilo_per_revisione_dati = true
```

Una sola trappola fallita è un segnale più forte di un'anomalia di
range interna (qui l'istruzione è esplicita, non c'è ambiguità
interpretativa) — per questo la soglia per la revisione umana è più
bassa (1, non 2) rispetto agli altri meccanismi di confidenza.

---

## 3. Pipeline end-to-end (riepilogo aggiornato)

```
1. Onboarding: bio, dati anagrafici/fisici, preferenze, lingue parlate,
   importanza vicinanza geografica, "Descrivi te stesso",
   "Descrivi il tuo partner ideale"          →  Documento 7, §3bis

2. Test Big Five (50 item)  →  score_big5_*                →  Documento 1

3. Test Attaccamento (24 item)  →  ansia_score, evitamento_score
                                                              →  Documento 2

4. Test EQ Score (32 item)  →  eq_pilastro_*, score_maturita_emotiva
   + controllo statistico di coerenza con il Big Five
   → flag_profilo_per_revisione_dati                        →  Documento 3

5. Test Profilo Relazionale (26 item, self + partner ideale)
   →  profilo_valori_self/_partner_ideale, profilo_stile_vita_self/_partner_ideale,
      profilo_dinamica_relazionale_self/_partner_ideale,
      profilo_aspirazioni_self/_partner_ideale                →  Documento 4

6. Estrazione profili canonici (SOLO per il report, non per il matching)
   →  self_profile_canonico, ideal_partner_profile_canonico    →  Documento 6, Prompt 3a/3b

7. Report utente ("La tua Prontezza Relazionale")
   →  report_prontezza_relazionale                             →  Documento 6, Prompt 5

8. Ciclo di matching mensile, per ogni utente attivo:
   a. STEP 0 — Filtri hard (età, stato civile, figli, dealbreaker,
      distanza/lingua, flag_profilo_per_revisione_dati)        →  Documento 7, §2 e §3bis
   b. Calcolo composito per ogni candidato sopravvissuto:
      - Punteggio Big Five                                     →  Documento 7, §3
      - Punteggio EQ/Attaccamento (formula continua)           →  Documento 7, §4
      - Coerenza Narrativa (Test Profilo Relazionale)          →  Documento 4, §6 + Documento 7, §5
      - Preferenze Soft (incl. Punteggio_Distanza)             →  Documento 7, §6
   c. FINAL_SCORE = w1·BigFive + w2·EQ/Attaccamento
                   + w3·Narrativa + w4·Preferenze Soft          →  Documento 7, §7
   d. Se FINAL_SCORE del migliore candidato < soglia_minima_proposta
      → nessuna proposta questo mese (mai match forzato)
   e. Altrimenti → report generato (Prompt 5) solo per il candidato
      proposto, distanza reale sempre visibile prima della
      pre-autorizzazione di pagamento
```

---

## 4. Schema DB consolidato (fonte di verità unica)

### 4.1 Identità, anagrafica, account
*(Definiti nel brainstorm iniziale del progetto: `user_id`, `nome`, `cognome`, `email`, `telefono`, `data_nascita`, `genere`, `orientamento_sessuale`, `stato_civile`, `ha_figli`, dati fisici, dati socio-economici, `stato_account`, `identita_verificata`, `livello_abbonamento`, ecc. — restano validi.)*

### 4.2 Campi liberi di profilazione — nuovi, sostituiscono la chat
| Campo | Tipo | Note |
|---|---|---|
| `descrizione_di_se` | Text | Campo libero onboarding, input del Prompt 3a |
| `descrizione_partner_ideale` | Text | Campo libero onboarding, input del Prompt 3b |

### 4.3 Preferenze di ricerca — ⚠️ un campo superato
| Campo | Stato | Nota |
|---|---|---|
| `pref_distanza_max_km` | **SUPERATO — non implementare** | Sostituito da `importanza_vicinanza_geografica` + `admin_config.soglia_area_urbana_km` (Documento 7, §3bis) |
| `pref_genere_cercato`, `pref_eta_min/max`, `pref_altezza_min/max_cm`, `pref_stato_civile_accettato`, `pref_accetta_figli`, `pref_desidera_figli_futuri` | Validi | Usati nei Filtri Hard |

### 4.4 Personalità — Big Five (Documento 1)
`score_big5_estroversione`, `score_big5_gradevolezza`, `score_big5_coscienziosita`, `score_big5_nevroticismo`, `score_big5_apertura` — tutti Float 0.0-1.0.

`confidenza_big5_estroversione`, `confidenza_big5_gradevolezza`, `confidenza_big5_coscienziosita`, `confidenza_big5_nevroticismo`, `confidenza_big5_apertura` — Float, valori possibili solo `0.6`/`1.0`, da controllo di varianza interna (Documento 1, §7 Step 4). Entrano nell'insieme unificato per `flag_profilo_per_revisione_dati` — vedi 4.6 sotto.

### 4.5 Attaccamento (Documento 2) — ⚠️ campo superato
| Campo | Stato | Tipo | Note |
|---|---|---|---|
| `attaccamento_probabilita` | **SUPERATO — non implementare** | — | Era dedotto dall'LLM in conversazione; non più necessario |
| `ansia_score` | Nuovo | Float 0.0-1.0 | Dato primario |
| `evitamento_score` | Nuovo | Float 0.0-1.0 | Dato primario |
| `stile_attaccamento` | Derivato | Enum | Solo per UI — calcolato con soglie deterministiche (Documento 2, §5, Step 4), non più argmax di una distribuzione LLM |
| `confidenza_attaccamento_ansia`, `confidenza_attaccamento_evitamento` | Nuovo | Float, valori possibili solo `0.6`/`1.0` | Da controllo di varianza interna (Documento 2, §5 Step 3bis) — mancava, colmato durante il Blocco C |

### 4.6 EQ Score (Documento 3)
| Campo | Tipo | Note |
|---|---|---|
| `eq_pilastro_autoconsapevolezza`, `eq_pilastro_autoregolazione`, `eq_pilastro_empatia`, `eq_pilastro_responsabilita` | Float 0.0-1.0 | Da test scritto, non più da rubric-scorer LLM |
| `score_maturita_emotiva` | Float 0.0-1.0 | Media pesata dei 4 pilastri |
| `confidenza_eq_autoconsapevolezza`, `confidenza_eq_autoregolazione`, `confidenza_eq_empatia`, `confidenza_eq_responsabilita` | Float, valori possibili solo `0.6`/`1.0` | Da varianza interna (Documento 3, §4a) **e/o** da coerenza incrociata col Big Five (Documento 3, §4b) — si prende il valore minore se entrambi i controlli si applicano. Mancava del tutto per Autoconsapevolezza/Responsabilità prima del Blocco C |
| `flag_profilo_per_revisione_dati` | Boolean | Deriva da: (a) ≥2 dimensioni distinte (su un insieme di 11: 5 Big Five + 4 EQ + 2 Attaccamento) con `confidenza_dimensione == 0.6` — formula completa in Documento 7, sezione "Soglia per revisione umana"; (b) quadrante Timoroso/Disorganizzato dell'attaccamento (Documento 7, §10); oppure (c) `flag_trappola_fallita >= 1` |
| `flag_trappola_fallita` | Integer | Numero di domande trappola fallite (su 3 totali, una per Big Five/Attaccamento/EQ Score) |

### 4.6bis Test Profilo Relazionale (Documento 4) — nuovo, sostituisce l'8 campo dell'embedding
| Campo | Tipo | Note |
|---|---|---|
| `profilo_valori_self` / `profilo_valori_partner_ideale` | JSON | 4 sotto-dimensioni ciascuno (centralita_famiglia, orientamento_carriera, bisogno_stabilita, crescita_personale) |
| `profilo_stile_vita_self` / `profilo_stile_vita_partner_ideale` | JSON | 3 sotto-dimensioni (socialita, organizzazione, ritmo_vita) |
| `profilo_dinamica_relazionale_self` / `profilo_dinamica_relazionale_partner_ideale` | JSON | 3 sotto-dimensioni (autonomia_fusione, condivisione_ruoli, espressivita_emotiva) |
| `profilo_aspirazioni_self` / `profilo_aspirazioni_partner_ideale` | JSON | 3 sotto-dimensioni (impegno_lungo_termine, mobilita_geografica, orizzonte_progettuale) |

### 4.6ter Liste "Mi Piace/Non Sopporto" (Documento 5) — nuovo
| Campo | Tipo | Note |
|---|---|---|
| `mi_piace`, `non_sopporto`, `partner_vorrei`, `partner_non_vorrei` | Text | Input grezzo, liste separate da virgola |
| `mi_piace_tags`, `non_sopporto_tags`, `partner_vorrei_tags`, `partner_non_vorrei_tags` | Array | Dopo parsing/normalizzazione |
| `tag_embedding_cache` | Tabella condivisa | `tag_normalizzato` (PK), `embedding_vector` — condivisa tra tutti gli utenti, non per-utente |

### 4.7 Campi ora superati (erano specifici della chat-intervista)
`red_flags_rilevati`, `incongruenze_test_intervista`, `transcript_id`, `chat_eq_completata_il` — **non implementare**: erano output del rubric-scorer su conversazione libera, ora eliminato. La loro funzione di controllo qualità è coperta da `flag_profilo_per_revisione_dati` (vedi 4.6), calcolato in modo interamente statistico.

### 4.8 Profili semantici per il report narrativo (Documento 6) — ⚠️ un campo superato, resto ora solo per il testo del report
| Campo | Stato | Tipo | Note |
|---|---|---|---|
| `vettore_embedding_profilo` | **SUPERATO — non implementare** | — | |
| `self_profile_canonico` | Valido | Text (4 categorie) | Ora estratto da `descrizione_di_se`, usato solo come materiale per Prompt 5 (report) |
| `ideal_partner_profile_canonico` | Valido | Text (4 categorie) | Idem, da `descrizione_partner_ideale` |
| `self_embedding_vector` | ⚠️ Non usato nel matching | Vector | Calcolato solo se serve altrove (es. ricerca testuale in UI); **non entra nel calcolo del Punteggio_Narrativo** |
| `ideal_embedding_vector` | ⚠️ Non usato nel matching | Vector | Idem |
| `report_prontezza_relazionale` | Valido | Text | |

### 4.9 Geografia e lingua (Documento 7, §3bis)
`importanza_vicinanza_geografica` (Float 0.0-1.0), `lingue_parlate` (Array).

### 4.10 Campi calcolati per-coppia (non persistiti a lungo termine)
`Punteggio_Narrativo_Strutturato` *(sostituisce `compatibilita_narrativa_complessiva`, ora superato)*, `Punteggio_Distanza`, `Punteggio_Tag_Liste`, `BigFive_Score`, `Punteggio_EQ_Totale`, `Punteggio_Narrativo`, `Punteggio_Preferenze_Soft`, `FINAL_SCORE`, `flag_asimmetria_narrativa`, `flag_rifiuto_esplicito`.

---

## 5. Parametri Admin Console (consolidato, v2)

| Campo | Tipo | Default | Note |
|---|---|---|---|
| `admin_config.report_top_candidates` | Integer | 10 | *(Rinominato da `matching_stage2_pool_size`)* Ora regola solo quanti report testuali pre-generare, non il calcolo dei punteggi |
| `admin_config.weight_bigfive` | Float | 0.30 | |
| `admin_config.weight_eq_attaccamento` | Float | 0.35 | |
| `admin_config.weight_narrativa` | Float | 0.20 | |
| `admin_config.weight_preferenze_soft` | Float | 0.15 | |
| `admin_config.weight_eq_autoconsapevolezza` | Float | 0.25 | Nuovo — composizione interna di `score_maturita_emotiva` |
| `admin_config.weight_eq_autoregolazione` | Float | 0.25 | Nuovo |
| `admin_config.weight_eq_empatia` | Float | 0.25 | Nuovo |
| `admin_config.weight_eq_responsabilita` | Float | 0.25 | Nuovo |
| `admin_config.soglia_minima_proposta` | Float | 0.55 | |
| `admin_config.soglia_area_urbana_km` | Integer | 50 | |
| `admin_config.soglia_importanza_vicinanza_esclusione` | Float | 0.6 | |

*Vincoli di validazione: `weight_bigfive + weight_eq_attaccamento + weight_narrativa + weight_preferenze_soft = 1.0`; i 4 `weight_eq_*` devono anch'essi sommare a 1.0.*

---

## 6. Cose ancora aperte

1. Flusso operativo di revisione umana per `flag_profilo_per_revisione_dati` — chi rivede, con quale SLA.
2. Come comunicare in app l'assenza di proposta in un dato mese.
3. Calibrazione dei pesi di default dopo il pilot su 30-50 utenti (inclusi i nuovi pesi della formula continua di attaccamento).
4. UX della scheda di proposta mensile: la distanza reale deve essere sempre visibile prima della pre-autorizzazione di pagamento.
5. Mitigazione residua di prompt injection sui 2 campi liberi ("Descrivi te stesso"/"partner ideale"): anche se non è una conversazione, restano testo libero in input al Prompt 3a/3b. Consigliato: trattare sempre l'input come dato da riassumere e mai come istruzione (già specificato nei prompt), eventualmente aggiungere un livello di sanitizzazione/troncamento a monte.
