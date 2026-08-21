"use client";

import { useTranslations } from "next-intl";
import { Alert, Button, Card } from "@/components/ui";
import { profileApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import type { StepProps } from "@/lib/wizard/types";

/**
 * Consenso esplicito art. 9 GDPR prima di raccogliere qualunque dato
 * particolare (orientamento sessuale nello step successivo, fede religiosa
 * più avanti nel profilo — entrambe le categorie coperte da questo unico
 * consenso, mostrato nel punto in cui la prima di queste viene richiesta).
 */
export function StepSensitiveConsent({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.sensitiveConsent");
  const tCommon = useTranslations("common");
  const { run, loading, error } = useAsyncAction(profileApi.updateProfile);

  async function handleAccept() {
    if (!state.userId) return;
    const result = await run(state.userId, { consenso_dati_sensibili: true });
    if (result) {
      update("consensoDatiSensibili", true);
      onNext();
    }
  }

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("intro")}</p>

      <div className="mt-5 flex flex-col gap-3 text-sm text-navy">
        <p>{t("whatWeAsk")}</p>
        <ul className="list-disc pl-5 text-slate">
          <li>{t("categoryOrientation")}</li>
          <li>{t("categoryReligion")}</li>
        </ul>
        <p className="text-slate">{t("why")}</p>
        <p className="text-slate">{t("rights")}</p>
      </div>

      <label className="mt-6 flex items-start gap-3 rounded-sm border border-border bg-ivory p-4 text-sm text-navy">
        <input
          type="checkbox"
          className="mt-0.5 h-4 w-4 accent-navy"
          checked={state.consensoDatiSensibili}
          onChange={(e) => update("consensoDatiSensibili", e.target.checked)}
        />
        {t("consentCheckbox")}
      </label>

      {error && <Alert tone="error" className="mt-4">{error}</Alert>}

      <div className="mt-6 flex gap-3">
        <Button variant="secondary" type="button" onClick={onBack}>
          {tCommon("back")}
        </Button>
        <Button type="button" onClick={handleAccept} disabled={!state.consensoDatiSensibili || loading}>
          {loading ? tCommon("loading") : t("accept")}
        </Button>
      </div>
    </Card>
  );
}
