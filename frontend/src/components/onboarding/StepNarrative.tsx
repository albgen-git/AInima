"use client";

import { FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Alert, Button, Card, TextareaField } from "@/components/ui";
import { psychometricApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import type { StepProps } from "@/lib/wizard/types";

/**
 * RF-07b: i due campi liberi che sostituiscono la chat-intervista.
 * Alimentano solo il layer generativo (Prompt 3a/3b + report finale),
 * mai direttamente lo score di compatibilità (RNF-11) — v. CLAUDE.md.
 */
export function StepNarrative({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.narrative");
  const tCommon = useTranslations("common");
  const { run, loading, error } = useAsyncAction(psychometricApi.updateNarrative);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!state.userId) return;
    const result = await run(state.userId, {
      descrizione_di_se: state.descrizione_di_se,
      descrizione_partner_ideale: state.descrizione_partner_ideale,
    });
    if (result) onNext();
  }

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-5">
        <TextareaField
          label={t("descrizioneDiSe")}
          hint={t("descrizioneDiSeHint")}
          required
          rows={5}
          value={state.descrizione_di_se}
          onChange={(e) => update("descrizione_di_se", e.target.value)}
        />
        <TextareaField
          label={t("descrizionePartnerIdeale")}
          hint={t("descrizionePartnerIdealeHint")}
          required
          rows={5}
          value={state.descrizione_partner_ideale}
          onChange={(e) => update("descrizione_partner_ideale", e.target.value)}
        />

        {error && <Alert tone="error">{error}</Alert>}

        <div className="mt-2 flex gap-3">
          <Button variant="secondary" type="button" onClick={onBack}>
            {tCommon("back")}
          </Button>
          <Button type="submit" size="lg" disabled={loading}>
            {loading ? tCommon("loading") : t("submit")}
          </Button>
        </div>
      </form>
    </Card>
  );
}
