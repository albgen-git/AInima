"use client";

import { FormEvent, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, Badge, Button, Card, PageShell, SelectField, TextField } from "@/components/ui";
import { profileApi, type ProfileOut, type ProfileUpdate } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import { getUserId } from "@/lib/session";

const CORPORATURA_VALUES = ["Snella", "Atletica", "Media", "Robusta", "Curvy"] as const;
const TITOLO_STUDIO_VALUES = [
  "Diploma",
  "Laurea triennale",
  "Laurea magistrale",
  "Dottorato",
  "Altro",
] as const;
const STATO_CIVILE_VALUES = ["Celibe/Nubile", "Divorziato/a", "Vedovo/a", "Separato/a"] as const;

export default function ProfileEditPage() {
  const t = useTranslations("profileEdit");
  const tProfile = useTranslations("onboarding.profile");
  const tCivil = useTranslations("onboarding.civilStatus");
  const tCommon = useTranslations("common");
  const userId = getUserId();

  const [profile, setProfile] = useState<ProfileOut | null>(null);
  const [saved, setSaved] = useState(false);
  const loadAction = useAsyncAction(profileApi.getProfile);
  const saveAction = useAsyncAction(profileApi.updateProfile);

  useEffect(() => {
    if (!userId) return;
    loadAction.run(userId).then((result) => {
      if (result) setProfile(result);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function update<K extends keyof ProfileOut>(key: K, value: ProfileOut[K]) {
    setProfile((p) => (p ? { ...p, [key]: value } : p));
    setSaved(false);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!userId || !profile) return;
    const payload: ProfileUpdate = {
      // altezza_cm volutamente ESCLUSA (v. CLAUDE.md, decisione esplicita
      // dell'utente): non cambia nel tempo, e permetterne la modifica dopo
      // la registrazione aprirebbe a un possibile "barare" sull'algoritmo di
      // matching. Il backend la ignorerebbe comunque una volta impostata
      // (v. routers/profile.py aggiorna_profilo), ma qui non è nemmeno
      // mostrata come campo modificabile, per chiarezza.
      peso_kg: profile.peso_kg,
      corporatura: profile.corporatura,
      colore_capelli: profile.colore_capelli,
      colore_occhi: profile.colore_occhi,
      fumo: profile.fumo,
      alcol: profile.alcol,
      stile_vita_sport: profile.stile_vita_sport,
      comune_residenza: profile.comune_residenza,
      titolo_studio: profile.titolo_studio,
      settore_occupazionale: profile.settore_occupazionale,
      fascia_reddito: profile.fascia_reddito,
      fede_religiosa: profile.fede_religiosa,
      importanza_religione: profile.importanza_religione,
      stato_civile: profile.stato_civile,
      ha_figli: profile.ha_figli,
    };
    const result = await saveAction.run(userId, payload);
    if (result) setSaved(true);
  }

  return (
    <PageShell>
      <h1 className="font-display text-3xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      {loadAction.loading && !profile && <p className="mt-6 text-sm text-slate">…</p>}
      {loadAction.error && <Alert tone="error" className="mt-6">{loadAction.error}</Alert>}

      {profile && (
        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-6">
          <Card>
            <div className="grid grid-cols-2 gap-4 text-sm text-slate">
              <div>
                <p className="text-xs uppercase tracking-wide">{tCommon("required")}</p>
                <p className="mt-1 font-medium text-navy">
                  {profile.nome} {profile.cognome}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide">{profile.data_nascita}</p>
              </div>
            </div>
          </Card>

          <Card className="flex flex-col gap-4">
            <SelectField
              label={tCivil("statoCivileLabel")}
              value={profile.stato_civile ?? ""}
              onChange={(e) => update("stato_civile", e.target.value)}
            >
              <option value="">—</option>
              {STATO_CIVILE_VALUES.map((s) => (
                <option key={s} value={s}>
                  {tCivil(`statoCivileOptions.${s}`)}
                </option>
              ))}
            </SelectField>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-navy">{tProfile("altezza")}</p>
                <p className="mt-1.5 rounded-sm border border-border bg-ivory px-3 py-2 text-sm text-slate">
                  {profile.altezza_cm ?? "—"}
                </p>
                <p className="mt-1 text-xs text-slate">{t("altezzaBloccata")}</p>
              </div>
              <TextField
                label={tProfile("peso")}
                type="number"
                value={profile.peso_kg ?? ""}
                onChange={(e) => update("peso_kg", e.target.value ? Number(e.target.value) : null)}
              />
            </div>

            <SelectField
              label={tProfile("corporatura")}
              value={profile.corporatura ?? ""}
              onChange={(e) => update("corporatura", e.target.value)}
            >
              <option value="">—</option>
              {CORPORATURA_VALUES.map((c) => (
                <option key={c} value={c}>
                  {tProfile(`corporaturaOptions.${c}`)}
                </option>
              ))}
            </SelectField>

            <div className="grid grid-cols-2 gap-4">
              <TextField
                label={tProfile("coloreCapelli")}
                value={profile.colore_capelli ?? ""}
                onChange={(e) => update("colore_capelli", e.target.value)}
              />
              <TextField
                label={tProfile("coloreOcchi")}
                value={profile.colore_occhi ?? ""}
                onChange={(e) => update("colore_occhi", e.target.value)}
              />
            </div>

            <TextField
              label={tProfile("stileVitaSport")}
              value={profile.stile_vita_sport ?? ""}
              onChange={(e) => update("stile_vita_sport", e.target.value)}
            />
          </Card>

          <Card className="flex flex-col gap-4">
            <TextField
              label={tProfile("comuneResidenza")}
              value={profile.comune_residenza ?? ""}
              onChange={(e) => update("comune_residenza", e.target.value)}
            />

            <SelectField
              label={tProfile("titoloStudio")}
              value={profile.titolo_studio ?? ""}
              onChange={(e) => update("titolo_studio", e.target.value)}
            >
              <option value="">—</option>
              {TITOLO_STUDIO_VALUES.map((v) => (
                <option key={v} value={v}>
                  {tProfile(`titoloStudioOptions.${v}`)}
                </option>
              ))}
            </SelectField>

            <TextField
              label={tProfile("settoreOccupazionale")}
              value={profile.settore_occupazionale ?? ""}
              onChange={(e) => update("settore_occupazionale", e.target.value)}
            />

            <TextField
              label={tProfile("fedeReligiosa")}
              value={profile.fede_religiosa ?? ""}
              onChange={(e) => update("fede_religiosa", e.target.value)}
            />
          </Card>

          {saveAction.error && <Alert tone="error">{saveAction.error}</Alert>}
          {saved && <Badge tone="sage">{t("saved")}</Badge>}

          <Button type="submit" size="lg" disabled={saveAction.loading} className="self-start">
            {saveAction.loading ? tCommon("loading") : t("save")}
          </Button>
        </form>
      )}
    </PageShell>
  );
}
