"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, Button, TextareaField } from "@/components/ui";
import { personalReportApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import { cn } from "@/lib/cn";

function Stella({
  piena,
  onClick,
  onMouseEnter,
  onMouseLeave,
  label,
}: {
  piena: boolean;
  onClick: () => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      aria-label={label}
      className="rounded-sm p-0.5 transition-transform hover:scale-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold"
    >
      <svg
        width="26"
        height="26"
        viewBox="0 0 24 24"
        fill={piena ? "var(--color-gold, #B8934A)" : "none"}
        stroke="var(--color-navy, #1B2340)"
        strokeWidth="1.3"
        strokeLinejoin="round"
      >
        <path d="M12 3.5l2.47 5.18 5.53.66-4.1 3.87 1.08 5.55L12 15.9l-4.98 2.86 1.08-5.55-4.1-3.87 5.53-.66L12 3.5z" />
      </svg>
    </button>
  );
}

/**
 * RF-30: valutazione a stelle + commento libero sotto il report di analisi
 * personale. Non uno widget da "recensione prodotto": stelle disegnate a
 * mano (non un'icon-font generica) in oro/navy come il resto della guida di
 * stile, etichetta introspettiva, nessun conteggio "voti totali" o simili
 * elementi da e-commerce.
 */
export function ReportFeedback({ userId, reportId }: { userId: string; reportId: string }) {
  const t = useTranslations("dashboard.personalReport.feedback");
  const [stelle, setStelle] = useState(0);
  const [hoverStelle, setHoverStelle] = useState(0);
  const [commento, setCommento] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const loadAction = useAsyncAction(personalReportApi.getFeedback);
  const sendAction = useAsyncAction(personalReportApi.inviaFeedback);

  useEffect(() => {
    loadAction.run(userId, reportId).then((result) => {
      if (result?.esiste) {
        setStelle(result.valutazione_stelle);
        setCommento(result.commento_libero ?? "");
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, reportId]);

  async function handleSubmit() {
    if (stelle < 1) return;
    const result = await sendAction.run(userId, reportId, {
      valutazione_stelle: stelle,
      commento_libero: commento.trim() || null,
    });
    if (result?.registrato) setSubmitted(true);
  }

  if (submitted) {
    return (
      <div className="mt-6 border-t border-border pt-5">
        <p className="text-sm text-slate">{t("thanks")}</p>
      </div>
    );
  }

  return (
    <div className="mt-6 border-t border-border pt-5">
      <p className="text-sm font-medium text-navy">{t("question")}</p>
      <div className="mt-2 flex gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <Stella
            key={n}
            piena={n <= (hoverStelle || stelle)}
            onClick={() => setStelle(n)}
            onMouseEnter={() => setHoverStelle(n)}
            onMouseLeave={() => setHoverStelle(0)}
            label={t("starLabel", { n })}
          />
        ))}
      </div>

      <TextareaField
        className="mt-4"
        placeholder={t("commentPlaceholder")}
        value={commento}
        onChange={(e) => setCommento(e.target.value)}
        rows={3}
      />

      {sendAction.error && <Alert tone="error" className="mt-3">{sendAction.error}</Alert>}

      <Button
        type="button"
        variant="secondary"
        className={cn("mt-4", stelle < 1 && "opacity-50")}
        disabled={stelle < 1 || sendAction.loading}
        onClick={handleSubmit}
      >
        {sendAction.loading ? t("sending") : t("submit")}
      </Button>
    </div>
  );
}
