"use client";

import { FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Alert, Button, Card, SelectField, TextField } from "@/components/ui";
import { profileApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import type { StepProps } from "@/lib/wizard/types";

const CORPORATURA_VALUES = ["Snella", "Atletica", "Media", "Robusta", "Curvy"] as const;
const TITOLO_STUDIO_VALUES = [
  "Diploma",
  "Laurea triennale",
  "Laurea magistrale",
  "Dottorato",
  "Altro",
] as const;
// Le chiavi di traduzione non possono contenere "." (separatore di
// namespace in next-intl) — i valori reali (con "." come separatore delle
// migliaia) sono quelli salvati sul backend, mappati qui a chiavi sicure.
const FASCIA_REDDITO_OPTIONS = [
  { value: "Preferisco non specificare", key: "nonSpecificato" },
  { value: "Fino a 25.000€", key: "fino25k" },
  { value: "25.000€ - 45.000€", key: "tra25e45k" },
  { value: "45.000€ - 70.000€", key: "tra45e70k" },
  { value: "Oltre 70.000€", key: "oltre70k" },
] as const;

function YesNoToggle({
  value,
  onChange,
  yesLabel,
  noLabel,
}: {
  value: boolean | null;
  onChange: (v: boolean) => void;
  yesLabel: string;
  noLabel: string;
}) {
  return (
    <div className="flex gap-3">
      <Button type="button" variant={value === true ? "primary" : "secondary"} onClick={() => onChange(true)}>
        {yesLabel}
      </Button>
      <Button type="button" variant={value === false ? "primary" : "secondary"} onClick={() => onChange(false)}>
        {noLabel}
      </Button>
    </div>
  );
}

export function StepProfile({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.profile");
  const tCommon = useTranslations("common");
  const { run, loading, error } = useAsyncAction(profileApi.updateProfile);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!state.userId) return;
    const result = await run(state.userId, {
      altezza_cm: state.altezza_cm ? Number(state.altezza_cm) : null,
      peso_kg: state.peso_kg ? Number(state.peso_kg) : null,
      corporatura: state.corporatura || null,
      colore_capelli: state.colore_capelli || null,
      colore_occhi: state.colore_occhi || null,
      fumo: state.fumo,
      alcol: state.alcol,
      stile_vita_sport: state.stile_vita_sport || null,
      comune_residenza: state.comune_residenza || null,
      titolo_studio: state.titolo_studio || null,
      settore_occupazionale: state.settore_occupazionale || null,
      fascia_reddito: state.fascia_reddito || null,
      fede_religiosa: state.fede_religiosa || null,
      importanza_religione: state.importanza_religione ? Number(state.importanza_religione) : null,
    });
    if (result) onNext();
  }

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-6">
        <section className="flex flex-col gap-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-navy">
            {t("physicalSection")}
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <TextField
              label={t("altezza")}
              type="number"
              min={100}
              max={250}
              required
              value={state.altezza_cm}
              onChange={(e) => update("altezza_cm", e.target.value)}
            />
            <TextField
              label={t("peso")}
              type="number"
              min={30}
              max={250}
              value={state.peso_kg}
              onChange={(e) => update("peso_kg", e.target.value)}
            />
          </div>

          <SelectField
            label={t("corporatura")}
            value={state.corporatura}
            onChange={(e) => update("corporatura", e.target.value)}
          >
            <option value="">—</option>
            {CORPORATURA_VALUES.map((c) => (
              <option key={c} value={c}>
                {t(`corporaturaOptions.${c}`)}
              </option>
            ))}
          </SelectField>

          <div className="grid grid-cols-2 gap-4">
            <TextField
              label={t("coloreCapelli")}
              value={state.colore_capelli}
              onChange={(e) => update("colore_capelli", e.target.value)}
            />
            <TextField
              label={t("coloreOcchi")}
              value={state.colore_occhi}
              onChange={(e) => update("colore_occhi", e.target.value)}
            />
          </div>

          <div>
            <span className="text-sm font-medium text-navy">{t("fumo")}</span>
            <div className="mt-1.5">
              <YesNoToggle
                value={state.fumo}
                onChange={(v) => update("fumo", v)}
                yesLabel={tCommon("yes")}
                noLabel={tCommon("no")}
              />
            </div>
          </div>

          <div>
            <span className="text-sm font-medium text-navy">{t("alcol")}</span>
            <div className="mt-1.5">
              <YesNoToggle
                value={state.alcol}
                onChange={(v) => update("alcol", v)}
                yesLabel={tCommon("yes")}
                noLabel={tCommon("no")}
              />
            </div>
          </div>

          <TextField
            label={t("stileVitaSport")}
            placeholder={t("stileVitaSportPlaceholder")}
            value={state.stile_vita_sport}
            onChange={(e) => update("stile_vita_sport", e.target.value)}
          />
        </section>

        <section className="flex flex-col gap-4 border-t border-border pt-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-navy">
            {t("socioSection")}
          </h2>

          <TextField
            label={t("comuneResidenza")}
            required
            value={state.comune_residenza}
            onChange={(e) => update("comune_residenza", e.target.value)}
          />

          <SelectField
            label={t("titoloStudio")}
            value={state.titolo_studio}
            onChange={(e) => update("titolo_studio", e.target.value)}
          >
            <option value="">—</option>
            {TITOLO_STUDIO_VALUES.map((v) => (
              <option key={v} value={v}>
                {t(`titoloStudioOptions.${v}`)}
              </option>
            ))}
          </SelectField>

          <TextField
            label={t("settoreOccupazionale")}
            value={state.settore_occupazionale}
            onChange={(e) => update("settore_occupazionale", e.target.value)}
          />

          <SelectField
            label={t("fasciaReddito")}
            value={state.fascia_reddito}
            onChange={(e) => update("fascia_reddito", e.target.value)}
          >
            <option value="">—</option>
            {FASCIA_REDDITO_OPTIONS.map(({ value, key }) => (
              <option key={value} value={value}>
                {t(`fasciaRedditoOptions.${key}`)}
              </option>
            ))}
          </SelectField>

          <TextField
            label={t("fedeReligiosa")}
            value={state.fede_religiosa}
            onChange={(e) => update("fede_religiosa", e.target.value)}
          />

          <SelectField
            label={t("importanzaReligione")}
            value={state.importanza_religione}
            onChange={(e) => update("importanza_religione", e.target.value)}
          >
            <option value="">—</option>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </SelectField>
        </section>

        {error && <Alert tone="error">{error}</Alert>}

        <div className="flex gap-3">
          <Button variant="secondary" type="button" onClick={onBack}>
            {tCommon("back")}
          </Button>
          <Button type="submit" disabled={loading}>
            {loading ? tCommon("loading") : tCommon("continue")}
          </Button>
        </div>
      </form>
    </Card>
  );
}
