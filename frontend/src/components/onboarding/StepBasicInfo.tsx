"use client";

import { FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Alert, Button, Card, SelectField, TextField } from "@/components/ui";
import { profileApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import type { StepProps } from "@/lib/wizard/types";

const GENERE_VALUES = ["Maschile", "Femminile", "Non binario", "Altro"] as const;

/**
 * Info anagrafiche ordinarie, raccolte DOPO la verifica OTP — l'account
 * esiste già a questo punto (creato con la sola email in StepEmail), qui
 * si completa via PUT invece di crearlo (v. CLAUDE.md).
 */
export function StepBasicInfo({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.register");
  const tCommon = useTranslations("common");
  const { run, loading, error } = useAsyncAction(profileApi.updateProfile);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!state.userId) return;
    const result = await run(state.userId, {
      nome: state.nome,
      cognome: state.cognome,
      data_nascita: state.data_nascita,
      genere: state.genere || null,
      telefono: state.telefono || null,
    });
    if (result) onNext();
  }

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-4">
          <TextField
            label={t("nome")}
            required
            value={state.nome}
            onChange={(e) => update("nome", e.target.value)}
          />
          <TextField
            label={t("cognome")}
            required
            value={state.cognome}
            onChange={(e) => update("cognome", e.target.value)}
          />
        </div>

        <TextField
          label={t("dataNascita")}
          type="date"
          required
          value={state.data_nascita}
          onChange={(e) => update("data_nascita", e.target.value)}
        />

        <SelectField
          label={t("genere")}
          required
          value={state.genere}
          onChange={(e) => update("genere", e.target.value as WizardGenere)}
        >
          <option value="" disabled>
            {t("selectPlaceholder")}
          </option>
          {GENERE_VALUES.map((g) => (
            <option key={g} value={g}>
              {t(`genereOptions.${g}`)}
            </option>
          ))}
        </SelectField>

        <TextField
          label={t("telefono")}
          type="tel"
          hint={t("telefonoHint")}
          placeholder={t("telefonoPlaceholder")}
          value={state.telefono}
          onChange={(e) => update("telefono", e.target.value)}
        />

        {error && <Alert tone="error">{error}</Alert>}

        <div className="mt-2 flex gap-3">
          <Button variant="secondary" type="button" onClick={onBack}>
            {tCommon("back")}
          </Button>
          <Button type="submit" size="lg" disabled={loading}>
            {loading ? tCommon("loading") : t("continueButton")}
          </Button>
        </div>
      </form>
    </Card>
  );
}

type WizardGenere = StepProps["state"]["genere"];
