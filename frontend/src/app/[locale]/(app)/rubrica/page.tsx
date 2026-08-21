"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { Alert, Card, PageShell } from "@/components/ui";
import { contactsApi, photoUrl, type RubricaEntry } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import { getUserId } from "@/lib/session";

export default function RubricaPage() {
  const t = useTranslations("rubrica");
  const [entries, setEntries] = useState<RubricaEntry[] | null>(null);
  const { run, loading, error } = useAsyncAction(contactsApi.getRubrica);
  const userId = getUserId();

  useEffect(() => {
    if (!userId) return;
    run(userId).then((result) => {
      if (result) setEntries(result);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <PageShell>
      <h1 className="font-display text-3xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      {loading && !entries && <p className="mt-6 text-sm text-slate">…</p>}
      {error && <Alert tone="error" className="mt-6">{error}</Alert>}

      {entries && entries.length === 0 && (
        <p className="mt-8 text-sm text-slate">{t("empty")}</p>
      )}

      {entries && entries.length > 0 && (
        <div className="mt-6 flex flex-col gap-4">
          {entries.map((entry) => (
            <Card key={entry.match_id} className="flex items-center gap-4">
              {entry.foto_profilo_url && (
                <Image
                  src={photoUrl(entry.foto_profilo_url)}
                  alt=""
                  width={64}
                  height={64}
                  className="h-16 w-16 shrink-0 rounded-full object-cover"
                />
              )}
              <div className="flex-1">
                <p className="font-display text-lg text-navy">
                  {entry.nome} {entry.cognome}
                </p>
                {entry.data_conferma && (
                  <p className="text-xs text-slate">
                    {t("matchedOn", { date: entry.data_conferma.slice(0, 10) })}
                  </p>
                )}
              </div>
              <a
                href={contactsApi.vcardUrl(userId!, entry.match_id)}
                className="rounded-sm border border-navy px-4 py-2 text-sm font-medium text-navy hover:bg-border"
              >
                {t("downloadVcard")}
              </a>
            </Card>
          ))}
        </div>
      )}
    </PageShell>
  );
}
