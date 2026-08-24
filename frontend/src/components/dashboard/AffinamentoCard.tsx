"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Alert, Button, Card } from "@/components/ui";
import { cn } from "@/lib/cn";
import { engagementApi } from "@/lib/api";
import type { AffinamentoItemOut } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";

const SCALE = [1, 2, 3, 4, 5] as const;

/**
 * Stato "Domande di affinamento pendenti" (Ainima_Dashboard_Trigger_Email_v1.md
 * §1, priorità 2) — teaser collassato di default, espandendo pesca gli item
 * completi (con item_id) via GET /affinamento/pendenti, poi li presenta uno
 * alla volta con la stessa scala 1-5 usata nell'onboarding. onCompleted
 * viene chiamato quando tutte le domande di QUESTO batch sono state
 * risposte, per far ricaricare la dashboard al genitore.
 */
export function AffinamentoCard({
  userId,
  count,
  onCompleted,
}: {
  userId: string;
  count: number;
  onCompleted: () => void;
}) {
  const t = useTranslations("dashboard.affinamento");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const [espansa, setEspansa] = useState(false);
  const [items, setItems] = useState<AffinamentoItemOut[] | null>(null);
  const [indice, setIndice] = useState(0);
  const { run: carica, loading: caricando, error: erroreCaricamento } = useAsyncAction(
    engagementApi.getDomandePendenti
  );
  const { run: rispondi, loading: rispondendo, error: erroreRisposta } = useAsyncAction(
    engagementApi.rispondiAffinamento
  );

  async function espandi() {
    setEspansa(true);
    const risultato = await carica(userId);
    if (risultato) setItems(risultato);
  }

  async function seleziona(valore: number) {
    if (!items) return;
    const item = items[indice];
    const ok = await rispondi(userId, item.item_id, { risposta: valore });
    if (!ok) return;
    if (indice + 1 < items.length) {
      setIndice((i) => i + 1);
    } else {
      onCompleted();
    }
  }

  if (!espansa) {
    return (
      <Card className="border-gold/30 bg-ivory-light">
        <h2 className="font-display text-xl text-navy">{t("title")}</h2>
        <p className="mt-1 text-sm text-slate">{t("teaser", { count })}</p>
        <Button className="mt-4" onClick={espandi} disabled={caricando}>
          {caricando ? tCommon("loading") : t("cta")}
        </Button>
        {erroreCaricamento && <Alert tone="error" className="mt-3">{erroreCaricamento}</Alert>}
      </Card>
    );
  }

  if (!items) {
    return (
      <Card className="border-gold/30 bg-ivory-light">
        <p className="text-sm text-slate">{tCommon("loading")}</p>
      </Card>
    );
  }

  const item = items[indice];

  return (
    <Card className="border-gold/30 bg-ivory-light">
      <h2 className="font-display text-xl text-navy">{t("title")}</h2>
      <p className="mt-2 text-xs text-slate">
        {t("progress", { current: indice + 1, total: items.length })}
      </p>
      <p className="mt-4 min-h-12 font-display text-lg text-navy">
        {locale === "it" ? item.testo_it : item.testo_en}
      </p>
      <div className="mt-4 flex flex-col gap-2">
        {SCALE.map((valore, i) => (
          <button
            key={valore}
            type="button"
            disabled={rispondendo}
            onClick={() => seleziona(valore)}
            className={cn(
              "rounded-xl border border-border bg-white px-4 py-2.5 text-left text-sm text-navy transition-colors hover:border-navy hover:bg-border disabled:opacity-50"
            )}
          >
            {t(`scale${i + 1}` as "scale1")}
          </button>
        ))}
      </div>
      {erroreRisposta && <Alert tone="error" className="mt-3">{erroreRisposta}</Alert>}
    </Card>
  );
}
