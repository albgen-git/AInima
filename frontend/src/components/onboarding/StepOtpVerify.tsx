"use client";

import { FormEvent, useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, Button, Card, TextField } from "@/components/ui";
import { authApi } from "@/lib/api";
import { setSessionToken, setUserId } from "@/lib/session";
import { useAsyncAction } from "@/lib/useAsyncAction";
import type { StepProps } from "@/lib/wizard/types";

export function StepOtpVerify({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.otpVerify");
  const tCommon = useTranslations("common");
  const [codice, setCodice] = useState("");
  const verifyAction = useAsyncAction(authApi.verifyOtp);
  const resendAction = useAsyncAction(authApi.requestOtp);

  async function handleVerify(e: FormEvent) {
    e.preventDefault();
    const result = await verifyAction.run({ email: state.email, codice });
    if (result) {
      setUserId(result.user_id);
      setSessionToken(result.token);
      update("userId", result.user_id);
      onNext();
    }
  }

  async function handleResend() {
    await resendAction.run({ email: state.email });
  }

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle", { email: state.email })}</p>

      <form onSubmit={handleVerify} className="mt-6 flex flex-col gap-4">
        <TextField
          label={t("codeLabel")}
          required
          inputMode="numeric"
          maxLength={6}
          value={codice}
          onChange={(e) => setCodice(e.target.value)}
        />

        {verifyAction.error && <Alert tone="error">{verifyAction.error}</Alert>}
        {resendAction.error && <Alert tone="error">{resendAction.error}</Alert>}

        <div className="flex flex-wrap gap-3">
          <Button variant="ghost" type="button" onClick={onBack}>
            {t("changeEmail")}
          </Button>
          <Button variant="secondary" type="button" onClick={handleResend} disabled={resendAction.loading}>
            {resendAction.loading ? tCommon("loading") : t("resend")}
          </Button>
          <Button type="submit" disabled={verifyAction.loading}>
            {verifyAction.loading ? tCommon("loading") : t("verify")}
          </Button>
        </div>
      </form>
    </Card>
  );
}
