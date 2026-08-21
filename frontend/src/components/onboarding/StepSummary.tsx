"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, Badge, Button, Card } from "@/components/ui";
import { authApi, type OnboardingStatus } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import { Link } from "@/i18n/navigation";
import type { StepProps } from "@/lib/wizard/types";

export function StepSummary({ state, onBack }: StepProps) {
  const t = useTranslations("onboarding.summary");
  const tCommon = useTranslations("common");
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const { run, loading, error } = useAsyncAction(authApi.getOnboardingStatus);

  useEffect(() => {
    if (!state.userId) return;
    run(state.userId).then((result) => {
      if (result) setStatus(result);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.userId]);

  const isActive = status?.stato_account === "Attivo";

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>

      {loading && !status && <p className="mt-4 text-sm text-slate">…</p>}
      {error && <Alert tone="error" className="mt-4">{error}</Alert>}

      {status && (
        <>
          <div className="mt-4 flex items-center gap-2">
            <Badge tone={isActive ? "sage" : "gold"}>
              {isActive ? t("statusActive") : t("statusPending")}
            </Badge>
          </div>
          <p className="mt-2 text-sm text-slate">
            {isActive ? t("subtitleActive") : t("subtitlePending")}
          </p>

          <div className="mt-6 flex flex-col gap-2">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-navy">
              {t("checklistTitle")}
            </h2>
            {Object.entries(status.checklist).map(([key, done]) => (
              <div key={key} className="flex items-center justify-between rounded-xl border border-border bg-ivory-light px-4 py-2.5">
                <span className="text-sm text-navy">{t(`checklist.${key}`)}</span>
                <Badge tone={done ? "sage" : "neutral"}>{done ? "✓" : "—"}</Badge>
              </div>
            ))}
          </div>

          <div className="mt-8 flex gap-3">
            <Button variant="secondary" onClick={onBack}>
              {tCommon("back")}
            </Button>
            <Link href="/dashboard">
              <Button>{t("goToDashboard")}</Button>
            </Link>
          </div>
        </>
      )}
    </Card>
  );
}
