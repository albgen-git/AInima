"use client";

import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { cn } from "@/lib/cn";

const TABS = [
  { href: "/dashboard", key: "dashboard" },
  { href: "/proposal", key: "proposal" },
  { href: "/rubrica", key: "rubrica" },
  { href: "/profile", key: "profile" },
  { href: "/preferences", key: "preferences" },
] as const;

export function AppNav() {
  const t = useTranslations("nav");
  const pathname = usePathname();

  return (
    <header className="border-b border-border bg-ivory-light">
      <div className="mx-auto flex max-w-[720px] items-center justify-between px-6 py-4">
        <Link href="/dashboard" className="font-display text-lg text-navy">
          Ainima
        </Link>
        <nav className="flex gap-1">
          {TABS.map((tab) => {
            const active = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={cn(
                  "rounded-sm px-3 py-1.5 text-sm font-medium transition-colors",
                  active ? "bg-navy text-ivory-light" : "text-slate hover:bg-border"
                )}
              >
                {t(tab.key)}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
