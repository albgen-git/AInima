# AInima — Guida di stile

Riferimento rapido per costruire il sito (e qualunque altro materiale) in modo coerente con il volantino e il posizionamento del brand: agenzia matrimoniale seria, guidata dall'IA — non un'app di dating.

---

## 1. Identità in una frase

**AInima** ascolta chi sei davvero e propone, con cura, un incontro alla volta — non uno scorrimento infinito di profili.

Tono: caldo, sobrio, fiducioso. Mai giocoso/frizzante come le app di dating, mai freddo/corporate come un software gestionale.

---

## 2. Colori

| Ruolo | Nome | Hex | Uso |
|---|---|---|---|
| Sfondo principale | Avorio | `#F6F1E7` | Sfondo di pagina, sostituisce il bianco puro |
| Sfondo card/superfici | Avorio chiaro | `#FBF8F1` | Card, form, riquadri su sfondo avorio |
| Testo / sezioni scure | Blu notte | `#1B2340` | Titoli, testo primario, footer, sezioni a contrasto |
| Accento | Oro antico | `#B8934A` | CTA primarie, dettagli editoriali, numeri di sequenza — **con parsimonia** |
| Testo secondario | Grigio ardesia | `#45465A` | Paragrafi, didascalie, testo di supporto |
| Successo/conferma | Salvia | `#6B8F71` | Stati positivi (es. "iscrizione confermata") |
| Errore/attenzione | Terracotta | `#A34A3D` | Errori di form, avvisi — mai rosso semaforo puro |

**Regole d'uso:**
- L'oro (`#B8934A`) va riservato a elementi grandi e rari: bottone principale, numerazioni (I / II / III), piccoli dettagli grafici. Su testo piccolo o link diffusi perde leggibilità.
- Il blu notte su avorio (e viceversa) è la coppia a massimo contrasto: usala per tutto ciò che deve essere letto senza sforzo.
- Non introdurre altri colori saturi (blu tech, verde acceso, viola) — rompono la coerenza boutique.

---

## 3. Tipografia

| Ruolo | Font consigliato | Fallback | Note |
|---|---|---|---|
| Titoli / display | **Lora** (Google Fonts) | Georgia, serif | Stesso font usato nel volantino — coerenza garantita |
| Corpo testo / UI | **Karla** (Google Fonts) | Inter, sans-serif | Pulito, caldo, non "tech-generico" |
| Corsivo editoriale | Lora *italic* | — | Solo per frasi-chiave (headline, pull quote), mai per paragrafi lunghi |

**Scala tipografica** (base 16px, rapporto ~1.25):

| Livello | Dimensione | Peso | Font |
|---|---|---|---|
| Display / H1 | 40-48px | 600 | Lora |
| H2 | 28-32px | 600 | Lora |
| H3 | 20-22px | 600 | Lora |
| Corpo | 16px | 400 | Karla |
| Corpo piccolo / didascalie | 13-14px | 400 | Karla |
| Eyebrow / label | 12px, +1.5px letter-spacing, maiuscolo | 600 | Karla |

Interlinea: 1.3 per i titoli, 1.6 per il corpo testo.

---

## 4. Spaziatura e layout

Unità base: **8px**. Usa multipli: 8, 16, 24, 32, 48, 64, 96.

- Padding interno card/bottoni: 16-24px
- Spazio tra sezioni della pagina: 64-96px
- Larghezza massima testo leggibile: ~640-720px (non far correre i paragrafi su tutto lo schermo)

**Raggio angoli:**
- Bottoni, input, badge: 6-8px
- Card: 12-16px
- Elementi decorativi tondi (avatar, badge circolari): 50%

---

## 5. Componenti base

**Bottone primario**
Sfondo `#B8934A`, testo `#FBF8F1`, padding 12px 24px, radius 8px. Uno solo per schermata — è l'azione che vuoi davvero che l'utente compia (es. "Iscriviti alla waitlist").

**Bottone secondario**
Sfondo trasparente, bordo 1px `#1B2340`, testo `#1B2340`. Per azioni di supporto ("Scopri come funziona").

**Card**
Sfondo `#FBF8F1`, bordo 0.5px `#E4DBC6`, radius 12px, padding 24px. Nessuna ombra pesante — al massimo un'ombra bassissima (`0 1px 3px rgba(27,35,64,0.06)`).

**Form/input**
Bordo 1px `#D9CBA8` a riposo, `#1B2340` al focus (mai il blu default del browser). Placeholder in grigio ardesia, mai in oro (troppo debole).

**Badge/numerazione fasi**
Numeri romani (I, II, III) in Lora, colore oro su sfondo scuro o blu notte su sfondo chiaro — coerente col volantino, più elegante di "01/02/03".

---

## 6. Microcopy — parole da usare e da evitare

Coerenza col posizionamento "agenzia matrimoniale seria", non app di dating:

| Evita | Usa invece |
|---|---|
| Swipe, mi piace, match (da solo) | Proposta, incontro, abbinamento |
| Chat, messaggi | Contatto, presentazione |
| Profili, sfoglia | Persone, presentazioni curate |
| "Trova l'amore" (generico) | "Costruisci qualcosa di vero" |

Bottoni: verbo all'infinito o imperativo, breve, senza punto finale ("Iscriviti alla waitlist", non "Iscriviti alla waitlist ora!").
Errori: dire cosa è successo e cosa fare, tono pacato, mai "Errore:" secco.

---

## 7. Accessibilità — controlli minimi

- Testo blu notte su avorio: contrasto molto alto, ok ovunque.
- Testo oro su avorio chiaro: contrasto insufficiente per testo piccolo — usa l'oro solo su sfondo scuro o per elementi grandi (bottoni pieni con testo chiaro sopra, non testo dorato su chiaro).
- Dimensione minima testo: 13px, mai sotto.
- Ogni elemento interattivo (bottoni, link, input) deve avere uno stato di focus visibile — bordo blu notte, non l'outline blu default del browser.

---

## 8. Cosa NON fare

- Niente gradienti, ombre pesanti, effetti neon o glassmorphism — l'estetica è piatta e sobria.
- Niente emoji nell'interfaccia o nelle comunicazioni.
- Niente verde/rosso semaforo standard per stati di successo/errore — usa salvia e terracotta.
- Non riempire la pagina di oro: è un accento, non un colore di sfondo.
