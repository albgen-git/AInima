/**
 * 40 item del test Big Five (E1-E8, A1-A8, C1-C8, N1-N8, O1-O8) + 1 item
 * trappola condiviso ('T1', a metà test) = 41 elementi totali, fedeli a
 * docs/Ainima_Test_Psicometrico_BigFive_v1.md (v2 — taglio da 50 a 40 item,
 * 8 per dimensione, + riscrittura anti-duplicazione di Nevroticismo
 * integrale/7 item di Gradevolezza/1 item di Coscienziosità) e
 * docs/Ainima_00_Indice_Schema_Consolidato_v1.md (domande trappola —
 * v. CLAUDE.md). Non alterare i codici: il backend valida che tutti i 41
 * siano presenti (ITEM_CODES + 'T1' in schemas/psychometric.py).
 */

export interface BigFiveItem {
  code: string;
  it: string;
  en: string;
}

export const BIG_FIVE_ITEMS: BigFiveItem[] = [
  // ESTROVERSIONE
  { code: "E1", it: "Mi sento a mio agio quando sono circondato/a da molte persone che non conosco.", en: "I feel comfortable when surrounded by many people I don't know." },
  { code: "E2", it: "Preferisco trascorrere il tempo libero da solo/a piuttosto che in compagnia.", en: "I prefer spending free time alone rather than with others." },
  { code: "E3", it: "Nelle riunioni di famiglia o con gli amici, sono spesso io a tenere viva la conversazione.", en: "At family or friend gatherings, I'm often the one keeping the conversation going." },
  { code: "E4", it: "Se un gruppo deve prendere una decisione, tendo a proporre io la soluzione.", en: "When a group needs to make a decision, I tend to propose the solution myself." },
  { code: "E5", it: "Mi risulta naturale prendere l'iniziativa in una situazione nuova.", en: "Taking initiative in a new situation comes naturally to me." },
  { code: "E6", it: "Le giornate intense e piene di impegni mi caricano di energia, non mi stancano.", en: "Intense, busy days energize me rather than tire me out." },
  { code: "E7", it: "Alla fine di una settimana impegnativa, sento il bisogno di isolarmi completamente.", en: "At the end of a demanding week, I feel the need to completely isolate myself." },
  { code: "E8", it: "Rido e scherzo facilmente anche con persone che ho appena conosciuto.", en: "I laugh and joke easily even with people I've just met." },
  // GRADEVOLEZZA (A4-A8 riscritti — duplicavano EQ Empatia/Responsabilità, v. documento)
  { code: "A1", it: "Di norma parto dal presupposto che le persone abbiano buone intenzioni.", en: "I generally assume people have good intentions." },
  { code: "A2", it: "Sono diffidente finché qualcuno non mi dimostra di meritare la mia fiducia.", en: "I'm wary until someone proves they deserve my trust." },
  { code: "A3", it: "Preferisco trovare un compromesso piuttosto che imporre il mio punto di vista.", en: "I prefer finding a compromise rather than imposing my point of view." },
  { code: "A4", it: "Mi viene naturale offrire aiuto a chi mi sta intorno, anche senza che me lo chieda.", en: "Offering help to people around me comes naturally, even without being asked." },
  { code: "A5", it: "Trovo soddisfazione nel dedicare tempo ed energie al benessere altrui.", en: "I find satisfaction in devoting time and energy to others' wellbeing." },
  { code: "A6", it: "Non sento il bisogno di dimostrare di avere ragione più degli altri.", en: "I don't feel the need to prove I'm right more than others." },
  { code: "A7", it: "Mi piace essere riconosciuto/a come il/la migliore in ciò che faccio.", en: "I like being recognized as the best at what I do." },
  { code: "A8", it: "Sono a mio agio anche quando qualcun altro riceve più meriti di me per un lavoro di squadra.", en: "I'm comfortable even when someone else gets more credit than me for teamwork." },
  // COSCIENZIOSITÀ (C1 riscritto — duplicava il Test Profilo Relazionale)
  { code: "C1", it: "Tengo i miei spazi (casa, scrivania, oggetti personali) ordinati e ben organizzati.", en: "I keep my spaces (home, desk, personal belongings) tidy and well organized." },
  { code: "C2", it: "Il disordine intorno a me non mi crea alcun fastidio.", en: "Clutter around me doesn't bother me at all." },
  { code: "C3", it: "Porto a termine ciò che inizio, anche quando perde di interesse.", en: "I finish what I start, even when it stops being interesting." },
  { code: "C4", it: "Se prendo un impegno con qualcuno, lo rispetto anche a costo di un sacrificio personale.", en: "If I make a commitment to someone, I keep it even at personal cost." },
  // Domanda trappola (Ainima_00_Indice_Schema_Consolidato_v1.md) — indipendente
  // da qualunque dimensione, non entra nello scoring Big Five (v. TRAPPOLA_
  // RISPOSTA_ATTESA in backend/schemas/psychometric.py). Posizionata a metà test.
  { code: "T1", it: "Per mostrare che stai leggendo con attenzione, seleziona 'Poco d'accordo' per questa domanda.", en: "To show you're reading carefully, select 'Slightly disagree' for this question." },
  { code: "C5", it: "Le persone possono contare su di me per rispettare gli orari e le scadenze.", en: "People can count on me to respect schedules and deadlines." },
  { code: "C6", it: "Preferisco mettere da parte risorse per il futuro piuttosto che spenderle subito.", en: "I prefer setting resources aside for the future rather than spending them right away." },
  { code: "C7", it: "Tendo a fare acquisti d'impulso, senza troppa pianificazione.", en: "I tend to make impulse purchases, without much planning." },
  { code: "C8", it: "Prima di una decisione importante, valuto con attenzione le conseguenze a lungo termine.", en: "Before an important decision, I carefully weigh the long-term consequences." },
  // NEVROTICISMO (dimensione integralmente riscritta — duplicava Test Attaccamento/EQ Autoregolazione)
  { code: "N1", it: "Mi capita spesso di preoccuparmi anche per questioni di poco conto.", en: "I often worry even about minor issues." },
  { code: "N2", it: "Anche di fronte a situazioni incerte, tendo a restare tranquillo/a.", en: "Even when facing uncertain situations, I tend to stay calm." },
  { code: "N3", it: "Tendo a immaginare scenari negativi quando qualcosa non è ancora chiaro.", en: "I tend to imagine negative scenarios when something isn't clear yet." },
  { code: "N4", it: "Sotto pressione, avverto facilmente sintomi fisici come tensione o mal di testa.", en: "Under pressure, I easily notice physical symptoms like tension or headaches." },
  { code: "N5", it: "Le giornate con troppi imprevisti mi lasciano esausto/a più della media.", en: "Days with too many unexpected events leave me more exhausted than average." },
  { code: "N6", it: "Il mio umore può cambiare più volte nell'arco di una stessa giornata, senza una causa precisa.", en: "My mood can change several times within the same day, without a clear cause." },
  { code: "N7", it: "Il mio stato d'animo resta piuttosto costante, indipendentemente da piccoli eventi esterni.", en: "My mood stays fairly steady, regardless of small external events." },
  { code: "N8", it: "Ci sono giorni in cui mi sento giù senza un motivo preciso.", en: "There are days when I feel down for no clear reason." },
  // APERTURA
  { code: "O1", it: "Mi piace approfondire argomenti anche complessi o lontani dal mio ambito.", en: "I enjoy digging into topics even when complex or outside my field." },
  { code: "O2", it: "Preferisco restare su ciò che conosco già piuttosto che esplorare temi nuovi.", en: "I prefer sticking to what I already know rather than exploring new topics." },
  { code: "O3", it: "Le domande senza una risposta semplice mi incuriosiscono più di quelle facili.", en: "Questions without a simple answer intrigue me more than easy ones." },
  { code: "O4", it: "Sono disposto/a a cambiare un'abitudine consolidata se trovo un modo migliore di fare le cose.", en: "I'm willing to change a set habit if I find a better way of doing things." },
  { code: "O5", it: "Mi piace confrontarmi con punti di vista molto diversi dal mio.", en: "I enjoy engaging with viewpoints very different from my own." },
  { code: "O6", it: "Penso che ci sia un modo giusto di vivere e vari modi sbagliati.", en: "I think there's one right way to live and various wrong ones." },
  { code: "O7", it: "Il confronto con culture, abitudini o valori diversi dai miei mi arricchisce.", en: "Encountering cultures, habits, or values different from mine enriches me." },
  { code: "O8", it: "Preferisco stare con persone che vedono il mondo esattamente come me.", en: "I prefer being around people who see the world exactly as I do." },
];
