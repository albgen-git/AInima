"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, Badge, Button, Card, PageShell } from "@/components/ui";
import { AffinamentoCard } from "@/components/dashboard/AffinamentoCard";
import { PillolaCard } from "@/components/dashboard/PillolaCard";
import { PersonalReportCard } from "@/components/dashboard/PersonalReportCard";
import { PhotoSection } from "@/components/dashboard/PhotoSection";
import { authApi, personalReportApi, type DashboardOut, type PersonalReportOut } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import { getUserId } from "@/lib/session";
import { Link } from "@/i18n/navigation";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const [data, setData] = useState<DashboardOut | null>(null);
  const [report, setReport] = useState<PersonalReportOut | null>(null);
  const { run, loading, error } = useAsyncAction(authApi.getDashboard);
  const { run: runReport } = useAsyncAction(personalReportApi.getUltimoReport);
  const userId = getUserId();

  function ricarica() {
    if (!userId) return;
    run(userId).then((result) => {
      if (result) setData(result);
    });
    runReport(userId).then((result) => {
      if (result) setReport(result);
    });
  }

  useEffect(() => {
    ricarica();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isActive = data?.stato_account === "Attivo";
  const nDomandePendenti = data?.domande_affinamento_pendenti.length ?? 0;
  // Blocco E (Ainima_Dashboard_Trigger_Email_v1.md §1): la dashboard non
  // deve mai sembrare vuota — se nessuno dei 3 stati con priorità è
  // presente, un messaggio rassicurante prende il loro posto, mai un vuoto.
  const nienteDaMostrare =
    !!data && !data.ha_proposta_attiva && nDomandePendenti === 0 && !data.pillola_pendente;

  return (
    <PageShell>
      <h1 className="font-display text-3xl text-navy">{t("title")}</h1>

      {loading && !data && <p className="mt-4 text-sm text-slate">…</p>}
      {error && <Alert tone="error" className="mt-4">{error}</Alert>}

      {data && (
        <div className="mt-6 flex flex-col gap-6">
          <Card>
            <div className="flex items-center gap-2">
              <Badge tone={isActive ? "sage" : "gold"}>{data.stato_account}</Badge>
            </div>
            <p className="mt-2 text-sm text-slate">
              {isActive ? t("greetingActive") : t("greetingPending")}
            </p>

            <div className="mt-5 grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-slate">{t("subscriptionLabel")}</p>
                <p className="font-medium text-navy">{data.livello_abbonamento ?? "—"}</p>
              </div>
              {data.data_scadenza_abbonamento && (
                <div>
                  <p className="text-slate">{t("subscriptionExpiry")}</p>
                  <p className="font-medium text-navy">{data.data_scadenza_abbonamento}</p>
                </div>
              )}
              <div className="col-span-2">
                <p className="text-slate">{t("nextCycleLabel")}</p>
                <p className="font-medium text-navy">
                  {data.prossima_data_ciclo ?? t("nextCycleNone")}
                </p>
              </div>
            </div>
          </Card>

          {data.ha_proposta_attiva && (
            <Card className="border-navy/20 bg-border">
              <h2 className="font-display text-xl text-navy">{t("hasProposalTitle")}</h2>
              <p className="mt-1 text-sm text-slate">{t("hasProposalSubtitle")}</p>
              <Link href="/proposal">
                <Button className="mt-4">{t("viewProposal")}</Button>
              </Link>
            </Card>
          )}

          {userId && nDomandePendenti > 0 && (
            <AffinamentoCard userId={userId} count={nDomandePendenti} onCompleted={ricarica} />
          )}

          {userId && data.pillola_pendente && (
            <PillolaCard userId={userId} pillola={data.pillola_pendente} />
          )}

          {userId && report?.pronto && <PersonalReportCard userId={userId} report={report} />}

          {nienteDaMostrare && (
            <Card className="text-center">
              <p className="text-sm text-slate">{t("nothingPending")}</p>
            </Card>
          )}

          {userId && <PhotoSection userId={userId} />}

          <div className="grid grid-cols-2 gap-4">
            <Link href="/rubrica">
              <Card className="text-center hover:border-navy">
                <span className="text-sm font-medium text-navy">{t("goToRubrica")}</span>
              </Card>
            </Link>
            <Link href="/profile">
              <Card className="text-center hover:border-navy">
                <span className="text-sm font-medium text-navy">{t("goToProfile")}</span>
              </Card>
            </Link>
          </div>
        </div>
      )}
    </PageShell>
  );
}
