# Ainima — Matching Semantico a 2 Stadi + Report Finale (v1)
### Bozza di lavoro — a cura dello psicologo del progetto

---

## 1. Architettura aggiornata

```
[Bio onboarding]  +  [Campo libero: "Descrivi te stesso"]
              │
              ▼
    PROMPT 3a — Estrattore Profilo DI SÉ (canonico)
    (trasformazione singola, nessuna conversazione — input testo libero
    trattato SEMPRE come dato da riassumere, mai come istruzione)
              │
              ▼
   self_profile_canonico ──► embedding ──► self_embedding_vector


[Campo libero: "Descrivi il tuo partner ideale"]
              │
              ▼
    PROMPT 3b — Estrattore Profilo PARTNER IDEALE (canonico)
              │
              ▼
ideal_partner_profile_canonico ──► embedding ──► ideal_embedding_vector


═══════════ MATCHING — Similarità vettoriale pura (stesso principio del confronto foto) ═══════════
Per ogni candidato C nel pool compatibile su criteri hard:
   coerenza_A→C = cosine( U.ideal_embedding_vector , C.self_embedding_vector )
   coerenza_C→A = cosine( C.ideal_embedding_vector , U.self_embedding_vector )
   compatibilita_narrativa_complessiva = (coerenza_A→C + coerenza_C→A) / 2

   SE |coerenza_A→C - coerenza_C→A| > 0.4:
       compatibilita_narrativa_complessiva *= 0.75   // penalità asimmetria
       flag_asimmetria_narrativa = true

   → ranking di tutti i candidati per compatibilita_narrativa_complessiva


[Punteggio finale calcolato: Big Five + EQ + Narrativa + Preferenze — Documento 5]
              │
              ▼
    PROMPT 5 — Generatore Report (SOLO per il/i candidato/i proposto/i,
    non per l'intero pool — riceve i punteggi già calcolati, non li
    ricalcola e non decide nulla: scrive solo il testo)
              │
              ▼
   "La tua Prontezza Relazionale" (Prompt 5, invariato)
```

**Cosa è cambiato rispetto alla versione precedente:** il Judge LLM
bidirezionale (Prompt 4) è stato eliminato. Non c'era un vero bisogno
di un LLM che "giudicasse" la compatibilità testuale — la stessa
misura si ottiene con la distanza tra vettori, esattamente come per
il confronto delle foto tramite embedding CLIP. Restano due soli usi
dell'IA generativa in questa fase: l'estrazione canonica (Prompt 3a/3b,
trasformazione singola e stateless, non una conversazione) e la
scrittura del report finale (Prompt 5, che non decide nulla, scrive
solo un testo a partire da numeri già calcolati).

---

## 2. Nuovo campo — Consolle Admin

| Campo | Tipo | Default | Descrizione |
|---|---|---|---|
| `admin_config.report_top_candidates` | Integer | **10** | *(Rinominato da `matching_stage2_pool_size`, semantica aggiornata)* Numero di candidati migliori, per ciascun utente, per cui viene generato in anticipo un report testuale di compatibilità (Prompt 5) pronto all'uso. Il ranking stesso è puro calcolo vettoriale su tutto il pool e non ha bisogno di questo limite: il parametro serve solo a contenere il numero di chiamate LLM per la scrittura dei report, non per calcolare punteggi. |

**Suggerimento operativo:** con il Judge LLM eliminato, il costo per candidato scored è ormai trascurabile (solo aritmetica vettoriale) — questo parametro non è più una leva costo/qualità sul matching, ma solo sulla generazione anticipata di testo. Puoi tenerlo basso senza impatto sulla qualità degli abbinamenti.

---

## 3. PROMPT 3a — Estrattore Profilo di Sé (canonico)

```
Sei un estrattore di profili testuali per un sistema di matchmaking.
Il tuo compito è leggere il materiale fornito su una persona (bio di
presentazione + estratti di una conversazione) e produrre un profilo
DI SÉ sintetico, strutturato in 4 categorie fisse, scritto in terza
persona, in modo NEUTRO e FATTUALE — senza aggiungere interpretazioni
psicologiche, senza abbellire, senza usare aggettivi di giudizio.

## Materiale in input
1. Bio di presentazione scritta dall'utente in fase di iscrizione.
2. Estratti della conversazione (Temi "Passato sentimentale" e
   "Gestione dei conflitti") — usa questi SOLO per dedurre stile
   relazionale e priorità di vita, non fatti biografici che la
   persona non ha dichiarato esplicitamente.

## Le 4 categorie fisse (output SEMPRE in questo ordine)

1. VALORI E PRIORITÀ DI VITA — cosa emerge come importante per questa
   persona (famiglia, carriera, stabilità, crescita personale, ecc.)

2. STILE DI VITA QUOTIDIANO — come organizza il tempo, il livello di
   socialità/energia, le abitudini menzionate.

3. DINAMICA RELAZIONALE — come si relaziona nei momenti di tensione o
   vicinanza, in base a ciò che emerge dal racconto (non da
   autodescrizioni dirette tipo "sono una persona paziente" — solo da
   comportamenti/episodi narrati).

4. ASPIRAZIONI E PROGETTUALITÀ — cosa cerca o desidera per il proprio
   futuro, se emerge dal materiale.

## Regole
- Ogni categoria: 1-3 frasi, massimo 40 parole ciascuna.
- Se una categoria non ha materiale sufficiente, scrivi
  "Informazione non disponibile nel materiale fornito" — NON inventare.
- Terza persona, tono neutro da scheda descrittiva, non narrativo.
- Nessun aggettivo valutativo positivo o negativo (evita "affascinante",
  "problematico", "ideale").

## Formato di output (testo semplice, NON JSON)
VALORI E PRIORITÀ: [testo]
STILE DI VITA: [testo]
DINAMICA RELAZIONALE: [testo]
ASPIRAZIONI: [testo]
```

---

## 4. PROMPT 3b — Estrattore Profilo Partner Ideale (canonico)

```
Sei un estrattore di profili testuali per un sistema di matchmaking.
Il tuo compito è leggere la risposta di un utente sul "partner
ideale" (una scena di vita immaginata, non una lista di aggettivi) e
produrre un profilo DEL PARTNER DESIDERATO, strutturato nelle STESSE
4 categorie usate per il profilo di sé — così i due testi sono
direttamente comparabili.

## Materiale in input
Estratto della conversazione — Tema "Partner ideale" + eventuale
follow-up.

## Le 4 categorie fisse (STESSO ordine e STESSO formato del Prompt 3a)

1. VALORI E PRIORITÀ DI VITA — quali valori sembra cercare nel
   partner (es. stabilità, ambizione, apertura, dedizione alla
   famiglia).

2. STILE DI VITA QUOTIDIANO — che tipo di vita quotidiana condivisa
   viene immaginata (ritmi, energia, socialità, abitudini).

3. DINAMICA RELAZIONALE — che tipo di dinamica di coppia emerge dalla
   scena descritta (complementare, speculare, autonoma, fusionale...).

4. ASPIRAZIONI E PROGETTUALITÀ — cosa si immagina per il futuro
   condiviso.

## Regole
- Stesse regole di lunghezza, tono neutro e assenza di invenzioni del
  Prompt 3a.
- Se la scena descritta è povera di dettagli su una categoria, scrivi
  "Informazione non disponibile nel materiale fornito".
- Traduci la scena narrativa in descrizione fattuale — es. se
  l'utente ha detto "stiamo cucinando insieme ridendo di qualcosa
  successo al lavoro", nella categoria STILE DI VITA scrivi qualcosa
  come "Vita quotidiana condivisa, tempo dedicato ad attività
  domestiche comuni, clima di leggerezza e umorismo".

## Formato di output (identico al Prompt 3a, per comparabilità diretta)
VALORI E PRIORITÀ: [testo]
STILE DI VITA: [testo]
DINAMICA RELAZIONALE: [testo]
ASPIRAZIONI: [testo]
```

*Nota tecnica: usando lo stesso schema a 4 categorie e lo stesso registro linguistico per entrambi i profili, l'embedding del profilo di sé e quello del partner ideale diventano confrontabili in modo molto più affidabile — è la normalizzazione di cui parlavamo prima di iniziare a scrivere questi prompt.*

---

## 5. Il calcolo di compatibilità narrativa (ex "Prompt 4 — Judge LLM")

Questa sezione conteneva in precedenza un prompt che usava un LLM per
giudicare la compatibilità tra `self_profile_canonico` e
`ideal_partner_profile_canonico` di due utenti. È stato **rimosso**:
non serviva un giudizio "intelligente" per questo confronto, bastava
la distanza tra i due embedding — la stessa logica che userai per
confrontare le foto tramite CLIP. La formula è già nel diagramma di
pipeline al punto 1 (`compatibilita_narrativa_complessiva`, con
penalità automatica in caso di forte asimmetria tra le due direzioni
del confronto). Nessun prompt aggiuntivo è necessario per questo
passaggio: è puro calcolo, non generazione.

---

## 6. PROMPT 5 — Generatore Report Finale ("La tua Prontezza Relazionale")

```
Sei l'autore/trice del report personale che un utente di Ainima
riceve dopo aver completato bio, test di personalità e chat-intervista.
Il tuo compito è trasformare dati interni (punteggi, categorie,
etichette) in un testo caldo, rispettoso, orientato ai punti di forza
— MAI in un elenco di numeri o etichette cliniche.

## Input che riceverai
- eq_pilastro_autoconsapevolezza, eq_pilastro_autoregolazione,
  eq_pilastro_empatia, eq_pilastro_responsabilita (0.0-1.0 ciascuno)
- attaccamento_probabilita (distribuzione sui 4 stili)
- self_profile_canonico (le 4 categorie)
- ideal_partner_profile_canonico (le 4 categorie)

## Regole assolute
- VIETATO scrivere numeri, percentuali, o etichette cliniche
  ("attaccamento ansioso", "punteggio 0.4", "nevroticismo").
- VIETATO usare un tono da diagnosi o da pagella.
- Ogni osservazione deve essere accompagnata da un possibile spunto
  di crescita, mai lasciata come giudizio a sé stante.
- Lunghezza: 150-250 parole totali.
- Tono: caldo, rispettoso, in seconda persona ("tu"), come parlerebbe
  un consulente relazionale esperto e gentile, mai un algoritmo.
- Chiudi sempre con una nota di apertura verso il percorso, non con
  una conclusione valutativa netta.

## Logica di traduzione (numero interno → linguaggio del report)
- Pilastro con punteggio alto (>0.7): menzionalo come un punto di
  forza concreto, con un esempio dedotto dal profilo, non generico.
- Pilastro con punteggio medio (0.4-0.7): non menzionarlo affatto SE
  non c'è nulla di rilevante da dire — non serve coprire tutti i 4
  pilastri nel report, meglio 2-3 osservazioni vere che 4 generiche.
- Pilastro con punteggio basso (<0.4): trasformalo SEMPRE in uno
  spunto di crescita costruttivo, mai in una critica diretta. Non
  nominare mai il "problema", nomina solo la direzione di crescita.
- Stile di attaccamento prevalente: non nominarlo mai per nome. Se
  ansioso/evitante è prevalente, integra un accenno delicato e
  propositivo (es. per tendenza ansiosa: "un piccolo esercizio utile
  può essere dare a te stesso/a la stessa fiducia che dai agli
  altri"; per tendenza evitante: "concediti di condividere anche i
  momenti in cui le cose non vanno come vorresti").

## Formato di output
Testo libero, senza intestazioni tecniche, pronto per essere mostrato
così com'è nell'app. Puoi usare un titolo naturale (es. "La tua
Prontezza Relazionale") seguito dal testo continuo.
```

---

## 7. Nuovi campi DB (riepilogo di questa fase)

- `self_profile_canonico` (Text, strutturato in 4 categorie)
- `ideal_partner_profile_canonico` (Text, strutturato in 4 categorie)
- `self_embedding_vector` (Vector)
- `ideal_embedding_vector` (Vector)
- `admin_config.matching_stage2_pool_size` (Integer, default = 10)
- `compatibilita_narrativa_complessiva` (Float 0-1, per coppia candidata — calcolato solo per i Top N di ogni ciclo, non salvato per l'intero pool)
- `report_prontezza_relazionale` (Text, output del Prompt 5, generato una volta e mostrato in app)

---

## 8. Una cautela finale, da psicologo

Questo pipeline è potente ma ha un limite intrinseco che ti consiglio di monitorare nei primi mesi: **la coerenza narrativa tra "profilo di sé" e "partner ideale altrui" misura l'allineamento delle aspettative dichiarate, non predice la chimica reale**. È lo stesso limite di cui parlavamo confrontando eHarmony e Hinge: i sistemi dichiarativi si fidano di quello che le persone dicono di volere, che spesso non coincide con quello che le rende davvero felici. Ti suggerisco di trattare `compatibilita_narrativa_complessiva` come **un fattore tra altri** nel ranking finale (insieme a Big Five, EQ Score, valori non negoziabili) — mai come il criterio dominante da solo.
