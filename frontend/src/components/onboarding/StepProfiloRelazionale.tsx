"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Alert, Button, Card } from "@/components/ui";
import { cn } from "@/lib/cn";
import { psychometricApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import { RELATIONAL_PROFILE_ITEMS } from "@/lib/wizard/relationalProfileItems";
import type { StepProps } from "@/lib/wizard/types";

const SCALE = [1, 2, 3, 4, 5] as const;

/**
 * Ainima_Test_Profilo_Relazionale_v1.md — sostituisce il confronto a
 * embedding tra i due campi liberi con un test scritto a scoring
 * deterministico (13 sotto-dimensioni, self + partner ideale), v.
 * CLAUDE.md, Blocco D.
 */
export function StepProfiloRelazionale({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.profiloRelazionale");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [index, setIndex] = useState(0);
  const { run, loading, error } = useAsyncAction(psychometricApi.submitProfiloRelazionale);

  const item = RELATIONAL_PROFILE_ITEMS[index];
  const isLast = index === RELATIONAL_PROFILE_ITEMS.length - 1;
  const scaleLabels = [t("scale1"), t("scale2"), t("scale3"), t("scale4"), t("scale5")];

  async function selectAnswer(value: number) {
    const next = { ...answers, [item.code]: value };
    setAnswers(next);

    if (!isLast) {
      setIndex((i) => i + 1);
      return;
    }
    if (!state.userId) return;
    const result = await run(state.userId, { risposte: next });
    if (result) {
      update("profiloRelazionaleCompletato", true);
      onNext();
    }
  }

  if (state.profiloRelazionaleCompletato) {
    return (
      <Card>
        <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
        <p className="mt-4 text-sm text-sage">{t("completed")}</p>
        <div className="mt-6 flex gap-3">
          <Button variant="secondary" onClick={onBack}>
            {tCommon("back")}
          </Button>
          <Button onClick={onNext}>{tCommon("continue")}</Button>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      <div className="mt-6">
        <div className="h-1.5 w-full rounded-full bg-border">
          <div
            className="h-1.5 rounded-full bg-navy transition-all"
            style={{ width: `${(index / RELATIONAL_PROFILE_ITEMS.length) * 100}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-slate">
          {t("progress", { current: index + 1, total: RELATIONAL_PROFILE_ITEMS.length })}
        </p>

        <p className="mt-6 min-h-16 font-display text-xl text-navy">
          {locale === "it" ? item.it : item.en}
        </p>

        <div className="mt-6 flex flex-col gap-2">
          {SCALE.map((value, i) => (
            <button
              key={value}
              type="button"
              disabled={loading}
              onClick={() => selectAnswer(value)}
              className={cn(
                "rounded-xl border border-border bg-ivory-light px-4 py-3 text-left text-sm text-navy transition-colors hover:border-navy hover:bg-border disabled:opacity-50"
              )}
            >
              {scaleLabels[i]}
            </button>
          ))}
        </div>

        {error && <Alert tone="error" className="mt-4">{error}</Alert>}

        <div className="mt-6 flex justify-between">
          <Button
            variant="secondary"
            type="button"
            onClick={() => (index === 0 ? onBack() : setIndex((i) => i - 1))}
          >
            {tCommon("back")}
          </Button>
        </div>
      </div>
    </Card>
  );
}
