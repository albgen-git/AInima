"use client";

import { useTranslations } from "next-intl";

/**
 * "Stato civile gradito nel partner" (pref_stato_civile_accettato) — RF-08,
 * multi-selezione (2026-09-05, richiesta esplicita dell'utente): un utente
 * può accettare più stati civile contemporaneamente, "Separato/a" resta
 * distinto da "Divorziato/a" (implicazioni pratiche diverse).
 *
 * "Nessuna preferenza" è una spunta DERIVATA, mai un vero 5° valore salvato:
 * è selezionata quando e solo quando tutte e 4 le opzioni lo sono
 * (bidirezionale: spuntarle tutte a mano la attiva da sola). Cliccarla la
 * attiva (seleziona tutte e 4); non è mai possibile usarla per svuotare la
 * selezione, perché un filtro vuoto ("non accetto nessuno stato civile")
 * non ha senso operativo — v. CLAUDE.md. Per lo stesso motivo, l'ultima
 * opzione rimasta selezionata non può essere deselezionata singolarmente.
 */
export const STATO_CIVILE_ACCETTATO_OPTIONS = [
  "Celibe/Nubile",
  "Separato/a",
  "Divorziato/a",
  "Vedovo/a",
] as const;

export function StatoCivileAccettatoField({
  value,
  onChange,
}: {
  value: string[];
  onChange: (next: string[]) => void;
}) {
  const t = useTranslations("onboarding.preferences");
  const tCivilStatus = useTranslations("onboarding.civilStatus");

  const tuttiSelezionati = STATO_CIVILE_ACCETTATO_OPTIONS.every((o) => value.includes(o));

  function toggleOpzione(opzione: string) {
    const attivo = value.includes(opzione);
    if (attivo) {
      if (value.length === 1) return; // non permette di svuotare del tutto
      onChange(value.filter((v) => v !== opzione));
    } else {
      onChange([...value, opzione]);
    }
  }

  function selezionaTutte() {
    if (!tuttiSelezionati) {
      onChange([...STATO_CIVILE_ACCETTATO_OPTIONS]);
    }
    // già tutte selezionate: no-op, "Nessuna preferenza" non svuota mai la selezione
  }

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm font-medium text-navy">{t("statoCivileAccettato")}</span>

      <div className="flex flex-col gap-2 rounded-sm border border-border bg-ivory p-3">
        <label className="flex items-center gap-3 border-b border-border pb-2 text-sm font-medium text-navy">
          <input
            type="checkbox"
            className="h-4 w-4 accent-navy"
            checked={tuttiSelezionati}
            onChange={selezionaTutte}
          />
          {t("noPreference")}
        </label>

        {STATO_CIVILE_ACCETTATO_OPTIONS.map((opzione) => (
          <label key={opzione} className="flex items-center gap-3 text-sm text-navy">
            <input
              type="checkbox"
              className="h-4 w-4 accent-navy"
              checked={value.includes(opzione)}
              onChange={() => toggleOpzione(opzione)}
            />
            {tCivilStatus(`statoCivileOptions.${opzione}`)}
          </label>
        ))}
      </div>

      <span className="text-xs text-slate">{t("statoCivileHint")}</span>
    </div>
  );
}
