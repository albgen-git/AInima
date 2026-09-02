"use client";

import { ChangeEvent, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, Badge, Button, Card } from "@/components/ui";
import { profileApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import type { StepProps } from "@/lib/wizard/types";

function PhotoUploadBlock({
  label,
  hint,
  required,
  uploadedUrl,
  onUpload,
  uploading,
  error,
  uploadLabel,
  uploadingLabel,
  uploadedLabel,
  changeLabel,
  multipleFacesWarning,
  showMultipleFacesWarning,
}: {
  label: string;
  hint: string;
  required?: boolean;
  uploadedUrl: string | null;
  onUpload: (file: File) => void;
  uploading: boolean;
  error: string | null;
  uploadLabel: string;
  uploadingLabel: string;
  uploadedLabel: string;
  changeLabel: string;
  multipleFacesWarning: string;
  showMultipleFacesWarning: boolean;
}) {
  // Ref + click() programmatico invece del trucco <label> + pointer-events-none:
  // quel pattern si affida all'attivazione nativa "click sulla label inoltra
  // all'input associato", che su alcuni browser mobile (Safari iOS in
  // particolare, caso reale segnalato dall'utente testando da cellulare) non
  // sempre inoltra il tap quando l'elemento visibile ha pointer-events:none —
  // il pulsante appariva presente ma non rispondeva al tocco. Un onClick
  // esplicito su un bottone realmente cliccabile è il pattern standard, non
  // soggetto a questa incoerenza cross-browser.
  const inputRef = useRef<HTMLInputElement>(null);

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  }

  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-medium text-navy">
        {label}
        {required && <span className="text-navy"> *</span>}
      </span>
      <p className="text-xs text-slate">{hint}</p>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleChange}
        disabled={uploading}
      />

      {uploadedUrl ? (
        <div className="flex items-center gap-3">
          <Badge tone="sage">{uploadedLabel}</Badge>
          <button
            type="button"
            className="cursor-pointer text-sm text-navy underline"
            onClick={() => inputRef.current?.click()}
          >
            {changeLabel}
          </button>
        </div>
      ) : (
        <Button
          type="button"
          variant="secondary"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          {uploading ? uploadingLabel : uploadLabel}
        </Button>
      )}
      {error && <Alert tone="error">{error}</Alert>}
      {showMultipleFacesWarning && <Alert tone="info">{multipleFacesWarning}</Alert>}
    </div>
  );
}

export function StepPhotos({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.photos");
  const tCommon = useTranslations("common");

  const profileUpload = useAsyncAction(profileApi.uploadProfilePhoto);
  const idealUpload = useAsyncAction(profileApi.uploadIdealPartnerPhoto);
  // RF-08c: avviso "più volti rilevati" — non blocca l'upload (v.
  // backend/routers/profile.py), solo un segnale informativo dopo il
  // salvataggio.
  const [profileMultiFace, setProfileMultiFace] = useState(false);
  const [idealMultiFace, setIdealMultiFace] = useState(false);

  async function handleUploadProfile(file: File) {
    if (!state.userId) return;
    const result = await profileUpload.run(state.userId, file);
    if (result) {
      update("foto_profilo_url", result.foto_profilo_url);
      setProfileMultiFace(result.volti_multipli_rilevati);
    }
  }

  async function handleUploadIdeal(file: File) {
    if (!state.userId) return;
    const result = await idealUpload.run(state.userId, file);
    if (result) {
      update("foto_partner_ideale_url", result.foto_partner_ideale_url);
      setIdealMultiFace(result.volti_multipli_rilevati);
    }
  }

  const canContinue = !!state.foto_profilo_url;

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      <div className="mt-6 flex flex-col gap-8">
        {/* RF-08d: indicazioni di qualità mostrate PRIMA del tentativo di
            upload, non solo come messaggio d'errore dopo un rifiuto. */}
        <Alert tone="info">{t("faceGuidance")}</Alert>

        <PhotoUploadBlock
          label={t("profileLabel")}
          hint={t("profileHint")}
          required
          uploadedUrl={state.foto_profilo_url}
          onUpload={handleUploadProfile}
          uploading={profileUpload.loading}
          error={profileUpload.error}
          uploadLabel={t("upload")}
          uploadingLabel={t("uploading")}
          uploadedLabel={t("uploaded")}
          changeLabel={t("changePhoto")}
          multipleFacesWarning={t("multipleFacesWarning")}
          showMultipleFacesWarning={profileMultiFace}
        />

        <PhotoUploadBlock
          label={t("idealLabel")}
          hint={t("idealHint")}
          uploadedUrl={state.foto_partner_ideale_url}
          onUpload={handleUploadIdeal}
          uploading={idealUpload.loading}
          error={idealUpload.error}
          uploadLabel={t("upload")}
          uploadingLabel={t("uploading")}
          uploadedLabel={t("uploaded")}
          changeLabel={t("changePhoto")}
          multipleFacesWarning={t("multipleFacesWarning")}
          showMultipleFacesWarning={idealMultiFace}
        />

        <Alert tone="info">{t("moderationNote")}</Alert>

        <div className="flex gap-3">
          <Button variant="secondary" type="button" onClick={onBack}>
            {tCommon("back")}
          </Button>
          <Button type="button" onClick={onNext} disabled={!canContinue}>
            {tCommon("continue")}
          </Button>
        </div>
      </div>
    </Card>
  );
}
