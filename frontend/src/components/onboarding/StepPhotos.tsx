"use client";

import { ChangeEvent } from "react";
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
}) {
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

      {uploadedUrl ? (
        <div className="flex items-center gap-3">
          <Badge tone="sage">{uploadedLabel}</Badge>
          <label className="cursor-pointer text-sm text-navy underline">
            {changeLabel}
            <input type="file" accept="image/*" className="hidden" onChange={handleChange} />
          </label>
        </div>
      ) : (
        <label>
          <Button
            type="button"
            variant="secondary"
            disabled={uploading}
            className="pointer-events-none"
          >
            {uploading ? uploadingLabel : uploadLabel}
          </Button>
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleChange}
            disabled={uploading}
          />
        </label>
      )}
      {error && <Alert tone="error">{error}</Alert>}
    </div>
  );
}

export function StepPhotos({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.photos");
  const tCommon = useTranslations("common");

  const profileUpload = useAsyncAction(profileApi.uploadProfilePhoto);
  const idealUpload = useAsyncAction(profileApi.uploadIdealPartnerPhoto);

  async function handleUploadProfile(file: File) {
    if (!state.userId) return;
    const result = await profileUpload.run(state.userId, file);
    if (result) update("foto_profilo_url", result.foto_profilo_url);
  }

  async function handleUploadIdeal(file: File) {
    if (!state.userId) return;
    const result = await idealUpload.run(state.userId, file);
    if (result) update("foto_partner_ideale_url", result.foto_partner_ideale_url);
  }

  const canContinue = !!state.foto_profilo_url;

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      <div className="mt-6 flex flex-col gap-8">
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
