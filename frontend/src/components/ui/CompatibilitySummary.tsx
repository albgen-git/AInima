import type { ProposalAnalysisOut } from "@/lib/api";

/**
 * Sintesi testuale di compatibilità caratteriale di coppia (RF-12 — v.
 * CLAUDE.md/Documento_Requisiti_v1.md, "Prompt 6") — MAI un numero, una
 * percentuale o un indicatore visivo che ne lasci intuire il valore
 * (v. CLAUDE.md: una barra proporzionale al punteggio, anche senza cifra
 * stampata, rivela comunque un parametro interno — rimossa il 2026-09-07
 * su richiesta esplicita, mai da reintrodurre in questa forma). Solo
 * testo generato. Condivisa tra la schermata Proposta e la Rubrica (un
 * match specifico, qualunque stato) — v. rispettivamente matchingApi.
 * getProposalAnalysis/getMatchAnalysis. La sintesi è generata una sola
 * volta per match e identica per entrambe le parti (mai due versioni
 * separate).
 */
export function CompatibilitySummary({
  analysis,
  loadingText,
  notReadyText,
  hintText,
}: {
  analysis: ProposalAnalysisOut | null;
  loadingText: string;
  notReadyText: string;
  hintText: string;
}) {
  if (!analysis) return <p className="text-sm text-slate">{loadingText}</p>;
  if (!analysis.pronta || !analysis.analisi) return <p className="text-sm text-slate">{notReadyText}</p>;

  return (
    <div>
      <p className="text-sm text-slate">{hintText}</p>
      {analysis.analisi.sintesi_caratteriale_coppia ? (
        <p className="mt-3 whitespace-pre-line text-sm text-navy">
          {analysis.analisi.sintesi_caratteriale_coppia}
        </p>
      ) : (
        // Fallback se la generazione non è (ancora) riuscita — non blocca
        // la UI, mostra solo lo spunto generico più leggero già esistente.
        analysis.analisi.spunto_di_attenzione && (
          <p className="mt-3 text-sm text-slate">{analysis.analisi.spunto_di_attenzione}</p>
        )
      )}
    </div>
  );
}
