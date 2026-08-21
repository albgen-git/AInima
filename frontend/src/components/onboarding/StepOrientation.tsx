"use client";

import { FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Alert, Button, Card, SelectField } from "@/components/ui";
import { profileApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import type { StepProps } from "@/lib/wizard/types";

const ORIENTAMENTO_VALUES = [
  "Eterosessuale",
  "Omosessuale",
  "Bisessuale",
  "Pansessuale",
  "Asessuale",
  "Altro",
] as const;

/**
 * Ultimo step dei dati particolari: raccoglie l'orientamento sessuale
 * (art. 9 GDPR, richiesto solo dopo il consenso esplicito del passo
 * precedente) e lo salva sull'account già esistente via PUT — con
 * l'autenticazione via email OTP l'account non nasce più qui, nasce alla
 * primissima richiesta OTP (v. CLAUDE.md).
 */
export function StepOrientation({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.orientation");
  const tCommon = useTranslations("common");
  const { run, loading, error } = useAsyncAction(profileApi.updateProfile);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!state.userId) return;
    const result = await run(state.userId, {
      orientamento_sessuale: state.orientamento_sessuale as (typeof ORIENTAMENTO_VALUES)[number],
    });
    if (result) onNext();
  }

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <SelectField
          label={t("orientamento")}
          required
          value={state.orientamento_sessuale}
          onChange={(e) =>
            update("orientamento_sessuale", e.target.value as StepProps["state"]["orientamento_sessuale"])
          }
        >
          <option value="" disabled>
            {t("selectPlaceholder")}
          </option>
          {ORIENTAMENTO_VALUES.map((o) => (
            <option key={o} value={o}>
              {t(`orientamentoOptions.${o}`)}
            </option>
          ))}
        </SelectField>

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
