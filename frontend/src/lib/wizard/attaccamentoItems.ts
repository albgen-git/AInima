/**
 * 24 item del test Attaccamento, fedeli a docs/Ainima_Test_Attaccamento_v1.md
 * — stessi codici (AN1-AN12, EV1-EV12) attesi da
 * backend/schemas/psychometric.py (ITEM_CODES_ATTACCAMENTO/REVERSE_ITEMS_ATTACCAMENTO).
 * Non alterare i codici: il backend valida che tutti e 24 siano presenti.
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
  { code: "AN4", it: "Mi sento sicuro/a del legame anche senza continue conferme.", en: "I feel secure in the bond even without constant confirmation." },
  { code: "AN5", it: "Temo che le persone a cui tengo possano allontanarsi da me senza preavviso.", en: "I fear that people I care about might drift away without warning." },
  { code: "AN6", it: "Anche nei momenti di silenzio prolungato da parte del partner, resto tranquillo/a.", en: "Even during long silences from my partner, I stay calm." },
  { code: "AN7", it: "Mi capita di controllare spesso se il partner mi ha risposto o mi sta pensando.", en: "I often find myself checking whether my partner has replied or is thinking of me." },
  { code: "AN8", it: "Non mi sento in ansia quando il partner trascorre del tempo lontano da me.", en: "I don't feel anxious when my partner spends time away from me." },
  { code: "AN9", it: "Temo che piccoli disaccordi possano mettere a rischio la relazione.", en: "I fear that small disagreements could put the relationship at risk." },
  { code: "AN10", it: "Riesco a stare bene anche quando la relazione attraversa un momento di distanza.", en: "I can stay fine even when the relationship goes through a distant phase." },
  { code: "AN11", it: "Mi capita di interpretare un tono neutro del partner come un segnale che qualcosa non va.", en: "I sometimes read a neutral tone from my partner as a sign something is wrong." },
  { code: "AN12", it: "Non ho bisogno di sapere costantemente cosa pensa di me il mio partner.", en: "I don't need to constantly know what my partner thinks of me." },
  // EVITAMENTO DELL'INTIMITÀ
  { code: "EV1", it: "Preferisco non dipendere troppo dal mio partner per il mio benessere emotivo.", en: "I prefer not to depend too much on my partner for my emotional wellbeing." },
  { code: "EV2", it: "Mi viene naturale condividere pensieri e paure profonde con chi amo.", en: "It comes naturally to me to share deep thoughts and fears with the person I love." },
  { code: "EV3", it: "Mi sento a disagio quando qualcuno cerca troppa vicinanza emotiva con me.", en: "I feel uncomfortable when someone seeks too much emotional closeness with me." },
  { code: "EV4", it: "Cerco attivamente intimità e vicinanza con il partner.", en: "I actively seek intimacy and closeness with my partner." },
  { code: "EV5", it: "Preferisco gestire da solo/a i momenti difficili piuttosto che appoggiarmi al partner.", en: "I prefer to handle difficult moments on my own rather than lean on my partner." },
  { code: "EV6", it: "Mi piace condividere apertamente le mie vulnerabilità con chi amo.", en: "I enjoy openly sharing my vulnerabilities with the person I love." },
  { code: "EV7", it: "Mantenere una certa distanza mi fa sentire più sicuro/a in una relazione.", en: "Keeping a certain distance makes me feel more secure in a relationship." },
  { code: "EV8", it: "Provo piacere nel sentirmi vicino/a emotivamente al partner.", en: "I enjoy feeling emotionally close to my partner." },
  { code: "EV9", it: "Tendo a minimizzare i problemi di coppia piuttosto che parlarne apertamente.", en: "I tend to downplay relationship problems rather than talk about them openly." },
  { code: "EV10", it: "Parlare apertamente dei miei sentimenti con il partner mi viene naturale.", en: "Talking openly about my feelings with my partner comes naturally to me." },
  { code: "EV11", it: "Mi infastidisce quando il partner cerca troppo contatto fisico o emotivo.", en: "It bothers me when my partner seeks too much physical or emotional contact." },
  { code: "EV12", it: "Mi sento a mio agio nel chiedere supporto al mio partner quando ne ho bisogno.", en: "I feel comfortable asking my partner for support when I need it." },
];
