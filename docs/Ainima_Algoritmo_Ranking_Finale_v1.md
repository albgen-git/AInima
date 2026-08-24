# Ainima — Algoritmo di Ranking Finale (v1)
### Bozza di lavoro — a cura dello psicologo del progetto

---

## 1. Pipeline completa

```
                         POOL CANDIDATI (nella stessa area geografica)
                                          │
                                          ▼
              ═══════ STEP 0 — FILTRI HARD (gate, pass/fail) ═══════
    Età, stato civile accettato, figli, dealbreaker fisici, distanza/lingua (§3bis)
                                          │
                                          ▼
                        Candidati sopravvissuti al filtro
                                          │
                                          ▼
     ═══════ Calcolo del punteggio composito per ciascun candidato ═══════
     STEP 1: Punteggio Big Five     STEP 2: Punteggio EQ/Attaccamento
     STEP 3: Coerenza Narrativa     STEP 4: Preferenze soft (estetica/stile)
     (tutti e 4 gli step sono calcolo puro — nessuna chiamata LLM in
     questa fase, vedi Documento 4 per la coerenza narrativa a embedding)
                                          │
                                          ▼
                    FINAL SCORE = Σ (wᵢ · Stepᵢ) — pesi da admin console
                                          │
                                          ▼
                  Candidato con FINAL SCORE più alto (sopra soglia minima)
                          → Proposta ufficiale del mese
                          → Report testuale generato SOLO ora (Prompt 5,
                            Documento 4), a valle del calcolo, mai prima
```

---

## 2. STEP 0 — Filtri Hard (gate, non punteggio)

Questi non entrano nel calcolo pesato: sono un cancello binario. Un candidato che non li supera **non viene nemmeno scored**, a prescindere da quanto sarebbe compatibile su tutto il resto.

- Range età reciproco rispettato da entrambe le parti
- Distanza: filtro condizionale, vedi logica dedicata al punto 3bis sotto (non più un semplice `pref_distanza_max_km` fisso)
- `stato_civile` compatibile con `pref_stato_civile_accettato`
- Coerenza su figli: `ha_figli`/`pref_accetta_figli` e `pref_desidera_figli_futuri` reciprocamente compatibili
- Dealbreaker fisici dichiarati come esclusione tassativa (es. altezza minima, se impostata come dealbreaker e non come preferenza soft)
- **Red flag critico:** se `flag_profilo_per_revisione_dati` è true (derivato da: ≥2 dimensioni con `confidenza_dimensione == 0.6` tra Big Five, EQ Score e Attaccamento — vedi Step 1-2 sotto e §10 di questo documento —, da `flag_trappola_fallita >= 1`, oppure dal quadrante Timoroso/Disorganizzato), il profilo va escluso dal matching automatico fino a revisione umana — non è un problema di compatibilità, è un problema di cura della persona, va gestito da un umano, non dall'algoritmo.

### Punto 3bis — La distanza non è più un limite fisso, ma un fattore personalizzato

L'idea di un tetto unico in km per tutti gli utenti è troppo rigida: non distingue chi rifiuta un pendolarismo scomodo da chi rifiuta a priori una relazione a distanza. La logica corretta va costruita su due nuovi dati raccolti in fase di onboarding:

- `importanza_vicinanza_geografica` (Float 0.0-1.0, da Likert 1-5): quanto quella specifica persona ritiene la vicinanza un fattore decisivo, indipendentemente dall'affinità.
- `lingue_parlate` (Array): le lingue in cui la persona è in grado di sostenere una relazione.

```
soglia_area_urbana_km = 50   // sotto questa soglia, la distanza resta come oggi

SE distanza_reale_km <= soglia_area_urbana_km:
    hard_filter_distanza = PASS (sempre)
    Punteggio_Distanza = 1 - (distanza_reale_km / soglia_area_urbana_km)

ALTRIMENTI (oltre la soglia, incluse le coppie internazionali):
    importanza_media = (importanza_vicinanza_geografica_A + importanza_vicinanza_geografica_B) / 2
    lingue_comuni = intersezione(lingue_parlate_A, lingue_parlate_B)

    SE lingue_comuni è vuoto:
        hard_filter_distanza = FAIL
        // qui il filtro resta rigido: senza una lingua condivisa la
        // relazione non può nemmeno iniziare, a prescindere da quanto
        // due profili siano affini su tutto il resto

    ALTRIMENTI SE importanza_media > 0.6:
        hard_filter_distanza = FAIL
        // entrambi (o anche uno solo, in modo marcato) considerano
        // la vicinanza un fattore decisivo: rispettarlo è più
        // importante che proporre comunque il match

    ALTRIMENTI:
        hard_filter_distanza = PASS
        Punteggio_Distanza = clamp( 1 - importanza_media , 0.2 , 0.8 )
        // oltre la soglia urbana i km reali smettono di essere
        // rilevanti in sé (2.000 km o 5.000 km non cambiano
        // l'esperienza psicologica della distanza): conta solo
        // quanto le due persone, di loro, hanno dichiarato di
        // tenerci alla vicinanza
```

**Perché ho tolto i km reali dal calcolo oltre la soglia urbana:** la percezione soggettiva della distanza non è lineare — la differenza psicologica tra Milano-Roma e Milano-Dubai è quasi nulla (in entrambi i casi "non è dietro l'angolo"), mentre conta moltissimo l'apertura dichiarata delle due persone a gestire quella distanza. Usare i km reali in quella fascia darebbe un falso senso di precisione a un fattore che è, di fatto, una questione di disponibilità personale.

---

## 3. STEP 1 — Punteggio Big Five (compatibilità caratteriale)

Riprendo la formula già impostata in precedenza:

> `BigFive_Score = Σ(wᵢ · Similarità_i) + Σ(kⱼ · Complementarità_j)`

| Facet | Logica | Come si calcola |
|---|---|---|
| Nevroticismo (globale) | Somiglianza, preferibilmente entrambi bassi | `1 - |N_A - N_B|`, con bonus se media bassa |
| Coscienziosità | Somiglianza | `1 - |C_A - C_B|` |
| Gestione risorse (facet C) | Somiglianza | `1 - |C7_10_A - C7_10_B|` |
| Apertura/Flessibilità valori (facet O) | Somiglianza medio-alta | `1 - |O8_10_A - O8_10_B|` |
| Assertività/Dominanza (facet E) | Complementarità moderata | Punteggio massimo quando uno dei due è moderatamente più alto dell'altro, penalità se **entrambi** estremamente alti |
| Estroversione (globale) | Mista/flessibile | `1 - |E_A - E_B| * 0.5` (peso ridotto: la letteratura qui è meno netta) |
| Gradevolezza | Somiglianza medio-alta, ma soprattutto valore assoluto alto conta per entrambi | Media dei due punteggi, non solo differenza |

`BigFive_Score` finale = media pesata delle righe sopra, normalizzata 0.0-1.0.

### Rettifica di confidenza per bassa coerenza interna del test

Il campo `confidenza_dimensione`, calcolato in `Ainima_Test_Psicometrico_BigFive_v1.md`
§7 Step 4, non è un quinto peso accanto a w1-w4: è un **modificatore di
confidenza interno al calcolo di BigFive_Score**, applicato solo alle
dimensioni con varianza interna anomala.

```
Per ogni dimensione Big Five (Estroversione, Gradevolezza, Coscienziosità,
Nevroticismo, Apertura):

    contributo_dimensione_effettivo = contributo_dimensione_originale * confidenza_dimensione
```

`BigFive_Score` si ricalcola poi come **media pesata** dei contributi
effettivi (non una somma semplice): questo evita che una singola
dimensione ridotta trascini in basso l'intero punteggio in modo
sproporzionato — le altre dimensioni non toccate continuano a pesare
per intero.

Lo stesso principio si applica a `Punteggio_EQ_Totale` (Step 2 sotto):
se il controllo statistico incrociato del Test EQ Score (`Ainima_Test_EQScore_v1.md`
§4) rileva un'incoerenza tra una facet Big Five e un pilastro EQ
correlato, il pilastro EQ coinvolto viene pesato con lo stesso
meccanismo (`confidenza_dimensione` ridotta), non escluso.

### Soglia per revisione umana (data quality, non giudizio sull'utente)

*(Correzione, seconda passata: la prima versione di questa correzione
usava ancora "numero di dimensioni... >= 2" in modo ambiguo — non
specificava se contare controlli falliti o dimensioni distinte. È la
stessa ambiguità che ha causato il Bug A trovato da Claude Code in
`_ricalcola_confidenza_e_flag()` nel Blocco C: due controlli incrociati
diversi puntavano entrambi su Autoregolazione, gonfiando il conteggio.
Ora la formula è esplicita su cosa si conta.)*

```
insieme_confidenze = {
    confidenza_big5_estroversione, confidenza_big5_gradevolezza,
    confidenza_big5_coscienziosita, confidenza_big5_nevroticismo,
    confidenza_big5_apertura,
    confidenza_eq_autoconsapevolezza, confidenza_eq_autoregolazione,
    confidenza_eq_empatia, confidenza_eq_responsabilita,
    confidenza_attaccamento_ansia, confidenza_attaccamento_evitamento
}   // 11 dimensioni distinte, sommando Big Five (5) + EQ Score (4) + Attaccamento (2)

SE count(v == 0.6 per v in insieme_confidenze) >= 2:
    flag_profilo_per_revisione_dati = true
```

**Punto chiave per l'implementazione:** questo è un conteggio su un
insieme di 11 valori distinti, uno per dimensione — MAI un contatore
incrementato una volta per ogni controllo che fallisce. Se più
controlli diversi (es. i 2 controlli incrociati dell'EQ Score §4b che
puntano entrambi su Autoregolazione) riducono la stessa dimensione,
quella dimensione compare comunque una sola volta nell'insieme sopra.

Non è un blocco del matching, e non genera mai una nota narrativa
libera sul profilo (es. "persona poco coerente") — solo un punteggio
di confidenza numerico. È un segnale che il profilo, nel suo insieme,
merita uno sguardo umano prima di entrare nel pool con piena fiducia,
non un giudizio sulla persona. Soglia impostata a 2 come punto di
partenza prudente, da ricalibrare col pilot.

---

## 4. STEP 2 — Punteggio EQ / Maturità Emotiva / Attaccamento

Questo è lo step a cui do il peso maggiore, per il motivo psicologico anticipato. Si compone di due parti.

### 4a. Compatibilità di maturità emotiva

```
media_maturita = (score_maturita_emotiva_A + score_maturita_emotiva_B) / 2
sbilanciamento = |score_maturita_emotiva_A - score_maturita_emotiva_B|

SE sbilanciamento > 0.35:
    penalita_sbilanciamento = (sbilanciamento - 0.35) * 1.5   // cresce rapidamente
ALTRIMENTI:
    penalita_sbilanciamento = 0

Punteggio_Maturita = clamp( media_maturita - penalita_sbilanciamento , 0.0 , 1.0 )
```

*Perché una soglia e non una penalità lineare da subito:* una piccola differenza di maturità è normale e spesso positiva (un partner leggermente più maturo può essere una risorsa). Il problema nasce quando il divario diventa strutturale — da lì in poi la penalità cresce più che proporzionalmente, coerente con quanto discusso sullo "sbilanciamento del carico emotivo".

### 4b. Compatibilità di attaccamento (formula continua, sostituisce la matrice categoriale)

Con il nuovo test scritto sull'attaccamento (`ansia_score`,
`evitamento_score` per ciascun utente — vedi `Ainima_Test_Attaccamento_v1.md`),
non serve più una matrice 4x4 su etichette: il calcolo diventa
diretto sui due punteggi continui, più preciso e interamente
deterministico — nessuna inferenza LLM coinvolta.

```
media_ansia       = (ansia_A + ansia_B) / 2
media_evitamento  = (evitamento_A + evitamento_B) / 2

// Penalità mirata sul pattern "inseguimento-fuga": scatta quando UNO
// dei due ha ansia alta e l'ALTRO ha evitamento alto — è la
// combinazione più instabile in letteratura, va pesata più di una
// semplice media
penalita_incrocio = max( ansia_A * evitamento_B , ansia_B * evitamento_A )

Attaccamento_Score = 1 - (media_ansia * 0.3)
                       - (media_evitamento * 0.3)
                       - (penalita_incrocio * 0.4)

Attaccamento_Score = clamp( Attaccamento_Score , 0.0 , 1.0 )
```

*Nota:* i pesi (0.3 / 0.3 / 0.4) sono un punto di partenza ragionevole,
non calibrato su dati reali — il peso maggiore sul termine incrociato
riflette la stessa logica di quello che prima era il valore più basso
della matrice (Ansioso-Evitante, il pattern "inseguimento-fuga" più
instabile in letteratura), ma va validato nel pilot come tutti gli
altri pesi già segnalati in questo documento.

```
Punteggio_EQ_Totale = (Punteggio_Maturita * 0.6) + (Attaccamento_Score * 0.4)
```

---

## 5. STEP 3 — Coerenza Narrativa (ora da test strutturato, non più da embedding)

Con l'introduzione del Test Profilo Relazionale (`Ainima_Test_Profilo_Relazionale_v1.md`),
questo step non usa più il confronto a embedding tra i campi liberi:

```
Punteggio_Narrativo = Punteggio_Narrativo_Strutturato
// calcolato interamente in Ainima_Test_Profilo_Relazionale_v1.md, §6
// già include la penalità di asimmetria per sotto-dimensione
```

---

## 6. STEP 4 — Preferenze Soft (estetica e stile di vita dichiarato)

Tutto ciò che l'utente ha indicato come *preferenza* e non come *dealbreaker* (già escluso allo Step 0):

```
Punteggio_Preferenze_Soft = media ponderata di:
  - Punteggio_Distanza (calcolato al punto 3bis)
  - Punteggio_Tag_Liste (vedi Ainima_Liste_Piace_Detesta_v1.md, §5)
  - corrispondenza fascia altezza preferita (se non dealbreaker)
  - corrispondenza stile estetico dichiarato (elegante/casual/sportivo/alternativo)
  - corrispondenza livello di attività fisica/sport
  - corrispondenza importanza della religione (|importanza_religione_A - importanza_religione_B|)
```

Se `flag_rifiuto_esplicito` (da `Ainima_Liste_Piace_Detesta_v1.md`) è
true per la coppia, va esposto nel report/admin insieme a
`flag_asimmetria_narrativa` — non nascosto dentro la media.

Peso volutamente contenuto nel calcolo finale — coerente con quanto discusso: l'estetica dichiarata è la componente meno predittiva e più soggetta al divario "teoria vs pratica" già affrontato in precedenza.

---

## 7. Formula finale e pesi (configurabili da admin console)

```
FINAL_SCORE = (w1 · BigFive_Score)
            + (w2 · Punteggio_EQ_Totale)
            + (w3 · Punteggio_Narrativo)
            + (w4 · Punteggio_Preferenze_Soft)

// vincolo: w1 + w2 + w3 + w4 = 1.0
```

**Pesi di default proposti:**

| Peso | Valore default | Motivazione |
|---|---|---|
| `w1` — Big Five | 0.30 | Base caratteriale solida, ma da sola non predice la tenuta della coppia |
| `w2` — EQ/Attaccamento | 0.35 | Il fattore più predittivo secondo la letteratura citata fin dall'inizio del progetto |
| `w3` — Coerenza Narrativa | 0.20 | Utile ma dichiarativo, va tenuto sotto peso rispetto ai segnali comportamentali |
| `w4` — Preferenze Soft | 0.15 | Rilevante per l'attrazione iniziale, ma la meno predittiva sul lungo periodo |

### Nuovi campi Admin Console

| Campo | Tipo | Default |
|---|---|---|
| `admin_config.weight_bigfive` | Float | 0.30 |
| `admin_config.weight_eq_attaccamento` | Float | 0.35 |
| `admin_config.weight_narrativa` | Float | 0.20 |
| `admin_config.weight_preferenze_soft` | Float | 0.15 |
| `admin_config.soglia_minima_proposta` | Float | 0.55 *(sotto questa soglia, nessuna proposta viene generata quel mese, anche per il miglior candidato disponibile — meglio nessun match che un match scadente)* |

*(Validazione consigliata in consolle: bloccare il salvataggio se `w1+w2+w3+w4 ≠ 1.0`.)*

---

## 8. Cosa fare quando nessun candidato supera la soglia

Coerente con il principio "Slow Matching" già definito nel progetto: se nessun profilo nel pool supera `soglia_minima_proposta`, quel mese **non genera una proposta forzata**. L'utente entra nel flusso "Settimana 4 — Attesa Attiva" con comunicazione trasparente (es. contenuti/newsletter), non con un match mediocre solo per rispettare la cadenza mensile — proporre qualcosa di scadente solo per "dare comunque qualcosa" rischierebbe di minare la fiducia nel metodo più di un mese di attesa in più.

---

## 9. Nuovi campi DB per la logica sulla distanza

| Campo | Tipo | Note |
|---|---|---|
| `importanza_vicinanza_geografica` | Float 0.0-1.0 | Da domanda Likert 1-5 in onboarding: "Quanto è importante per te che il partner viva vicino a te?" |
| `lingue_parlate` | Array | Lingue in cui la persona può sostenere una relazione — usato come filtro duro per le coppie oltre la soglia urbana |
| `admin_config.soglia_area_urbana_km` | Integer | Default 50. Sotto questa soglia la distanza resta un fattore graduato "classico"; oltre, entra la logica basata su importanza soggettiva + lingua comune |
| `admin_config.soglia_importanza_vicinanza_esclusione` | Float | Default 0.6. Sopra questo valore medio tra i due profili, la distanza torna a essere un filtro escludente anche oltre la soglia urbana |

## 10. Una cautela finale, da psicologo

Due avvertenze prima di mandare questo calcolo in produzione:

1. **La formula di attaccamento è una semplificazione utile, non verità clinica.** È costruita su pattern generali della letteratura, ma l'attaccamento reale di una persona è più sfumato di una formula a due dimensioni. Trattala come uno dei quattro ingredienti del punteggio, mai come predittore isolato — cosa che, va detto, la formula già fa bene tenendola a un peso di 0.35 e non superiore.
2. **Il caso "ansia alta + evitamento alto" (quadrante Timoroso/Disorganizzato)** meriterebbe, più che un punteggio automatico, un flag per revisione umana quando possibile — è il profilo più associato a storie di trauma relazionale, e un algoritmo puro rischia di trattarlo solo come "un numero più basso" invece che come un segnale che, in un servizio serio, merita più attenzione umana, non meno. Aggiungi questa condizione ai criteri che generano `flag_profilo_per_revisione_dati` già definiti altrove (Documento EQ Score, §4): `SE ansia_score > 0.7 E evitamento_score > 0.7: flag_profilo_per_revisione_dati = true`.

## Prossimi passi

1. Validare i pesi di default con il pilot (30-50 utenti) prima del lancio pubblico.
2. Costruire il flusso di gestione per i profili con `red_flags_rilevati` o con il quadrante Timoroso/Disorganizzato (chi li rivede? Con quale SLA?).
3. Decidere come mostrare (o non mostrare) all'utente il fatto che "nessuna proposta" è stata generata questo mese, senza generare frustrazione.
4. La scheda di proposta mensile deve mostrare sempre la distanza reale in modo trasparente **prima** che l'utente pre-autorizzi il pagamento — coerente con la trasparenza già scelta per il flusso di pagamento, così nessuno accetta "alla cieca" un match a lunga distanza.
