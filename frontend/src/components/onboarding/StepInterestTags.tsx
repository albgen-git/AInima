"use client";

import { FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Alert, Button, Card, TextField } from "@/components/ui";
import { preferencesApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import type { StepProps } from "@/lib/wizard/types";

/**
 * RF-08c: liste "mi piace/non sopporto" e "partner vorrei/non vorrei" —
 * v. docs/Ainima_Liste_Piace_Detesta_v1.md. A differenza dei due campi
 * liberi narrativi (step precedente), queste liste ENTRANO davvero nel
 * calcolo del punteggio di compatibilità (Punteggio_Tag_Liste, STEP 4),
 * non solo nel report — v. CLAUDE.md.
 */
export function StepInterestTags({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.interestTags");
  const tCommon = useTranslations("common");
  const { run, loading, error } = useAsyncAction(preferencesApi.updateInterestTags);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!state.userId) return;
    const result = await run(state.userId, {
      mi_piace: state.mi_piace,
      non_sopporto: state.non_sopporto,
      partner_vorrei: state.partner_vorrei,
      partner_non_vorrei: state.partner_non_vorrei,
    });
    if (result) onNext();
  }

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-5">
        <TextField
          label={t("miPiace")}
          hint={t("miPiaceHint")}
          placeholder={t("placeholder")}
          value={state.mi_piace}
          onChange={(e) => update("mi_piace", e.target.value)}
        />
        <TextField
          label={t("nonSopporto")}
          hint={t("nonSopportoHint")}
          placeholder={t("placeholder")}
          value={state.non_sopporto}
          onChange={(e) => update("non_sopporto", e.target.value)}
        />
        <TextField
          label={t("partnerVorrei")}
          hint={t("partnerVorreiHint")}
          placeholder={t("placeholder")}
          value={state.partner_vorrei}
          onChange={(e) => update("partner_vorrei", e.target.value)}
        />
        <TextField
          label={t("partnerNonVorrei")}
          hint={t("partnerNonVorreiHint")}
          placeholder={t("placeholder")}
          value={state.partner_non_vorrei}
          onChange={(e) => update("partner_non_vorrei", e.target.value)}
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
