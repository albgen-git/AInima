"use client";

import { FormEvent, useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, Badge, Button, Card, TextField } from "@/components/ui";
import { authApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import type { StepProps } from "@/lib/wizard/types";

export function StepPayment({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.payment");
  const tCommon = useTranslations("common");
  const [cardNumber, setCardNumber] = useState("");
  const { run, loading, error } = useAsyncAction(authApi.setPaymentMethod);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!state.userId) return;
    // Nessun gateway reale collegato (v. subtitle/disclaimer): il "token"
    // qui è solo un identificatore simulato lato client, non una vera
    // tokenizzazione — nessun dato di carta in chiaro viene comunque
    // salvato lato Ainima.
    const simulatedToken = `tok_sim_${cardNumber.replace(/\s/g, "").slice(-4)}`;
    const result = await run(state.userId, { metodo_pagamento_token: simulatedToken });
    if (result?.pre_autorizzato) {
      update("cartaRegistrata", true);
    }
  }

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      {state.cartaRegistrata ? (
        <div className="mt-6 flex flex-col gap-4">
          <Badge tone="sage">{t("success")}</Badge>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={onBack}>
              {tCommon("back")}
            </Button>
            <Button onClick={onNext}>{tCommon("continue")}</Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <Alert tone="info">{t("disclaimer")}</Alert>
          <TextField
            label={t("cardNumberLabel")}
            required
            placeholder={t("cardNumberPlaceholder")}
            value={cardNumber}
            onChange={(e) => setCardNumber(e.target.value)}
          />
          {error && <Alert tone="error">{error}</Alert>}
          <div className="flex gap-3">
            <Button variant="secondary" type="button" onClick={onBack}>
              {tCommon("back")}
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? tCommon("loading") : t("submit")}
            </Button>
          </div>
        </form>
      )}
    </Card>
  );
}
