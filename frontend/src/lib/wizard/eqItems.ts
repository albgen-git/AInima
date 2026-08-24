/**
 * 24 item del test EQ Score (AC1-AC6, AR1-AR6, EM1-EM6, RE1-RE6) + 1 item
 * trappola condiviso ('T3', al confine tra Autoregolazione ed Empatia) =
 * 25 elementi totali, fedeli a docs/Ainima_Test_EQScore_v1.md (v2 — taglio
 * da 32 a 24 item, 6 per pilastro) e
 * docs/Ainima_00_Indice_Schema_Consolidato_v1.md (domande trappola — v.
 * CLAUDE.md). Non alterare i codici: il backend valida che tutti i 25
 * siano presenti (ITEM_CODES_EQ + 'T3' in schemas/psychometric.py).
 */

export interface EqItem {
  code: string;
  it: string;
  en: string;
}

export const EQ_ITEMS: EqItem[] = [
  // AUTOCONSAPEVOLEZZA
  { code: "AC1", it: "Quando sono di cattivo umore, di solito riesco a individuare cosa l'ha causato.", en: "When I'm in a bad mood, I can usually pinpoint what caused it." },
  { code: "AC2", it: "Spesso mi accorgo di essere arrabbiato/a solo quando qualcuno me lo fa notare.", en: "I often realize I'm angry only when someone points it out." },
  { code: "AC3", it: "Riesco a distinguere tra emozioni simili (es. delusione e rabbia) invece di etichettarle tutte come \"mi sento male\".", en: "I can tell similar emotions apart (e.g. disappointment and anger) instead of labeling them all as \"feeling bad\"." },
  { code: "AC4", it: "Le mie reazioni emotive a volte mi sorprendono, come se arrivassero dal nulla.", en: "My emotional reactions sometimes surprise me, as if they came out of nowhere." },
  { code: "AC5", it: "So riconoscere quando uno stato d'animo del passato influenza il mio modo di reagire oggi.", en: "I can recognize when a past mood affects how I react today." },
  { code: "AC6", it: "Dopo un momento di tensione, riesco a spiegarmi cosa mi ha davvero infastidito.", en: "After a tense moment, I can explain to myself what really bothered me." },
  // AUTOREGOLAZIONE
  { code: "AR1", it: "Quando sono molto arrabbiato/a, faccio fatica a controllare cosa dico.", en: "When I'm very angry, I struggle to control what I say." },
  { code: "AR2", it: "Riesco a prendermi una pausa prima di rispondere quando sono nervoso/a.", en: "I can take a pause before responding when I'm upset." },
  { code: "AR3", it: "Un piccolo imprevisto può bastare a mandarmi in crisi per il resto della giornata.", en: "A small mishap can be enough to throw off my whole day." },
  { code: "AR4", it: "Anche sotto stress, riesco solitamente a mantenere un tono di voce calmo.", en: "Even under stress, I can usually keep a calm tone of voice." },
  { code: "AR5", it: "So aspettare il momento giusto per affrontare una discussione importante, invece di reagire a caldo.", en: "I know how to wait for the right moment to address an important issue, instead of reacting in the heat of it." },
  { code: "AR6", it: "Riesco a calmarmi da solo/a dopo un episodio di forte tensione, senza bisogno che qualcun altro intervenga.", en: "I can calm myself down after a tense episode, without needing anyone else to step in." },
  // Domanda trappola (Ainima_00_Indice_Schema_Consolidato_v1.md) — indipendente
  // da qualunque pilastro, non entra nello scoring EQ. Posizionata al
  // confine tra Autoregolazione ed Empatia, a metà test.
  { code: "T3", it: "Domanda di controllo: seleziona 'Neutro / Dipende' per questa affermazione.", en: "Control question: select 'Neutral / Depends' for this statement." },
  // EMPATIA
  { code: "EM1", it: "Mi accorgo facilmente quando una persona vicina a me è a disagio, anche se non lo dice apertamente.", en: "I easily notice when someone close to me is uncomfortable, even if they don't say so openly." },
  { code: "EM2", it: "Quando qualcuno mi racconta un problema, il mio primo istinto è offrire una soluzione più che ascoltare come si sente.", en: "When someone tells me about a problem, my first instinct is to offer a solution rather than listen to how they feel." },
  { code: "EM3", it: "Prima di giudicare il comportamento di qualcuno, provo a immaginare cosa potrebbe aver vissuto.", en: "Before judging someone's behavior, I try to imagine what they might have been through." },
  { code: "EM4", it: "Fatico a capire perché le persone si arrabbiano per cose che a me sembrano poco importanti.", en: "I struggle to understand why people get upset over things that seem unimportant to me." },
  { code: "EM5", it: "Mi capita di modificare il mio comportamento dopo aver notato che ha ferito qualcuno, anche senza che me lo dicano.", en: "I sometimes change my behavior after noticing it hurt someone, even without being told." },
  { code: "EM6", it: "Riesco a percepire quando una persona dice \"va tutto bene\" ma in realtà non è così.", en: "I can sense when someone says \"everything's fine\" but it really isn't." },
  // RESPONSABILITÀ RELAZIONALE
  { code: "RE1", it: "Quando sbaglio, ammetto l'errore anche se è scomodo farlo.", en: "When I make a mistake, I admit it even when it's uncomfortable." },
  { code: "RE2", it: "Se una discussione va male, di solito penso che sia soprattutto colpa dell'altra persona.", en: "If an argument goes badly, I usually think it's mostly the other person's fault." },
  { code: "RE3", it: "Riesco a chiedere scusa senza aggiungere giustificazioni che scaricano la colpa sull'altro.", en: "I can apologize without adding justifications that shift the blame onto the other person." },
  { code: "RE4", it: "Preferisco lasciar perdere piuttosto che ammettere di aver sbagliato qualcosa.", en: "I prefer to let it go rather than admit I got something wrong." },
  { code: "RE5", it: "Dopo un conflitto, mi chiedo spesso cosa avrei potuto fare diversamente.", en: "After a conflict, I often ask myself what I could have done differently." },
  { code: "RE6", it: "Sono disposto/a a cambiare il mio comportamento se capisco che sta danneggiando una relazione.", en: "I'm willing to change my behavior if I realize it's harming a relationship." },
];
