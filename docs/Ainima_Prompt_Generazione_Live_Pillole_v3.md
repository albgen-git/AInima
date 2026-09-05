# Ainima — Prompt Generazione Live Pillole (v3, via CRON)
### Una pillola per esecuzione — sostituisce l'approccio batch per l'MVP

---

## 1. Cosa cambia rispetto al batch

Generazione diretta a ogni esecuzione del CRON, senza revisione umana
preventiva — scelta accettata per velocità in fase MVP. Nessun
problema di sicurezza nuovo (nessun input utente nel prompt, come già
chiarito). Il compromesso reale è editoriale: senza un umano che
legge prima, serve un **controllo automatico leggero** che intercetti
almeno le violazioni meccaniche (frasi vietate, lunghezza) prima che
il testo entri in `pillole_libreria` — vedi §3.

**Cambio strutturale importante:** il controllo di varietà non può più
confrontare pillole tra loro nello stesso lotto (non esiste un lotto,
una sola pillola per esecuzione). Il prompt riceve invece **lo storico
delle ultime pillole generate** e deve esplicitamente evitare di
ripetere tecnica, apertura o dominio di metafora rispetto a quelle.

---

## 2. PROMPT — Generazione Singola con Anti-Ripetizione da Storico

```
Sei un editor che scrive contenuto breve ed educativo per Ainima, un
servizio di matchmaking matrimoniale basato su un approccio riflessivo
e maturo, non una app di dating. Scrivi UNA pillola — un testo breve
(40-70 parole) su intelligenza emotiva, comunicazione, valori o
preparazione a una relazione seria. General purpose: non
personalizzata su nessun dato specifico di un utente.

## Storico delle ultime pillole generate (evita di ripeterle)
[qui va inserito un array delle ultime 8-10 pillole: titolo, pilastro,
contesto, tecnica_usata, tema_centrale — se lo storico è vuoto (prima
esecuzione), procedi liberamente]

## Cosa evitare rispetto allo storico
- Non usare la stessa tecnica (vedi lista sotto) delle ultime 2 pillole.
- Non toccare lo stesso pilastro delle ultime 2, se possibile bilancia
  verso il pilastro meno rappresentato nello storico.
- **Non riusare lo stesso `tema_centrale` (vedi sotto) di NESSUNA delle
  ultime 8-10 pillole nello storico** — non solo le ultime 2. Se il tuo
  tema_centrale coincide anche solo come sinonimo o variante
  grammaticale con uno già presente nello storico (es. "silenzio" e
  "silenzioso" contano come lo stesso tema), scegline un altro prima
  di scrivere il testo.
- Se un dominio di metafora (natura, cucina, musica, meccanica,
  artigianato, ecc.) coincide con quello implicito nel `tema_centrale`
  di una pillola recente, scegline uno diverso.
- Non aprire con una struttura di frase simile a nessuna delle ultime 3.
- Le formule di esempio elencate nella sezione tecniche sotto (es.
  "Capita spesso che...") sono SOLO illustrazioni della categoria, MAI
  da riusare testualmente — se la tua apertura coincide quasi
  letteralmente con un esempio del prompt, riscrivila.

## Le 4 categorie (pilastro)
- Intelligenza Emotiva (autoconsapevolezza, gestione dell'ansia, traumi)
- Comunicazione & Conflitto (ascolto attivo, confini, disaccordi)
- Cultura e Valori (integrazione, famiglia, tradizioni)
- Preparazione al Matrimonio (finanze, ruoli, progetti di vita)

## I 3 contesti
- Attesa generale (nessun match attivo — default se non specificato)
- Post-match confermato, pre primo appuntamento
- Post-rifiuto (tono più delicato, di supporto)

## Le 6 tecniche (scegline una, diversa dalle ultime 2 dello storico)
1. Domanda diretta e scomoda (non retorica)
2. Piccolo scenario concreto ("Capita spesso che...")
3. Osservazione controintuitiva
4. Metafora da un dominio lontano (non viaggio/giardino/ponte — sono
   già abusati nel genere, evitali sempre, storico o no)
5. Contrasto netto ("Non è X, è Y")
6. Consiglio pratico diretto, senza preamboli

## Frasi/aperture SEMPRE vietate (indipendentemente dallo storico)
- "Hai mai pensato/notato che..."
- "È normale sentirsi..."
- "La chiave è..." / "Il segreto è..."
- "Ricorda che..." / "Non dimenticare che..."
- "Nella vita di coppia..."
- Domande retoriche con risposta ovvia ("Ti è mai capitato di...")

## Regole di tono
- Mai un'etichetta clinica o diagnostica.
- Mai un imperativo moralistico ("Devi imparare a...").
- Nessun riferimento a una situazione di coppia specifica reale.
- Linguaggio neutro e internazionale.
- Va bene essere un po' spiazzanti o giocosi quando il tema lo permette.

## Formato di output (JSON, un solo oggetto)
{
  "titolo": "breve, 4-8 parole",
  "testo": "40-70 parole",
  "pilastro": "intelligenza_emotiva | comunicazione_conflitto | cultura_valori | preparazione_matrimonio",
  "contesto": "attesa_generale | post_match | post_rifiuto",
  "tecnica_usata": "una delle 6 sopra",
  "tema_centrale": "1-2 parole che catturano l'immagine o il concetto
    portante della pillola (es. 'silenzio', 'manutenzione', 'bussola',
    'confini') — usato SOLO per il controllo anti-ripetizione delle
    prossime generazioni, non mostrato mai all'utente"
}
```

---

## 3. Controllo automatico leggero prima della pubblicazione (sostituisce la revisione umana per l'MVP)

Senza un umano nel loop, questi controlli meccanici vanno eseguiti in
codice subito dopo la generazione, prima dell'insert in
`pillole_libreria`:

```
SE lunghezza(testo) < 30 parole O > 90 parole: scarta, rigenera
SE testo inizia con una delle frasi vietate (match case-insensitive
   su prefissi): scarta, rigenera
SE tecnica_usata coincide con una delle ultime 2 nello storico: scarta, rigenera
SE tema_centrale coincide (anche come sinonimo/variante grammaticale
   semplice, es. "silenzio"/"silenzioso") con una delle ultime 8-10
   pillole nello storico: scarta, rigenera
SE pilastro coincide con quello delle ultime 2 nello storico E
   esistono pilastri meno rappresentati: scarta, rigenera
SE JSON malformato o campo mancante: scarta, rigenera (max 3 tentativi,
   poi alert per revisione manuale — unico caso in cui serve un umano)
```

Questo non sostituisce del tutto il giudizio umano (tono, qualità
reale del contenuto, coerenza col brand) — ma intercetta le violazioni
meccaniche delle regole senza bisogno di un umano ad ogni esecuzione.
Consiglio comunque una lettura umana a campione (es. 1 pillola su 10)
anche nell'MVP, non per approvarle prima della pubblicazione ma per
accorgersi presto se la qualità sta scendendo.

---

## 4. Esempi approvati (riferimento di tono/qualità, 2026-09-05)

Cinque pillole generate e approvate da Alberto — riferimento di calibrazione
per tono e qualità attesi, **non da riusare direttamente** (rischierebbero
proprio la ripetizione che il meccanismo anti-ripetizione vuole evitare).

#### #1 — Pilastro: Comunicazione & Conflitto — Contesto: Attesa generale — Tecnica: Contrasto netto

**Non è chi urla, è chi sparisce**
Il conflitto più difficile da riparare spesso non è quello acceso, ma quello silenzioso — la frase lasciata a metà, la porta chiusa senza spiegazioni. Chi urla lascia almeno qualcosa da affrontare. Chi sparisce lascia solo un vuoto da interpretare, ed è lì che nascono i fraintendimenti più duraturi.

#### #2 — Pilastro: Preparazione al Matrimonio — Contesto: Attesa generale — Tecnica: Piccolo scenario concreto

**Il primo conto in comune**
Capita spesso che due persone parlino di sogni condivisi molto prima di parlare di come dividere una bolletta imprevista. Eppure è proprio in quella conversazione minore — chi paga cosa, come si decide una spesa grande — che si vede quanto due visioni del futuro sanno davvero incastrarsi.

#### #3 — Pilastro: Intelligenza Emotiva — Contesto: Post-match confermato — Tecnica: Metafora da dominio lontano (artigianato)

**Come un vaso al tornio**
Un ceramista non forza la forma del vaso: la asseconda, correggendo con pazienza mentre gira. Nelle prime conversazioni con una persona nuova vale lo stesso principio — meno si cerca di dirigere tutto verso un risultato preciso, più la forma naturale della relazione ha spazio per emergere.

#### #4 — Pilastro: Cultura e Valori — Contesto: Attesa generale — Tecnica: Domanda diretta e scomoda

**Quanto del "noi" viene da fuori?**
Quante delle cose che consideri non negoziabili in una relazione vengono davvero da te, e quante da ciò che la tua famiglia o il tuo ambiente ti hanno insegnato ad aspettarti? Non è una domanda con una risposta comoda, ma vale la pena farsela prima di scoprirla nel momento sbagliato.

#### #5 — Pilastro: Comunicazione & Conflitto — Contesto: Post-rifiuto — Tecnica: Consiglio pratico diretto

**Una domanda, non un verdetto**
Se un incontro non è andato come speravi, prova a chiederti una cosa sola: cosa hai imparato su cosa cerchi davvero, non su cosa è andato storto. Trasforma il rifiuto da giudizio su di te a informazione su di te — è una differenza piccola nelle parole, grande nell'effetto.
