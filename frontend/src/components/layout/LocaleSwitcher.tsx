"use client";

import { useEffect, useRef, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { cn } from "@/lib/cn";

/**
 * RNF-03: selettore della SOLA lingua dell'interfaccia — i dati che
 * arrivano dal backend (profili, report, campi liberi) non passano mai da
 * qui, restano sempre in italiano indipendentemente da questa scelta (v.
 * CLAUDE.md). Cambiare lingua rinaviga la pagina corrente sotto l'altro
 * prefisso locale (/it/... <-> /en/...) tramite il router di next-intl —
 * la libreria i18n già in uso in tutto il progetto (v. src/i18n/routing.ts),
 * nessuna nuova dipendenza. La persistenza tra sessioni è già gestita dal
 * middleware next-intl (cookie NEXT_LOCALE impostato automaticamente ad
 * ogni navigazione con prefisso locale) — nessun codice aggiuntivo per
 * salvarla, verificato dal vivo (v. CLAUDE.md).
 */
export function LocaleSwitcher({ className }: { className?: string }) {
  const t = useTranslations("localeSwitcher");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  function scegli(nuovaLocale: string) {
    setOpen(false);
    router.replace(pathname, { locale: nuovaLocale });
  }

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t("label")}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex h-9 items-center gap-1.5 rounded-full border border-navy/25 bg-ivory px-3 text-xs font-semibold uppercase tracking-wide text-navy transition-colors hover:bg-border",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold"
        )}
      >
        {locale}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-20 mt-2 w-32 rounded-md border border-border bg-ivory-light py-1.5 shadow-card"
        >
          {routing.locales.map((l) => (
            <button
              key={l}
              type="button"
              role="menuitem"
              onClick={() => scegli(l)}
              className={cn(
                "block w-full px-4 py-1.5 text-left text-sm transition-colors hover:bg-border focus-visible:bg-border focus-visible:outline-none",
                l === locale ? "font-semibold text-navy" : "text-slate"
              )}
            >
              {t(`languageNames.${l}`)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
