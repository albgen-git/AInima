import type { ProposalAnalysisOut } from "@/lib/api";

/**
 * Barra di compatibilità caratteriale (RF-12: "sintesi dell'analisi
 * caratteriale" della coppia) — MAI un numero stampato (v. CLAUDE.md:
 * "all'utente non va mai mostrato un numero, una percentuale o
 * un'etichetta clinica"), solo una barra visiva + un eventuale spunto
 * costruttivo generico. Condivisa tra la schermata Proposta e la Rubrica
 * (un match specifico, qualunque stato) — v. rispettivamente
 * matchingApi.getProposalAnalysis/getMatchAnalysis.
 */
export function CompatibilityBar({
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
      <div className="h-2 w-full rounded-full bg-border">
        <div
          className="h-2 rounded-full bg-gold transition-all"
          style={{ width: `${Math.round(analysis.analisi.punteggio_narrativo_strutturato * 100)}%` }}
        />
      </div>
      <p className="mt-2 text-sm text-slate">{hintText}</p>
      {analysis.analisi.spunto_di_attenzione && (
        <p className="mt-3 text-sm text-slate">{analysis.analisi.spunto_di_attenzione}</p>
      )}
    </div>
  );
}
