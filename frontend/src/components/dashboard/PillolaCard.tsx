"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, Button, Card } from "@/components/ui";
import { engagementApi } from "@/lib/api";
import type { PillolaPendenteOut } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";

/**
 * Stato "Pillola da leggere" (Ainima_Dashboard_Trigger_Email_v1.md §1,
 * priorità 3) — teaser di una riga collassato, espandendo mostra il testo
 * pieno e segna la pillola come aperta (non scompare finché l'utente non
 * ricarica/torna in dashboard, per non far sparire il contenuto mentre lo
 * sta ancora leggendo).
 */
export function PillolaCard({ userId, pillola }: { userId: string; pillola: PillolaPendenteOut }) {
  const t = useTranslations("dashboard.pillola");
  const [espansa, setEspansa] = useState(false);
  const { run: segnaAperta, error } = useAsyncAction(engagementApi.segnaPillolaAperta);

  async function espandi() {
    setEspansa(true);
    await segnaAperta(userId, pillola.pillola_id);
  }

  const teaser = pillola.testo.length > 110 ? `${pillola.testo.slice(0, 110)}…` : pillola.testo;

  return (
    <Card className="border-navy/15 bg-white">
      <h2 className="font-display text-xl text-navy">{t("title")}</h2>
      <p className="mt-1 font-medium text-navy">{pillola.titolo}</p>
      {espansa ? (
        <p className="mt-2 whitespace-pre-line text-sm text-slate">{pillola.testo}</p>
      ) : (
        <>
          <p className="mt-2 text-sm text-slate">{teaser}</p>
          <Button className="mt-4" variant="secondary" onClick={espandi}>
            {t("cta")}
          </Button>
        </>
      )}
      {error && <Alert tone="error" className="mt-3">{error}</Alert>}
    </Card>
  );
}
