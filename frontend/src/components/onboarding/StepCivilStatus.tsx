"use client";

import { FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Alert, Button, Card, SelectField } from "@/components/ui";
import { profileApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import type { StepProps } from "@/lib/wizard/types";

const STATO_CIVILE_VALUES = ["Celibe/Nubile", "Divorziato/a", "Vedovo/a", "Separato/a"] as const;

export function StepCivilStatus({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.civilStatus");
  const tCommon = useTranslations("common");
  const { run, loading, error } = useAsyncAction(profileApi.updateProfile);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!state.userId) return;
    const result = await run(state.userId, {
      stato_civile: state.stato_civile,
      ha_figli: state.ha_figli,
    });
    if (result) onNext();
  }

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <SelectField
          label={t("statoCivileLabel")}
          required
          value={state.stato_civile}
          onChange={(e) => update("stato_civile", e.target.value)}
        >
          <option value="" disabled>
            —
          </option>
          {STATO_CIVILE_VALUES.map((s) => (
            <option key={s} value={s}>
              {t(`statoCivileOptions.${s}`)}
            </option>
          ))}
        </SelectField>

        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-navy">{t("haFigliLabel")}</span>
          <div className="flex gap-3">
            <Button
              type="button"
              variant={state.ha_figli === true ? "primary" : "secondary"}
              onClick={() => update("ha_figli", true)}
            >
              {tCommon("yes")}
            </Button>
            <Button
              type="button"
              variant={state.ha_figli === false ? "primary" : "secondary"}
              onClick={() => update("ha_figli", false)}
            >
              {tCommon("no")}
            </Button>
          </div>
        </div>

        {error && <Alert tone="error">{error}</Alert>}

        <div className="mt-2 flex gap-3">
          <Button variant="secondary" type="button" onClick={onBack}>
            {tCommon("back")}
          </Button>
          <Button type="submit" disabled={loading || !state.stato_civile || state.ha_figli === null}>
            {loading ? tCommon("loading") : tCommon("continue")}
          </Button>
        </div>
      </form>
    </Card>
  );
}
