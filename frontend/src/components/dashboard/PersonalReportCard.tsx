"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button, Card } from "@/components/ui";
import type { PersonalReportOut } from "@/lib/api";
import { ReportFeedback } from "./ReportFeedback";

/**
 * RF-28..RF-30b: mostra l'ultima versione del report di analisi personale
 * ("La tua Prontezza Relazionale") una volta pronta — collassato di
 * default (il testo è lungo, ~200-350 parole), espande su richiesta. Il
 * feedback a stelle (RF-30) compare solo da espanso, sotto il testo.
 */
export function PersonalReportCard({
  userId,
  report,
}: {
  userId: string;
  report: Extract<PersonalReportOut, { pronto: true }>;
}) {
  const t = useTranslations("dashboard.personalReport");
  const [espanso, setEspanso] = useState(false);

  return (
    <Card className="border-navy/15 bg-white">
      <h2 className="font-display text-xl text-navy">{t("title")}</h2>
      <p className="mt-1 text-sm text-slate">{t("subtitle")}</p>
      {espanso ? (
        <>
          <p className="mt-3 whitespace-pre-line text-sm text-navy">{report.contenuto_report}</p>
          <ReportFeedback userId={userId} reportId={report.report_id} />
          <Button className="mt-4" variant="secondary" onClick={() => setEspanso(false)}>
            {t("collapse")}
          </Button>
        </>
      ) : (
        <Button className="mt-4" variant="secondary" onClick={() => setEspanso(true)}>
          {t("expand")}
        </Button>
      )}
    </Card>
  );
}
