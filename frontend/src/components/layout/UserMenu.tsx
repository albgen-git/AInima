"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { profileApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import { clearUserId, getUserId } from "@/lib/session";
import { cn } from "@/lib/cn";

/**
 * RF-27b: icona utente in alto a destra, presente su tutte le schermate
 * autenticate (montata una sola volta in AppNav, che è già condiviso da
 * tutte — v. app/[locale]/(app)/layout.tsx). Nessuna sessione reale da
 * invalidare lato server (v. lib/session.ts: il JWT emesso alla verifica
 * OTP non è ancora verificato da nessuna rotta, v. CLAUDE.md) — il logout
 * è quindi solo client-side (rimuove user_id/token da localStorage).
 */
export function UserMenu() {
  const t = useTranslations("userMenu");
  const router = useRouter();
  const userId = getUserId();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const firstItemRef = useRef<HTMLAnchorElement>(null);
  const { run, loading } = useAsyncAction(profileApi.getProfile);
  const [nomeCompleto, setNomeCompleto] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !userId || nomeCompleto || loading) return;
    run(userId).then((result) => {
      if (result) setNomeCompleto(`${result.nome ?? ""} ${result.cognome ?? ""}`.trim());
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (!open) return;
    firstItemRef.current?.focus();

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

  function handleLogout() {
    clearUserId();
    setOpen(false);
    router.push("/onboarding");
  }

  if (!userId) return null;

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t("openMenu")}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex h-9 w-9 items-center justify-center rounded-full border border-navy/25 bg-ivory text-navy transition-colors hover:bg-border",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold"
        )}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="1.7" />
          <path
            d="M4 20c1.6-3.6 5-5.5 8-5.5s6.4 1.9 8 5.5"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
          />
        </svg>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-20 mt-2 w-56 rounded-md border border-border bg-ivory-light py-2 shadow-card"
        >
          <p className="truncate px-4 py-1.5 text-sm font-medium text-navy">
            {nomeCompleto || "…"}
          </p>
          <div className="my-1 border-t border-border" />
          <Link
            ref={firstItemRef}
            href="/profile"
            role="menuitem"
            onClick={() => setOpen(false)}
            className="block px-4 py-2 text-sm text-navy hover:bg-border focus-visible:bg-border focus-visible:outline-none"
          >
            {t("editProfile")}
          </Link>
          <Link
            href="/dashboard#foto"
            role="menuitem"
            onClick={() => setOpen(false)}
            className="block px-4 py-2 text-sm text-navy hover:bg-border focus-visible:bg-border focus-visible:outline-none"
          >
            {t("photos")}
          </Link>
          <div className="my-1 border-t border-border" />
          <button
            type="button"
            role="menuitem"
            onClick={handleLogout}
            className="block w-full px-4 py-2 text-left text-sm text-terracotta hover:bg-border focus-visible:bg-border focus-visible:outline-none"
          >
            {t("logout")}
          </button>
        </div>
      )}
    </div>
  );
}
