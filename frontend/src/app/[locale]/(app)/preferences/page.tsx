"use client";

import { FormEvent, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, Badge, Button, Card, PageShell, SelectField, TextField } from "@/components/ui";
import {
  preferencesApi,
  profileApi,
  type DealbreakerCriteriaIn,
  type Genere,
  type ProfileOut,
  type SiNoDaValutare,
  type SiNoIndifferente,
  type SoftCriteriaIn,
} from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import { getUserId } from "@/lib/session";

const GENERE_VALUES: Genere[] = ["Maschile", "Femminile", "Non binario", "Altro"];
const ACCETTA_FIGLI_VALUES: SiNoIndifferente[] = ["Si", "No", "Indifferente"];
const DESIDERA_FIGLI_VALUES: SiNoDaValutare[] = ["Si", "No", "Da valutare"];
const CORPORATURA_VALUES = ["Snella", "Atletica", "Media", "Robusta", "Curvy"] as const;

interface FormState {
  pref_genere_cercato: Genere | "";
  pref_eta_min: string;
  pref_eta_max: string;
  pref_accetta_figli: SiNoIndifferente;
  pref_desidera_figli_futuri: SiNoDaValutare;
  importanza_vicinanza_geografica: string;
  lingue_parlate: string;
  pref_altezza_min: string;
  pref_altezza_max: string;
  pref_stato_civile_accettato: string;
  pref_titolo_studio: string;
  pref_corporatura: string;
  pref_fumo: boolean | null;
  pref_alcol: boolean | null;
  pref_fede_religiosa: string;
  pref_importanza_religione: string;
}

// importanza_vicinanza_geografica arriva da GET /profile già normalizzata
// 0.0-1.0 (v. routers/profile.py) — qui si ricostruisce il Likert 1-5
// originale per lo stesso select riusato nel wizard di onboarding.
function normalizzataAValoreLikert(v: number | null): string {
  if (v === null) return "3";
  return String(Math.round(v * 4) + 1);
}

export default function PreferencesEditPage() {
  const t = useTranslations("preferencesEdit");
  const tPref = useTranslations("onboarding.preferences");
  const tCommon = useTranslations("common");
  const userId = getUserId();

  const [form, setForm] = useState<FormState | null>(null);
  const [saved, setSaved] = useState(false);

  const loadPrefsAction = useAsyncAction(preferencesApi.getPreferences);
  const loadProfileAction = useAsyncAction(profileApi.getProfile);
  const dealbreakerAction = useAsyncAction(preferencesApi.updateDealbreaker);
  const softAction = useAsyncAction(preferencesApi.updateSoft);
  const geoAction = useAsyncAction(profileApi.updateProfile);

  useEffect(() => {
    if (!userId) return;
    Promise.all([loadPrefsAction.run(userId), loadProfileAction.run(userId)]).then(
      ([prefs, profile]) => {
        if (!prefs) return;
        const p = profile as ProfileOut | null;
        setForm({
          pref_genere_cercato: prefs.dealbreaker?.pref_genere_cercato ?? "",
          pref_eta_min: String(prefs.dealbreaker?.pref_eta_min ?? 25),
          pref_eta_max: String(prefs.dealbreaker?.pref_eta_max ?? 45),
          pref_accetta_figli: prefs.dealbreaker?.pref_accetta_figli ?? "Indifferente",
          pref_desidera_figli_futuri: prefs.dealbreaker?.pref_desidera_figli_futuri ?? "Da valutare",
          importanza_vicinanza_geografica: normalizzataAValoreLikert(
            p?.importanza_vicinanza_geografica ?? null
          ),
          lingue_parlate: (p?.lingue_parlate ?? []).join(", "),
          pref_altezza_min: prefs.soft?.pref_altezza_min ? String(prefs.soft.pref_altezza_min) : "",
          pref_altezza_max: prefs.soft?.pref_altezza_max ? String(prefs.soft.pref_altezza_max) : "",
          pref_stato_civile_accettato: prefs.soft?.pref_stato_civile_accettato ?? "",
          pref_titolo_studio: prefs.soft?.pref_titolo_studio ?? "",
          pref_corporatura: prefs.soft?.pref_corporatura ?? "",
          pref_fumo: prefs.soft?.pref_fumo ?? null,
          pref_alcol: prefs.soft?.pref_alcol ?? null,
          pref_fede_religiosa: prefs.soft?.pref_fede_religiosa ?? "",
          pref_importanza_religione: prefs.soft?.pref_importanza_religione
            ? String(prefs.soft.pref_importanza_religione)
            : "",
        });
      }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => (f ? { ...f, [key]: value } : f));
    setSaved(false);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!userId || !form) return;

    const dealbreakerPayload: DealbreakerCriteriaIn = {
      pref_genere_cercato: form.pref_genere_cercato || null,
      pref_eta_min: Number(form.pref_eta_min),
      pref_eta_max: Number(form.pref_eta_max),
      pref_accetta_figli: form.pref_accetta_figli,
      pref_desidera_figli_futuri: form.pref_desidera_figli_futuri,
    };
    const dealbreakerResult = await dealbreakerAction.run(userId, dealbreakerPayload);
    if (!dealbreakerResult) return;

    const geoResult = await geoAction.run(userId, {
      importanza_vicinanza_geografica: Number(form.importanza_vicinanza_geografica),
      lingue_parlate: form.lingue_parlate
        ? form.lingue_parlate.split(",").map((l) => l.trim()).filter(Boolean)
        : null,
    });
    if (!geoResult) return;

    const softPayload: SoftCriteriaIn = {
      pref_altezza_min: form.pref_altezza_min ? Number(form.pref_altezza_min) : null,
      pref_altezza_max: form.pref_altezza_max ? Number(form.pref_altezza_max) : null,
      pref_stato_civile_accettato: form.pref_stato_civile_accettato || null,
      pref_titolo_studio: form.pref_titolo_studio || null,
      pref_corporatura: form.pref_corporatura || null,
      pref_fumo: form.pref_fumo,
      pref_alcol: form.pref_alcol,
      pref_fede_religiosa: form.pref_fede_religiosa || null,
      pref_importanza_religione: form.pref_importanza_religione
        ? Number(form.pref_importanza_religione)
        : null,
    };
    const softResult = await softAction.run(userId, softPayload);
    if (softResult) setSaved(true);
  }

  const loading = loadPrefsAction.loading || loadProfileAction.loading;
  const saving = dealbreakerAction.loading || geoAction.loading || softAction.loading;
  const error = dealbreakerAction.error || geoAction.error || softAction.error;

  return (
    <PageShell>
      <h1 className="font-display text-3xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      {loading && !form && <p className="mt-6 text-sm text-slate">…</p>}
      {loadPrefsAction.error && <Alert tone="error" className="mt-6">{loadPrefsAction.error}</Alert>}

      {form && (
        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-6">
          <Card className="flex flex-col gap-4">
            <Badge tone="navy">{tPref("dealbreakerTitle")}</Badge>
            <p className="text-xs text-slate">{tPref("dealbreakerSubtitle")}</p>

            <SelectField
              label={tPref("genereCercato")}
              value={form.pref_genere_cercato}
              onChange={(e) => update("pref_genere_cercato", e.target.value as Genere | "")}
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
                label={tPref("etaMin")}
                type="number"
                min={18}
                max={99}
                value={form.pref_eta_min}
                onChange={(e) => update("pref_eta_min", e.target.value)}
              />
              <TextField
                label={tPref("etaMax")}
                type="number"
                min={18}
                max={99}
                value={form.pref_eta_max}
                onChange={(e) => update("pref_eta_max", e.target.value)}
              />
            </div>

            <SelectField
              label={tPref("importanzaVicinanza")}
              value={form.importanza_vicinanza_geografica}
              onChange={(e) => update("importanza_vicinanza_geografica", e.target.value)}
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </SelectField>
            <p className="-mt-2 text-xs text-slate">{tPref("importanzaVicinanzaHint")}</p>

            <TextField
              label={tPref("lingueParlate")}
              placeholder={tPref("lingueParlatePlaceholder")}
              value={form.lingue_parlate}
              onChange={(e) => update("lingue_parlate", e.target.value)}
            />
            <p className="-mt-2 text-xs text-slate">{tPref("lingueParlateHint")}</p>

            <div>
              <span className="text-sm font-medium text-navy">{tPref("accettaFigli")}</span>
              <div className="mt-1.5 flex flex-wrap gap-2">
                {ACCETTA_FIGLI_VALUES.map((v) => (
                  <Button
                    key={v}
                    type="button"
                    variant={form.pref_accetta_figli === v ? "primary" : "secondary"}
                    onClick={() => update("pref_accetta_figli", v)}
                  >
                    {tPref(`accettaFigliOptions.${v}`)}
                  </Button>
                ))}
              </div>
            </div>

            <div>
              <span className="text-sm font-medium text-navy">{tPref("desideraFigliFuturi")}</span>
              <div className="mt-1.5 flex flex-wrap gap-2">
                {DESIDERA_FIGLI_VALUES.map((v) => (
                  <Button
                    key={v}
                    type="button"
                    variant={form.pref_desidera_figli_futuri === v ? "primary" : "secondary"}
                    onClick={() => update("pref_desidera_figli_futuri", v)}
                  >
                    {tPref(`desideraFigliFuturiOptions.${v}`)}
                  </Button>
                ))}
              </div>
            </div>
          </Card>

          <Card className="flex flex-col gap-4">
            <Badge tone="gold">{tPref("softTitle")}</Badge>
            <p className="text-xs text-slate">{tPref("softSubtitle")}</p>

            <div className="grid grid-cols-2 gap-4">
              <TextField
                label={tPref("altezzaMin")}
                type="number"
                value={form.pref_altezza_min}
                onChange={(e) => update("pref_altezza_min", e.target.value)}
              />
              <TextField
                label={tPref("altezzaMax")}
                type="number"
                value={form.pref_altezza_max}
                onChange={(e) => update("pref_altezza_max", e.target.value)}
              />
            </div>

            <TextField
              label={tPref("statoCivileAccettato")}
              value={form.pref_stato_civile_accettato}
              onChange={(e) => update("pref_stato_civile_accettato", e.target.value)}
            />

            <TextField
              label={tPref("titoloStudio")}
              value={form.pref_titolo_studio}
              onChange={(e) => update("pref_titolo_studio", e.target.value)}
            />

            <SelectField
              label={tPref("corporatura")}
              value={form.pref_corporatura}
              onChange={(e) => update("pref_corporatura", e.target.value)}
            >
              <option value="">{tPref("noPreference")}</option>
              {CORPORATURA_VALUES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </SelectField>

            <TextField
              label={tPref("fedeReligiosa")}
              value={form.pref_fede_religiosa}
              onChange={(e) => update("pref_fede_religiosa", e.target.value)}
            />

            <SelectField
              label={tPref("importanzaReligione")}
              value={form.pref_importanza_religione}
              onChange={(e) => update("pref_importanza_religione", e.target.value)}
            >
              <option value="">{tPref("noPreference")}</option>
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </SelectField>
          </Card>

          {error && <Alert tone="error">{error}</Alert>}
          {saved && <Badge tone="sage">{t("saved")}</Badge>}

          <Button type="submit" size="lg" disabled={saving} className="self-start">
            {saving ? tCommon("loading") : t("save")}
          </Button>
        </form>
      )}
    </PageShell>
  );
}
