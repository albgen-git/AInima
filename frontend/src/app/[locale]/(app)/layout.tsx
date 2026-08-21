"use client";

import { useEffect, useState } from "react";
import { AppNav } from "@/components/layout/AppNav";
import { getUserId } from "@/lib/session";
import { useRouter } from "@/i18n/navigation";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Nessuna sessione reale (MVP, v. lib/session.ts) — l'unico controllo
    // possibile è la presenza dello user_id salvato dopo la registrazione.
    if (!getUserId()) {
      router.replace("/onboarding");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReady(true);
  }, [router]);

  if (!ready) return null;

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <AppNav />
      <div className="flex flex-1 justify-center">{children}</div>
    </div>
  );
}
