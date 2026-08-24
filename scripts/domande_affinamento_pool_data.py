"""Dati sorgente per domande_affinamento_pool (Blocco E — v. CLAUDE.md,
Ainima_Engagement_Periodico_v1_BOZZA.md §2.1 "Item di riserva").

20 item psicometrici reali, rimossi durante l'accorciamento di Big Five
(50->40), Attaccamento (24->18) ed EQ Score (32->24) — validi, non
fittizi, semplicemente spostati fuori dall'onboarding per lunghezza.
Ognuno verificato PAROLA PER PAROLA contro il codice realmente servito
prima del taglio (non contro appunti o cronologia di conversazione):

- Attaccamento (6) ed EQ (8): recuperati da `git show HEAD:...` sui file
  attaccamentoItems.ts/eqItems.ts — il commit iniziale del repo cattura
  ancora la versione pre-Blocco-B (24/32 item), prima del taglio.
- Big Five (6): il commit iniziale cattura già la versione POST-taglio
  (40 item, non 50) — non utilizzabile per questo confronto. Recuperato
  invece dalla cache di build Turbopack
  (frontend/.next/dev/server/chunks/ssr/*.js.map), che conteneva ancora
  il sorgente completo del vecchio file a 50 item (stesso artefatto già
  notato altrove in CLAUDE.md), riservato realmente da Turbopack a un
  browser in una sessione precedente — non un abbozzo, il file reale.

Altri 4 item Big Five proposti inizialmente (dall'autore della specifica)
sono stati SCARTATI dopo verifica: non comparivano in nessuna delle 50
righe originali estratte dalla cache. Confermato dall'autore stesso:
provenivano da uno stadio di bozza intermedio mai sincronizzato al codice
— non possono essere descritti come "rimossi dall'onboarding" perché non
ci sono mai entrati (v. CLAUDE.md per la cronologia completa della
verifica).

Il flag "reverse" (item invertito, ricodificare 6-punteggio_grezzo prima
di entrare nella media della dimensione) riflette quanto dichiarato dalla
fonte — non è stato riverificato contro la costante REVERSE_ITEMS del
file schemas/psychometric.py precedente al taglio (non recuperata in
questa verifica, a differenza del testo degli item). Da confermare in
fase di re-implementazione se questi item torneranno mai a essere
scorati dal vivo.
"""

DOMANDE_AFFINAMENTO_POOL = [
    # ── Big Five (6) — verificati contro la cache Turbopack del vecchio bigFiveItems.ts a 50 item ──
    {
        "codice_originale": "O4", "test_origine": "bigfive", "dimensione": "apertura", "reverse": True,
        "testo_it": "Trovo faticoso e poco utile discutere di idee astratte.",
        "testo_en": "I find discussing abstract ideas tiring and not very useful.",
    },
    {
        "codice_originale": "C10", "test_origine": "bigfive", "dimensione": "coscienziosita", "reverse": True,
        "testo_it": "Vivo alla giornata, senza preoccuparmi troppo della pianificazione futura.",
        "testo_en": "I live day to day, without worrying much about future planning.",
    },
    {
        "codice_originale": "E5", "test_origine": "bigfive", "dimensione": "estroversione", "reverse": True,
        "testo_it": "Evito di espormi quando è necessario esprimere un'opinione forte davanti ad altri.",
        "testo_en": "I avoid putting myself out there when a strong opinion needs to be voiced in front of others.",
    },
    {
        "codice_originale": "E10", "test_origine": "bigfive", "dimensione": "estroversione", "reverse": True,
        "testo_it": "Tendo a essere riservato/a finché non conosco bene qualcuno.",
        "testo_en": "I tend to be reserved until I get to know someone well.",
    },
    {
        "codice_originale": "C5", "test_origine": "bigfive", "dimensione": "coscienziosita", "reverse": True,
        "testo_it": "Capita spesso che io rimandi le cose all'ultimo momento.",
        "testo_en": "I often put things off until the last moment.",
    },
    {
        "codice_originale": "O6", "test_origine": "bigfive", "dimensione": "apertura", "reverse": True,
        "testo_it": "Un cambiamento improvviso nei miei piani mi mette a disagio più che incuriosirmi.",
        "testo_en": "A sudden change in my plans unsettles me more than it intrigues me.",
    },
    # ── Attaccamento (6) — verificati con git show HEAD:attaccamentoItems.ts (24 item, pre-Blocco-B) ──
    {
        "codice_originale": "EV8", "test_origine": "attaccamento", "dimensione": "evitamento", "reverse": True,
        "testo_it": "Provo piacere nel sentirmi vicino/a emotivamente al partner.",
        "testo_en": "I enjoy feeling emotionally close to my partner.",
    },
    {
        "codice_originale": "AN4", "test_origine": "attaccamento", "dimensione": "ansia_abbandono", "reverse": True,
        "testo_it": "Mi sento sicuro/a del legame anche senza continue conferme.",
        "testo_en": "I feel secure in the bond even without constant confirmation.",
    },
    {
        "codice_originale": "AN8", "test_origine": "attaccamento", "dimensione": "ansia_abbandono", "reverse": True,
        "testo_it": "Non mi sento in ansia quando il partner trascorre del tempo lontano da me.",
        "testo_en": "I don't feel anxious when my partner spends time away from me.",
    },
    {
        "codice_originale": "AN12", "test_origine": "attaccamento", "dimensione": "ansia_abbandono", "reverse": True,
        "testo_it": "Non ho bisogno di sapere costantemente cosa pensa di me il mio partner.",
        "testo_en": "I don't need to constantly know what my partner thinks of me.",
    },
    {
        "codice_originale": "EV4", "test_origine": "attaccamento", "dimensione": "evitamento", "reverse": True,
        "testo_it": "Cerco attivamente intimità e vicinanza con il partner.",
        "testo_en": "I actively seek intimacy and closeness with my partner.",
    },
    {
        "codice_originale": "EV12", "test_origine": "attaccamento", "dimensione": "evitamento", "reverse": True,
        "testo_it": "Mi sento a mio agio nel chiedere supporto al mio partner quando ne ho bisogno.",
        "testo_en": "I feel comfortable asking my partner for support when I need it.",
    },
    # ── EQ Score (8) — verificati con git show HEAD:eqItems.ts (32 item, pre-Blocco-B) ──
    {
        "codice_originale": "AR5", "test_origine": "eq", "dimensione": "autoregolazione", "reverse": True,
        "testo_it": "Tendo ad agire d'impulso quando sono contrariato/a, per poi pentirmene.",
        "testo_en": "I tend to act on impulse when upset, and regret it afterward.",
    },
    {
        "codice_originale": "AC6", "test_origine": "eq", "dimensione": "autoconsapevolezza", "reverse": True,
        "testo_it": "Preferisco non pensare troppo al motivo per cui provo certe emozioni.",
        "testo_en": "I prefer not to think too much about why I feel certain emotions.",
    },
    {
        "codice_originale": "AC8", "test_origine": "eq", "dimensione": "autoconsapevolezza", "reverse": True,
        "testo_it": "Mi rendo conto delle mie vere motivazioni solo molto tempo dopo, se mai lo faccio.",
        "testo_en": "I realize my true motivations only long afterward, if ever.",
    },
    {
        "codice_originale": "AR7", "test_origine": "eq", "dimensione": "autoregolazione", "reverse": True,
        "testo_it": "Le critiche, anche costruttive, mi mandano fuori controllo più di quanto vorrei.",
        "testo_en": "Criticism, even constructive, throws me off more than I'd like.",
    },
    {
        "codice_originale": "EM6", "test_origine": "eq", "dimensione": "empatia", "reverse": True,
        "testo_it": "In una discussione, il mio obiettivo principale è far valere il mio punto di vista.",
        "testo_en": "In an argument, my main goal is to make my point of view prevail.",
    },
    {
        "codice_originale": "EM8", "test_origine": "eq", "dimensione": "empatia", "reverse": True,
        "testo_it": "Non capisco perché dovrei preoccuparmi di come si sente qualcuno se non l'ha detto apertamente.",
        "testo_en": "I don't see why I should worry about how someone feels if they haven't said so openly.",
    },
    {
        "codice_originale": "RE6", "test_origine": "eq", "dimensione": "responsabilita", "reverse": True,
        "testo_it": "Tendo a ricordare più facilmente gli errori degli altri che i miei.",
        "testo_en": "I tend to remember others' mistakes more easily than my own.",
    },
    {
        "codice_originale": "RE8", "test_origine": "eq", "dimensione": "responsabilita", "reverse": True,
        "testo_it": "Quando qualcuno mi fa una critica, la mia prima reazione è difendermi.",
        "testo_en": "When someone criticizes me, my first reaction is to defend myself.",
    },
]

assert len(DOMANDE_AFFINAMENTO_POOL) == 20
assert sum(1 for d in DOMANDE_AFFINAMENTO_POOL if d["test_origine"] == "bigfive") == 6
assert sum(1 for d in DOMANDE_AFFINAMENTO_POOL if d["test_origine"] == "attaccamento") == 6
assert sum(1 for d in DOMANDE_AFFINAMENTO_POOL if d["test_origine"] == "eq") == 8
