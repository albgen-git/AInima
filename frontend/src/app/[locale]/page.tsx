import { getTranslations } from "next-intl/server";
import { Button, PageShell } from "@/components/ui";
import { Link } from "@/i18n/navigation";
import { LocaleSwitcher } from "@/components/layout/LocaleSwitcher";

export default async function Home() {
  const t = await getTranslations("common");

  return (
    <main className="flex flex-1 items-center justify-center">
      <LocaleSwitcher className="fixed right-6 top-6" />
      <PageShell className="flex flex-col items-center text-center">
        <h1 className="font-display text-4xl font-medium text-navy">
          {t("appName")}
        </h1>
        <p className="mt-3 max-w-md text-slate">{t("tagline")}</p>
        <Link href="/onboarding" className="mt-10">
          <Button size="lg">{t("continue")}</Button>
        </Link>
      </PageShell>
    </main>
  );
}
