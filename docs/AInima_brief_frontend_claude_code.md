# Brief frontend AInima — per Claude Code

Incolla questo (o riassumilo) come prompt iniziale, o meglio: salvalo come `FRONTEND.md` nella cartella del progetto AInima, così Claude Code lo trova automaticamente a inizio sessione.

## Stack

- Backend: FastAPI (già definito)
- Rendering pagine: **Jinja2** — niente SPA separata per l'MVP, un solo progetto da deployare
- Styling: **Tailwind CSS**, configurato con i token in `ainima-tokens.css` (allegato)
- Interattività: **HTMX** per le parti dinamiche (colloquio IA a step, validazione form, aggiornamenti senza reload completo della pagina) — non aggiungere React/Vue a meno che non lo chieda esplicitamente
- Font: **Lora** (titoli) + **Karla** (corpo testo), da Google Fonts

## Cosa costruire per l'MVP (in ordine di priorità)

1. **Landing page / waitlist**: headline, sotto-headline, form email, come funziona (3 step), CTA — coerente col volantino già fatto
2. **Onboarding**: test Big Five (50 item) + colloquio IA testuale (HTMX per gli scambi dinamici)
3. **Report "Prontezza Relazionale"**: pagina di risultato, tono caldo, nessun punteggio/etichetta clinica visibile
4. **Rubrica**: elenco dei match passati, download vCard
5. **Area admin**: separata, può essere più spartana/funzionale — non serve la stessa cura estetica del prodotto rivolto all'utente

## Vincoli di design (dal brand)

- Palette, font, spaziature: usa **esattamente** i valori in `ainima-tokens.css` — non lasciare che vengano reinterpretati o approssimati
- Niente gradienti, ombre pesanti, glassmorphism — superfici piatte
- L'oro (`--color-gold`) solo su bottoni pieni o sfondo scuro — mai come colore di testo su sfondo chiaro (contrasto insufficiente)
- Mobile-first: la maggior parte del traffico da flyer/social sarà da telefono — testare prima lo stretto (360-390px), poi allargare
- Focus visibile su ogni elemento interattivo (bordo blu notte), mai l'outline blu default del browser
- Microcopy: mai "swipe", "mi piace", "match" da solo, "profili" — usa "proposta", "incontro", "presentazione" (vedi guida di stile per il glossario completo)

## Cosa NON fare

- Non introdurre librerie UI pesanti (Bootstrap, Material UI) — Tailwind puro è sufficiente e più coerente con un'estetica su misura
- Non usare emoji nell'interfaccia
- Non implementare verifica documenti/identità (esplicitamente esclusa dal prodotto)
- Non hardcodare colori/font — sempre dai token in `ainima-tokens.css`

## File allegati da mettere nel progetto

- `ainima-tokens.css` — variabili CSS + snippet config Tailwind
- `AInima_guida_stile.md` — guida di stile completa (tono, componenti, accessibilità)
