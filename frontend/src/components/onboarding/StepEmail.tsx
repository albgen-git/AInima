"use client";

import { FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Alert, Button, Card, TextField } from "@/components/ui";
import { authApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import type { StepProps } from "@/lib/wizard/types";

/**
 * Unico punto d'ingresso, sia per chi si iscrive per la prima volta sia
 * per chi torna — stessa richiesta per entrambi i casi (RF-02, l'account
 * viene creato qui se non esiste ancora, con la sola email). Nessuna
 * password: l'accesso prosegue con un codice OTP inviato via email.
 */
export function StepEmail({ state, update, onNext }: StepProps) {
  const t = useTranslations("onboarding.email");
  const tCommon = useTranslations("common");
  const { run, loading, error } = useAsyncAction(authApi.requestOtp);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const result = await run({ email: state.email });
    if (result) {
      update("otpInviato", true);
      onNext();
    }
  }

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <TextField
          label={t("emailLabel")}
          type="email"
          required
          value={state.email}
          onChange={(e) => update("email", e.target.value)}
        />

        {error && <Alert tone="error">{error}</Alert>}

        <Button type="submit" size="lg" disabled={loading} className="mt-2">
          {loading ? tCommon("loading") : t("submit")}
        </Button>
      </form>
    </Card>
  );
}
