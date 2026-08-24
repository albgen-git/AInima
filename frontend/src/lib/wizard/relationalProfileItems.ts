/**
 * 26 item del Test Profilo Relazionale (13 sotto-dimensioni in 4 categorie
 * — Valori/Stile di Vita/Dinamica Relazionale/Aspirazioni — ciascuna con 2
 * item: Sé + Partner ideale), fedeli a
 * docs/Ainima_Test_Profilo_Relazionale_v1.md. Nessun item invertito,
 * nessuna domanda trappola per questo test (confermato in
 * docs/Ainima_00_Indice_Schema_Consolidato_v1.md — "non toccato").
 * Sostituisce il confronto a embedding nel calcolo di matching (Blocco D —
 * v. CLAUDE.md). Non alterare i codici: il backend valida che tutti i 26
 * siano presenti (ITEM_CODES_PROFILO_RELAZIONALE in schemas/psychometric.py).
 */

export interface RelationalProfileItem {
  code: string;
  it: string;
  en: string;
}

export const RELATIONAL_PROFILE_ITEMS: RelationalProfileItem[] = [
  // CATEGORIA 1 — VALORI E PRIORITÀ DI VITA
  { code: "V1S", it: "La famiglia (attuale o futura) è una delle massime priorità della mia vita.", en: "Family (current or future) is one of the highest priorities in my life." },
  { code: "V1I", it: "Cerco un partner per cui la famiglia sia una priorità centrale.", en: "I'm looking for a partner for whom family is a central priority." },
  { code: "V2S", it: "Investo molte energie nella mia carriera e nei miei obiettivi professionali.", en: "I invest a lot of energy in my career and professional goals." },
  { code: "V2I", it: "Mi piacerebbe un partner ambizioso, orientato alla crescita professionale.", en: "I'd like a partner who is ambitious and focused on professional growth." },
  { code: "V3S", it: "La stabilità (economica, abitativa, di routine) è per me un valore fondamentale.", en: "Stability (financial, housing, routine) is a fundamental value for me." },
  { code: "V3I", it: "Cerco un partner che dia valore alla stabilità e alla sicurezza quanto me.", en: "I'm looking for a partner who values stability and security as much as I do." },
  { code: "V4S", it: "Dedico tempo ed energie alla mia crescita personale (introspezione, spiritualità, sviluppo di sé).", en: "I dedicate time and energy to my personal growth (introspection, spirituality, self-development)." },
  { code: "V4I", it: "Vorrei un partner interessato al proprio percorso di crescita personale.", en: "I'd like a partner interested in their own personal growth journey." },

  // CATEGORIA 2 — STILE DI VITA QUOTIDIANO
  { code: "S1S", it: "Nella vita di tutti i giorni, cerco spesso occasioni di socialità e stare con altre persone.", en: "In everyday life, I often seek out social occasions and time with other people." },
  { code: "S1I", it: "Mi piacerebbe un partner con un forte bisogno di socialità e vita di gruppo.", en: "I'd like a partner with a strong need for socializing and group activities." },
  { code: "S2S", it: "Organizzo le mie giornate con largo anticipo, seguendo una routine strutturata.", en: "I organize my days well in advance, following a structured routine." },
  { code: "S2I", it: "Cerco un partner organizzato/a, che pianifica piuttosto che improvvisare.", en: "I'm looking for an organized partner who plans rather than improvises." },
  { code: "S3S", it: "Preferisco un ritmo di vita dinamico e pieno di impegni piuttosto che tranquillo.", en: "I prefer a dynamic, busy pace of life rather than a calm one." },
  { code: "S3I", it: "Mi piacerebbe condividere la vita con un partner dal ritmo dinamico e attivo.", en: "I'd like to share life with a partner who has a dynamic, active pace." },

  // CATEGORIA 3 — DINAMICA RELAZIONALE
  { code: "D1S", it: "Nella coppia, ho bisogno di mantenere spazi e tempi indipendenti dal partner.", en: "In a couple, I need to maintain spaces and time independent from my partner." },
  { code: "D1I", it: "Cerco un partner che rispetti e condivida il mio bisogno di autonomia personale.", en: "I'm looking for a partner who respects and shares my need for personal autonomy." },
  { code: "D2S", it: "Nella coppia preferisco decisioni condivise piuttosto che ruoli fissi e definiti.", en: "In a couple, I prefer shared decisions rather than fixed, defined roles." },
  { code: "D2I", it: "Cerco un partner con cui costruire una dinamica paritetica nelle decisioni di coppia.", en: "I'm looking for a partner to build an equal partnership with in couple decisions." },
  { code: "D3S", it: "Nei momenti di tensione o vicinanza, esprimo apertamente ciò che provo al partner.", en: "In moments of tension or closeness, I openly express what I feel to my partner." },
  { code: "D3I", it: "Cerco un partner che sappia esprimere apertamente le proprie emozioni nella coppia.", en: "I'm looking for a partner who can openly express their emotions in the relationship." },

  // CATEGORIA 4 — ASPIRAZIONI E PROGETTUALITÀ
  { code: "A1S", it: "Il matrimonio o un impegno formale a lungo termine è un obiettivo chiaro per me.", en: "Marriage or a long-term formal commitment is a clear goal for me." },
  { code: "A1I", it: "Cerco un partner orientato a un impegno serio e a lungo termine.", en: "I'm looking for a partner oriented toward a serious, long-term commitment." },
  { code: "A2S", it: "Sono aperto/a a trasferirmi o cambiare vita in modo significativo per una relazione importante.", en: "I'm open to relocating or making a significant life change for an important relationship." },
  { code: "A2I", it: "Mi piacerebbe un partner disposto a considerare un trasferimento o un grande cambiamento per la coppia.", en: "I'd like a partner willing to consider relocating or making a big change for the relationship." },
  { code: "A3S", it: "Pianifico attivamente il mio futuro a lungo termine (5-10 anni), non solo il presente.", en: "I actively plan my long-term future (5-10 years), not just the present." },
  { code: "A3I", it: "Cerco un partner che condivida una visione di lungo termine per la vita insieme.", en: "I'm looking for a partner who shares a long-term vision for life together." },
];
