"use client";

import { FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Alert, Badge, Button, Card, SelectField, TextField } from "@/components/ui";
import { preferencesApi, profileApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import type { StepProps } from "@/lib/wizard/types";

const GENERE_VALUES = ["Maschile", "Femminile", "Non binario", "Altro"] as const;
const ACCETTA_FIGLI_VALUES = ["Si", "No", "Indifferente"] as const;
const DESIDERA_FIGLI_VALUES = ["Si", "No", "Da valutare"] as const;
const CORPORATURA_VALUES = ["Snella", "Atletica", "Media", "Robusta", "Curvy"] as const;

function TriStateToggle({
  value,
  onChange,
  yesLabel,
  noLabel,
  noPreferenceLabel,
}: {
  value: boolean | null;
  onChange: (v: boolean | null) => void;
  yesLabel: string;
  noLabel: string;
  noPreferenceLabel: string;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button type="button" size="md" variant={value === null ? "primary" : "secondary"} onClick={() => onChange(null)}>
        {noPreferenceLabel}
      </Button>
      <Button type="button" size="md" variant={value === true ? "primary" : "secondary"} onClick={() => onChange(true)}>
        {yesLabel}
      </Button>
      <Button type="button" size="md" variant={value === false ? "primary" : "secondary"} onClick={() => onChange(false)}>
        {noLabel}
      </Button>
    </div>
  );
}

export function StepPreferences({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.preferences");
  const tCommon = useTranslations("common");
  const dealbreakerAction = useAsyncAction(preferencesApi.updateDealbreaker);
  const softAction = useAsyncAction(preferencesApi.updateSoft);
  const geoAction = useAsyncAction(profileApi.updateProfile);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!state.userId) return;

    const dealbreakerResult = await dealbreakerAction.run(state.userId, {
      pref_genere_cercato: state.pref_genere_cercato || null,
      pref_eta_min: Number(state.pref_eta_min),
      pref_eta_max: Number(state.pref_eta_max),
      pref_accetta_figli: state.pref_accetta_figli,
      pref_desidera_figli_futuri: state.pref_desidera_figli_futuri,
    });
    if (!dealbreakerResult) return;

    // importanza_vicinanza_geografica/lingue_parlate vivono in socio_profile,
    // non in dealbreaker_criteria — sostituiscono pref_distanza_max_km
    // (superato, v. CLAUDE.md), quindi passano dall'endpoint profilo.
    const geoResult = await geoAction.run(state.userId, {
      importanza_vicinanza_geografica: Number(state.importanza_vicinanza_geografica),
      lingue_parlate: state.lingue_parlate
        ? state.lingue_parlate.split(",").map((l) => l.trim()).filter(Boolean)
        : null,
    });
    if (!geoResult) return;

    const softResult = await softAction.run(state.userId, {
      pref_altezza_min: state.pref_altezza_min ? Number(state.pref_altezza_min) : null,
      pref_altezza_max: state.pref_altezza_max ? Number(state.pref_altezza_max) : null,
      pref_stato_civile_accettato: state.pref_stato_civile_accettato || null,
      pref_titolo_studio: state.pref_titolo_studio || null,
      pref_corporatura: state.pref_corporatura || null,
      pref_fumo: state.pref_fumo,
      pref_alcol: state.pref_alcol,
      pref_fede_religiosa: state.pref_fede_religiosa || null,
      pref_importanza_religione: state.pref_importanza_religione
        ? Number(state.pref_importanza_religione)
        : null,
    });
    if (softResult) onNext();
  }

  const loading = dealbreakerAction.loading || softAction.loading || geoAction.loading;
  const error = dealbreakerAction.error || softAction.error || geoAction.error;

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-8">
        <section className="flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <Badge tone="navy">{t("dealbreakerTitle")}</Badge>
          </div>
          <p className="text-xs text-slate">{t("dealbreakerSubtitle")}</p>

          <SelectField
            label={t("genereCercato")}
            value={state.pref_genere_cercato}
            onChange={(e) => update("pref_genere_cercato", e.target.value as StepProps["state"]["pref_genere_cercato"])}
          >
            <option value="">{tCommon("indifferent")}</option>
            {GENERE_VALUES.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </SelectField>

          <div className="grid grid-cols-2 gap-4">
            <TextField
              label={t("etaMin")}
              type="number"
              min={18}
              max={99}
              required
              value={state.pref_eta_min}
              onChange={(e) => update("pref_eta_min", e.target.value)}
            />
            <TextField
              label={t("etaMax")}
              type="number"
              min={18}
              max={99}
              required
              value={state.pref_eta_max}
              onChange={(e) => update("pref_eta_max", e.target.value)}
            />
          </div>

          <SelectField
            label={t("importanzaVicinanza")}
            value={state.importanza_vicinanza_geografica}
            onChange={(e) => update("importanza_vicinanza_geografica", e.target.value)}
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </SelectField>
          <p className="-mt-2 text-xs text-slate">{t("importanzaVicinanzaHint")}</p>

          <TextField
            label={t("lingueParlate")}
            placeholder={t("lingueParlatePlaceholder")}
            value={state.lingue_parlate}
            onChange={(e) => update("lingue_parlate", e.target.value)}
          />
          <p className="-mt-2 text-xs text-slate">{t("lingueParlateHint")}</p>

          <div>
            <span className="text-sm font-medium text-navy">{t("accettaFigli")}</span>
            <div className="mt-1.5 flex flex-wrap gap-2">
              {ACCETTA_FIGLI_VALUES.map((v) => (
                <Button
                  key={v}
                  type="button"
                  variant={state.pref_accetta_figli === v ? "primary" : "secondary"}
                  onClick={() => update("pref_accetta_figli", v)}
                >
                  {t(`accettaFigliOptions.${v}`)}
                </Button>
              ))}
            </div>
          </div>

          <div>
            <span className="text-sm font-medium text-navy">{t("desideraFigliFuturi")}</span>
            <div className="mt-1.5 flex flex-wrap gap-2">
              {DESIDERA_FIGLI_VALUES.map((v) => (
                <Button
                  key={v}
                  type="button"
                  variant={state.pref_desidera_figli_futuri === v ? "primary" : "secondary"}
                  onClick={() => update("pref_desidera_figli_futuri", v)}
                >
                  {t(`desideraFigliFuturiOptions.${v}`)}
                </Button>
              ))}
            </div>
          </div>
        </section>

        <section className="flex flex-col gap-4 border-t border-border pt-6">
          <Badge tone="gold">{t("softTitle")}</Badge>
          <p className="text-xs text-slate">{t("softSubtitle")}</p>

          <div className="grid grid-cols-2 gap-4">
            <TextField
              label={t("altezzaMin")}
              type="number"
              value={state.pref_altezza_min}
              onChange={(e) => update("pref_altezza_min", e.target.value)}
            />
            <TextField
              label={t("altezzaMax")}
              type="number"
              value={state.pref_altezza_max}
              onChange={(e) => update("pref_altezza_max", e.target.value)}
            />
          </div>

          <TextField
            label={t("statoCivileAccettato")}
            value={state.pref_stato_civile_accettato}
            onChange={(e) => update("pref_stato_civile_accettato", e.target.value)}
          />

          <TextField
            label={t("titoloStudio")}
            value={state.pref_titolo_studio}
            onChange={(e) => update("pref_titolo_studio", e.target.value)}
          />

          <SelectField
            label={t("corporatura")}
            value={state.pref_corporatura}
            onChange={(e) => update("pref_corporatura", e.target.value)}
          >
            <option value="">{t("noPreference")}</option>
            {CORPORATURA_VALUES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </SelectField>

          <div>
            <span className="text-sm font-medium text-navy">{t("fumo")}</span>
            <div className="mt-1.5">
              <TriStateToggle
                value={state.pref_fumo}
                onChange={(v) => update("pref_fumo", v)}
                yesLabel={tCommon("yes")}
                noLabel={tCommon("no")}
                noPreferenceLabel={t("noPreference")}
              />
            </div>
          </div>

          <div>
            <span className="text-sm font-medium text-navy">{t("alcol")}</span>
            <div className="mt-1.5">
              <TriStateToggle
                value={state.pref_alcol}
                onChange={(v) => update("pref_alcol", v)}
                yesLabel={tCommon("yes")}
                noLabel={tCommon("no")}
                noPreferenceLabel={t("noPreference")}
              />
            </div>
          </div>

          <TextField
            label={t("fedeReligiosa")}
            value={state.pref_fede_religiosa}
            onChange={(e) => update("pref_fede_religiosa", e.target.value)}
          />

          <SelectField
            label={t("importanzaReligione")}
            value={state.pref_importanza_religione}
            onChange={(e) => update("pref_importanza_religione", e.target.value)}
          >
            <option value="">{t("noPreference")}</option>
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
