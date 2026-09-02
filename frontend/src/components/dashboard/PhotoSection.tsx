"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, Button, Card } from "@/components/ui";
import { photoUrl, profileApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";

function PhotoSlotView({
  label,
  emptyLabel,
  url,
  loading,
  error,
  inRevisione,
  volteMultipli,
  onFile,
}: {
  label: string;
  emptyLabel: string;
  url: string | null;
  loading: boolean;
  error: string | null;
  inRevisione: boolean;
  volteMultipli: boolean;
  onFile: (file: File) => void;
}) {
  const t = useTranslations("dashboard.photos");
  const inputRef = useRef<HTMLInputElement>(null);

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) onFile(file);
  }

  return (
    <div>
      <p className="mb-2 text-center text-xs font-medium uppercase tracking-wide text-slate">{label}</p>
      <div className="flex flex-col items-center gap-3">
        <div className="h-32 w-32 overflow-hidden rounded-full border border-border bg-ivory">
          {url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={photoUrl(url)} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center px-2 text-center text-xs text-slate">
              {emptyLabel}
            </div>
          )}
        </div>

        <input ref={inputRef} type="file" accept="image/*" className="hidden" onChange={handleChange} />
        <Button
          type="button"
          variant="secondary"
          disabled={loading}
          onClick={() => inputRef.current?.click()}
        >
          {loading ? t("uploading") : url ? t("change") : t("upload")}
        </Button>

        {inRevisione && <Alert tone="info">{t("pendingModeration")}</Alert>}
        {volteMultipli && <Alert tone="info">{t("multipleFacesWarning")}</Alert>}
        {error && <Alert tone="error">{error}</Alert>}
      </div>
    </div>
  );
}

export function PhotoSection({ userId }: { userId: string }) {
  const t = useTranslations("dashboard.photos");
  const [fotoProfilo, setFotoProfilo] = useState<string | null>(null);
  const [fotoIdeale, setFotoIdeale] = useState<string | null>(null);
  const [revisioneProfilo, setRevisioneProfilo] = useState(false);
  const [revisioneIdeale, setRevisioneIdeale] = useState(false);
  // RF-08c: avviso "più volti rilevati" (AWS Rekognition DetectFaces) —
  // non blocca l'upload, solo un segnale informativo.
  const [multiFaceProfilo, setMultiFaceProfilo] = useState(false);
  const [multiFaceIdeale, setMultiFaceIdeale] = useState(false);
  const loadAction = useAsyncAction(profileApi.getProfile);
  const profiloAction = useAsyncAction(profileApi.uploadProfilePhoto);
  const idealeAction = useAsyncAction(profileApi.uploadIdealPartnerPhoto);

  useEffect(() => {
    loadAction.run(userId).then((result) => {
      if (!result) return;
      setFotoProfilo(result.foto_profilo_url);
      setFotoIdeale(result.foto_partner_ideale_url);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  // RF-06b: se la scansione automatica segnala l'immagine come 'Sospetta',
  // NON aggiorniamo la foto mostrata (resta quella precedente, se c'era)
  // invece di sostituirla silenziosamente con una non ancora approvata.
  // Limite noto, non risolvibile solo lato frontend: il backend sovrascrive
  // comunque foto_*_url alla nuova immagine al momento dell'upload (nessun
  // campo di staging separato oggi) — un ricaricamento della pagina
  // mostrerebbe quindi la nuova foto in revisione. Segnalato come lavoro
  // successivo lato backend, non implementato qui (fuori dallo scope
  // "solo frontend" di questa modifica).
  async function handleProfiloFile(file: File) {
    setRevisioneProfilo(false);
    setMultiFaceProfilo(false);
    const result = await profiloAction.run(userId, file);
    if (!result) return;
    setMultiFaceProfilo(result.volti_multipli_rilevati);
    if (result.esito_moderazione === "Sospetta") {
      setRevisioneProfilo(true);
      return;
    }
    setFotoProfilo(result.foto_profilo_url);
  }

  async function handleIdealeFile(file: File) {
    setRevisioneIdeale(false);
    setMultiFaceIdeale(false);
    const result = await idealeAction.run(userId, file);
    if (!result) return;
    setMultiFaceIdeale(result.volti_multipli_rilevati);
    if (result.esito_moderazione === "Sospetta") {
      setRevisioneIdeale(true);
      return;
    }
    setFotoIdeale(result.foto_partner_ideale_url);
  }

  return (
    <Card id="foto" className="scroll-mt-6">
      <h2 className="font-display text-xl text-navy">{t("title")}</h2>
      <p className="mt-1 text-sm text-slate">{t("subtitle")}</p>

      {/* RF-08d: indicazioni di qualità mostrate PRIMA del tentativo di
          upload, non solo come messaggio d'errore dopo un rifiuto. */}
      <Alert tone="info" className="mt-4">{t("faceGuidance")}</Alert>

      <div className="mt-5 grid grid-cols-2 gap-6">
        <PhotoSlotView
          label={t("profileLabel")}
          emptyLabel={t("noPhoto")}
          url={fotoProfilo}
          loading={profiloAction.loading}
          error={profiloAction.error}
          inRevisione={revisioneProfilo}
          volteMultipli={multiFaceProfilo}
          onFile={handleProfiloFile}
        />
        <PhotoSlotView
          label={t("idealLabel")}
          emptyLabel={t("noIdealPhoto")}
          url={fotoIdeale}
          loading={idealeAction.loading}
          error={idealeAction.error}
          inRevisione={revisioneIdeale}
          volteMultipli={multiFaceIdeale}
          onFile={handleIdealeFile}
        />
      </div>
    </Card>
  );
}
