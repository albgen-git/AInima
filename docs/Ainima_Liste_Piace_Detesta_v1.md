# Ainima — Liste "Mi Piace / Non Sopporto" e "Partner Vorrei / Non Vorrei" (v1)
### Bozza di lavoro — a cura dello psicologo del progetto

---

## 1. I 4 campi

| Campo | Esempio | Cosa descrive |
|---|---|---|
| `mi_piace` | "gatti, animali, cucina, montagna" | Interessi/tratti positivi di sé |
| `non_sopporto` | "maleducazione, ritardi cronici" | Cose che la persona rifiuta in generale |
| `partner_vorrei` | "empatia, curiosità, sport" | Cosa cerca esplicitamente nel partner |
| `partner_non_vorrei` | "avarizia, arroganza, gelosia" | Dealbreaker espliciti sul partner |

Testo libero, separato da virgola. Nessuna chat, nessuna conversazione
— stesso principio di sicurezza già adottato per gli altri campi
liberi del progetto, con superficie di rischio ancora più bassa: sono
liste corte, non narrativa.

---

## 2. Pipeline di elaborazione

```
Input utente: "gatti, animali, cucina"
        │
        ▼
Step 1 — Parsing: split su virgola, trim, lowercase, dedup
        → ["gatti", "animali", "cucina"]
        │
        ▼
Step 2 — Embedding per tag, con CACHE CONDIVISA tra tutti gli utenti
        (tabella tag_embedding_cache: tag_normalizzato → vector,
        calcolato una sola volta per ogni tag mai visto, poi riusato)
        │
        ▼
mi_piace_tags = ["gatti", "animali", "cucina"]  (Array, salvato per l'utente)
```

**Nuova tabella:** `tag_embedding_cache` — `tag_normalizzato` (PK, string), `embedding_vector` (Vector), `prima_volta_vista_il` (Timestamp). Condivisa tra tutti gli utenti, cresce lentamente nel tempo (i tag comuni si esauriscono presto).

---

## 3. Funzione di confronto tra liste

```
tag_overlap_score(lista_source, lista_target):
    SE lista_source è vuota: RETURN null   // dato mancante, non 0
    SE lista_target è vuota: RETURN 0.0    // nessuna corrispondenza possibile

    per ogni tag in lista_source:
        miglior_match = max( cosine(embedding(tag), embedding(t)) per t in lista_target )

    RETURN media(miglior_match per ogni tag in lista_source)
```

Confronto **direzionale** (source → target), come per gli altri
confronti già costruiti nel progetto — per questo ogni combinazione va
calcolata in entrambe le direzioni quando rilevante.

---

## 4. Le 3 componenti del punteggio

### 4a. Interessi comuni (bonus, simmetrico)
```
Interessi_Comuni = ( tag_overlap(A.mi_piace, B.mi_piace)
                    + tag_overlap(B.mi_piace, A.mi_piace) ) / 2
```

### 4b. Corrispondenza desideri (bidirezionale)
```
Corrispondenza_Desideri = ( tag_overlap(A.partner_vorrei, B.mi_piace)
                           + tag_overlap(B.partner_vorrei, A.mi_piace) ) / 2
```
Quanto ciò che A cerca esplicitamente compare in ciò che B è/ama, e viceversa.

### 4c. Penalità sui rifiuti espliciti (bidirezionale)
```
lista_rifiuti_A = A.partner_non_vorrei_tags ∪ A.non_sopporto_tags  (unione, dedup)
lista_rifiuti_B = B.partner_non_vorrei_tags ∪ B.non_sopporto_tags

Penalita_Rifiuti = ( tag_overlap(lista_rifiuti_A, B.mi_piace)
                    + tag_overlap(lista_rifiuti_B, A.mi_piace) ) / 2
```
Un dealbreaker dichiarato pesa di più di una semplice assenza di
affinità — per questo è una penalità separata, non solo un punteggio
basso su "Corrispondenza_Desideri".

---

## 5. Formula finale

```
Punteggio_Tag_Liste = clamp(
      (Corrispondenza_Desideri * 0.6)
    + (Interessi_Comuni * 0.4)
    - Penalita_Rifiuti
  , 0.0, 1.0)

// Se una componente è null (liste vuote da entrambe le parti su quel
// campo), escludila dalla media invece di trattarla come 0 — un
// campo non compilato non è un disallineamento, è un dato mancante.

SE Penalita_Rifiuti > 0.7:
    flag_rifiuto_esplicito = true
    // segnale forte: uno dei due è/ama qualcosa che l'altro ha
    // dichiarato esplicitamente di non volere — va reso visibile nel
    // report e/o pesato più di una semplice sottrazione lineare
```

---

## 6. Dove entra nel calcolo finale (Documento 6 — Ranking)

`Punteggio_Tag_Liste` entra come nuova componente dentro lo **Step 4
— Preferenze Soft**, insieme a `Punteggio_Distanza` e agli altri
sotto-punteggi già definiti:

```
Punteggio_Preferenze_Soft = media ponderata di:
  - Punteggio_Distanza
  - Punteggio_Tag_Liste   ← nuovo
  - corrispondenza fascia altezza preferita
  - corrispondenza stile estetico dichiarato
  - corrispondenza livello di attività fisica/sport
  - corrispondenza importanza della religione
```

`flag_rifiuto_esplicito`, se presente, va esposto nel report/admin
allo stesso modo di `flag_asimmetria_narrativa` — un segnale da
mostrare, non da nascondere dentro una media.

---

## 7. Nuovi campi DB

| Campo | Tipo | Note |
|---|---|---|
| `mi_piace`, `non_sopporto`, `partner_vorrei`, `partner_non_vorrei` | Text | Input grezzo dell'utente |
| `mi_piace_tags`, `non_sopporto_tags`, `partner_vorrei_tags`, `partner_non_vorrei_tags` | Array | Dopo parsing/normalizzazione |
| `tag_embedding_cache` | Tabella condivisa | `tag_normalizzato` (PK), `embedding_vector`, `prima_volta_vista_il` |
| `flag_rifiuto_esplicito` | Boolean | Per-coppia, non persistito a lungo termine, esposto nel report/admin |

---

## 8. Una cautela pratica, non solo clinica

**Normalizzazione minima:** anche senza LLM, vale la pena un livello
base di pulizia dati — trim, lowercase, rimozione di caratteri
ripetuti o testo palesemente non pertinente (es. numeri, URL) prima di
calcolare l'embedding. Non serve un filtro sofisticato: basta evitare
che un tag "sporco" inquini silenziosamente la cache condivisa,
usata da tutti gli utenti successivi che scrivono qualcosa di simile.

**Nota psicologica:** le liste `non_sopporto`/`partner_non_vorrei`
tendono a raccogliere anche linguaggio piuttosto carico emotivamente
("arroganza", "menefreghismo"). È un dato utile per il matching, ma
se in futuro decidi di mostrare all'utente un riepilogo di queste
liste (es. in un report), vale la pena passarlo dallo stesso principio
già stabilito per il report EQ: mai restituire un elenco freddo di
"difetti rifiutati", meglio riformulare in positivo ("cerchi una
relazione basata su generosità e rispetto reciproco").
