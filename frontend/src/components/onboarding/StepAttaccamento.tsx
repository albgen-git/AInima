"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Alert, Button, Card } from "@/components/ui";
import { cn } from "@/lib/cn";
import { psychometricApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import { ATTACCAMENTO_ITEMS } from "@/lib/wizard/attaccamentoItems";
import type { StepProps } from "@/lib/wizard/types";

const SCALE = [1, 2, 3, 4, 5] as const;

/**
 * Ainima_Test_Attaccamento_v1.md — sostituisce l'inferenza LLM dalla
 * chat-intervista con un test scritto a scoring deterministico
 * (ansia_score/evitamento_score), v. CLAUDE.md 2026-08-19.
 */
export function StepAttaccamento({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.attaccamento");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [frameworkDismissed, setFrameworkDismissed] = useState(false);
  const { run, loading, error } = useAsyncAction(psychometricApi.submitAttaccamento);

  const item = ATTACCAMENTO_ITEMS[index];
  const isLast = index === ATTACCAMENTO_ITEMS.length - 1;
  const scaleLabels = [t("scale1"), t("scale2"), t("scale3"), t("scale4"), t("scale5")];

  async function selectAnswer(value: number) {
    if (selected !== null) return;
    setSelected(value);
    const next = { ...answers, [item.code]: value };
    setAnswers(next);

    // Piccola pausa per dare un feedback visivo della risposta selezionata
    // prima di avanzare — altrimenti il click sembra non avere alcun effetto.
    await new Promise((resolve) => setTimeout(resolve, 350));

    if (!isLast) {
      setSelected(null);
      setIndex((i) => i + 1);
      return;
    }
    if (!state.userId) {
      setSelected(null);
      return;
    }
    const result = await run(state.userId, { risposte: next });
    if (result) {
      update("attaccamentoCompletato", true);
      onNext();
    } else {
      setSelected(null);
    }
  }

  if (state.attaccamentoCompletato) {
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

  if (!frameworkDismissed) {
    return (
      <Card>
        <h1 className="font-display text-2xl text-navy">{t("frameworkTitle")}</h1>
        <p className="mt-4 text-sm text-slate">{t("frameworkBody")}</p>
        <div className="mt-6 flex gap-3">
          <Button variant="secondary" onClick={onBack}>
            {tCommon("back")}
          </Button>
          <Button onClick={() => setFrameworkDismissed(true)}>{t("frameworkCta")}</Button>
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
            style={{ width: `${(index / ATTACCAMENTO_ITEMS.length) * 100}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-slate">
          {t("progress", { current: index + 1, total: ATTACCAMENTO_ITEMS.length })}
        </p>

        <p className="mt-6 min-h-16 font-display text-xl text-navy">
          {locale === "it" ? item.it : item.en}
        </p>

        <div className="mt-6 flex flex-col gap-2">
          {SCALE.map((value, i) => (
            <button
              key={value}
              type="button"
              disabled={loading || selected !== null}
              onClick={() => selectAnswer(value)}
              className={cn(
                "rounded-xl border px-4 py-3 text-left text-sm transition-colors",
                selected === value
                  ? "border-navy bg-navy text-ivory"
                  : "border-border bg-ivory-light text-navy hover:border-navy hover:bg-border",
                selected !== null && selected !== value && "opacity-40"
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
            disabled={selected !== null}
            onClick={() => (index === 0 ? setFrameworkDismissed(false) : setIndex((i) => i - 1))}
          >
            {tCommon("back")}
          </Button>
        </div>
      </div>
    </Card>
  );
}
