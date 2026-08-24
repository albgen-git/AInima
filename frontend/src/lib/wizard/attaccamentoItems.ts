/**
 * 18 item del test Attaccamento (AN1-AN9, EV1-EV9) + 1 item trappola
 * condiviso ('T2', al confine tra le due dimensioni) = 19 elementi totali,
 * fedeli a docs/Ainima_Test_Attaccamento_v1.md (v2 — taglio da 24 a 18
 * item, 9 per dimensione) e docs/Ainima_00_Indice_Schema_Consolidato_v1.md
 * (domande trappola — v. CLAUDE.md). Non alterare i codici: il backend
 * valida che tutti i 19 siano presenti (ITEM_CODES_ATTACCAMENTO + 'T2' in
 * schemas/psychometric.py).
 */

export interface AttaccamentoItem {
  code: string;
  it: string;
  en: string;
}

export const ATTACCAMENTO_ITEMS: AttaccamentoItem[] = [
  // ANSIA DA ABBANDONO
  { code: "AN1", it: "Ho spesso paura che la persona che amo smetta di provare interesse per me.", en: "I often fear that the person I love will stop caring about me." },
  { code: "AN2", it: "Non mi preoccupo se il mio partner non mi contatta per un po'.", en: "I don't worry if my partner doesn't contact me for a while." },
  { code: "AN3", it: "Ho bisogno di frequenti rassicurazioni sul fatto di essere amato/a.", en: "I need frequent reassurance that I am loved." },
  { code: "AN4", it: "Temo che le persone a cui tengo possano allontanarsi da me senza preavviso.", en: "I fear that people I care about might drift away without warning." },
  { code: "AN5", it: "Anche nei momenti di silenzio prolungato da parte del partner, resto tranquillo/a.", en: "Even during long silences from my partner, I stay calm." },
  { code: "AN6", it: "Mi capita di controllare spesso se il partner mi ha risposto o mi sta pensando.", en: "I often find myself checking whether my partner has replied or is thinking of me." },
  { code: "AN7", it: "Temo che piccoli disaccordi possano mettere a rischio la relazione.", en: "I fear that small disagreements could put the relationship at risk." },
  { code: "AN8", it: "Riesco a stare bene anche quando la relazione attraversa un momento di distanza.", en: "I can stay fine even when the relationship goes through a distant phase." },
  { code: "AN9", it: "Mi capita di interpretare un tono neutro del partner come un segnale che qualcosa non va.", en: "I sometimes read a neutral tone from my partner as a sign something is wrong." },
  // Domanda trappola (Ainima_00_Indice_Schema_Consolidato_v1.md) — indipendente
  // da qualunque dimensione, non entra nello scoring di ansia/evitamento.
  // Posizionata al confine tra le due dimensioni, a metà test.
  { code: "T2", it: "Domanda di controllo: seleziona 'Abbastanza d'accordo' per continuare.", en: "Control question: select 'Slightly agree' to continue." },
  // EVITAMENTO DELL'INTIMITÀ
  { code: "EV1", it: "Preferisco non dipendere troppo dal mio partner per il mio benessere emotivo.", en: "I prefer not to depend too much on my partner for my emotional wellbeing." },
  { code: "EV2", it: "Mi viene naturale condividere pensieri e paure profonde con chi amo.", en: "It comes naturally to me to share deep thoughts and fears with the person I love." },
  { code: "EV3", it: "Mi sento a disagio quando qualcuno cerca troppa vicinanza emotiva con me.", en: "I feel uncomfortable when someone seeks too much emotional closeness with me." },
  { code: "EV4", it: "Preferisco gestire da solo/a i momenti difficili piuttosto che appoggiarmi al partner.", en: "I prefer to handle difficult moments on my own rather than lean on my partner." },
  { code: "EV5", it: "Mi piace condividere apertamente le mie vulnerabilità con chi amo.", en: "I enjoy openly sharing my vulnerabilities with the person I love." },
  { code: "EV6", it: "Mantenere una certa distanza mi fa sentire più sicuro/a in una relazione.", en: "Keeping a certain distance makes me feel more secure in a relationship." },
  { code: "EV7", it: "Tendo a minimizzare i problemi di coppia piuttosto che parlarne apertamente.", en: "I tend to downplay relationship problems rather than talk about them openly." },
  { code: "EV8", it: "Parlare apertamente dei miei sentimenti con il partner mi viene naturale.", en: "Talking openly about my feelings with my partner comes naturally to me." },
  { code: "EV9", it: "Mi infastidisce quando il partner cerca troppo contatto fisico o emotivo.", en: "It bothers me when my partner seeks too much physical or emotional contact." },
];
