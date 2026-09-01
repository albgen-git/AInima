"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { PageShell, ProgressSteps } from "@/components/ui";
import { LocaleSwitcher } from "@/components/layout/LocaleSwitcher";
import { authApi } from "@/lib/api";
import { clearUserId, getUserId } from "@/lib/session";
import { initialWizardState, WizardState } from "@/lib/wizard/types";
import { useRouter } from "@/i18n/navigation";
import { StepEmail } from "@/components/onboarding/StepEmail";
import { StepOtpVerify } from "@/components/onboarding/StepOtpVerify";
import { StepBasicInfo } from "@/components/onboarding/StepBasicInfo";
import { StepSensitiveConsent } from "@/components/onboarding/StepSensitiveConsent";
import { StepOrientation } from "@/components/onboarding/StepOrientation";
import { StepPayment } from "@/components/onboarding/StepPayment";
import { StepCivilStatus } from "@/components/onboarding/StepCivilStatus";
import { StepProfile } from "@/components/onboarding/StepProfile";
import { StepPhotos } from "@/components/onboarding/StepPhotos";
import { StepPreferences } from "@/components/onboarding/StepPreferences";
import { StepBigFive } from "@/components/onboarding/StepBigFive";
import { StepAttaccamento } from "@/components/onboarding/StepAttaccamento";
import { StepEq } from "@/components/onboarding/StepEq";
import { StepProfiloRelazionale } from "@/components/onboarding/StepProfiloRelazionale";
import { StepNarrative } from "@/components/onboarding/StepNarrative";
import { StepInterestTags } from "@/components/onboarding/StepInterestTags";
import { StepSummary } from "@/components/onboarding/StepSummary";

// L'ordine qui deve restare 1:1 con STEP_* in backend/routers/auth.py
// (primo_passo_incompleto si aspetta gli stessi indici).
//
// 2026-08-19 (v. CLAUDE.md): "interview" (chat EQ, StepInterview.tsx) non è
// più nel flusso attivo — sostituito da 3 step scritti: "attaccamento",
// "eq" (test a punteggio deterministico) e "narrative" (i due campi liberi
// RF-07b). StepInterview.tsx non è stato cancellato (v. CLAUDE.md), solo
// rimosso da questo array.
//
// 2026-08-20 (v. CLAUDE.md, punto 5 audit): nuovo step "interestTags" —
// liste "mi piace/non sopporto" (RF-08c, Ainima_Liste_Piace_Detesta_v1.md),
// a differenza di "narrative" queste ENTRANO nel calcolo del match.
//
// 2026-08-21 (Blocco D — v. CLAUDE.md): nuovo step "profiloRelazionale"
// (26 item, Ainima_Test_Profilo_Relazionale_v1.md) — sostituisce il
// confronto a embedding tra i campi liberi nel calcolo di matching,
// raggruppato con gli altri test Likert deterministici (bigfive →
// attaccamento → eq → profiloRelazionale), prima di "narrative".
const STEP_KEYS = [
  "email", // unico punto d'ingresso — crea l'account (sola email) se nuovo
  "otpVerify", // verifica OTP — qui nasce la sessione (userId)
  "basicInfo", // nome/cognome/data di nascita/genere/telefono, via PUT
  "sensitiveConsent", // consenso art. 9 GDPR
  "orientation", // dato particolare, via PUT
  "payment",
  "civilStatus",
  "profile",
  "photos",
  "preferences",
  "bigfive",
  "attaccamento",
  "eq",
  "profiloRelazionale",
  "narrative",
  "interestTags",
  "summary",
] as const;

const STEP_BASIC_INFO_INDEX = 2; // primo step sensato per chi ha già una sessione (v. sopra)

export default function OnboardingPage() {
  const t = useTranslations("onboarding.steps");
  const router = useRouter();
  const [stepIndex, setStepIndex] = useState(0);
  const [state, setState] = useState<WizardState>(initialWizardState);

  useEffect(() => {
    // Legge localStorage (sistema esterno, non disponibile in SSR) — deve
    // restare in un effect per evitare mismatch di idratazione, anche se
    // il render iniziale mostrerà per un istante lo step email.
    const existingId = getUserId();
    if (!existingId) return;

    authApi
      .getOnboardingStatus(existingId)
      .then((status) => {
        // "Attivo" (i 6 campi del gate RF-09) non implica che narrativa/liste
        // siano completi — non fanno parte del gate per scelta di prodotto
        // (v. CLAUDE.md). Reindirizzare qui SOLO in base a stato_account
        // mandava in dashboard un account già attivo ma con questi due step
        // ancora vuoti, saltandoli per sempre al primo reload. Ora si guarda
        // anche primo_passo_incompleto: se punta ancora a uno step reale
        // (< STEP_SUMMARY), lo si mostra comunque prima del redirect.
        const STEP_SUMMARY_INDEX = STEP_KEYS.length - 1;
        const nienteDaCompletare = status.primo_passo_incompleto >= STEP_SUMMARY_INDEX;
        if (status.stato_account === "Attivo" && nienteDaCompletare) {
          router.replace("/dashboard");
          return;
        }
        setState((s) => ({ ...s, userId: existingId }));
        setStepIndex(Math.max(status.primo_passo_incompleto, STEP_BASIC_INFO_INDEX));
      })
      .catch(() => {
        // user_id salvato non più valido (es. DB di test ripulito) —
        // meglio ripartire da zero che restare bloccati su uno stato invalido.
        clearUserId();
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function update<K extends keyof WizardState>(key: K, value: WizardState[K]) {
    setState((s) => ({ ...s, [key]: value }));
  }

  function next() {
    setStepIndex((i) => Math.min(i + 1, STEP_KEYS.length - 1));
  }

  function back() {
    setStepIndex((i) => Math.max(i - 1, 0));
  }

  const steps = STEP_KEYS.map((key) => t(key));

  const commonProps = { state, update, onNext: next, onBack: back };

  return (
    <main className="flex flex-1 justify-center">
      <LocaleSwitcher className="fixed right-6 top-6" />
      <PageShell>
        <ProgressSteps steps={steps} currentIndex={stepIndex} />
        <div className="mt-8">
          {stepIndex === 0 && <StepEmail {...commonProps} />}
          {stepIndex === 1 && <StepOtpVerify {...commonProps} />}
          {stepIndex === 2 && <StepBasicInfo {...commonProps} />}
          {stepIndex === 3 && <StepSensitiveConsent {...commonProps} />}
          {stepIndex === 4 && <StepOrientation {...commonProps} />}
          {stepIndex === 5 && <StepPayment {...commonProps} />}
          {stepIndex === 6 && <StepCivilStatus {...commonProps} />}
          {stepIndex === 7 && <StepProfile {...commonProps} />}
          {stepIndex === 8 && <StepPhotos {...commonProps} />}
          {stepIndex === 9 && <StepPreferences {...commonProps} />}
          {stepIndex === 10 && <StepBigFive {...commonProps} />}
          {stepIndex === 11 && <StepAttaccamento {...commonProps} />}
          {stepIndex === 12 && <StepEq {...commonProps} />}
          {stepIndex === 13 && <StepProfiloRelazionale {...commonProps} />}
          {stepIndex === 14 && <StepNarrative {...commonProps} />}
          {stepIndex === 15 && <StepInterestTags {...commonProps} />}
          {stepIndex === 16 && <StepSummary {...commonProps} />}
        </div>
      </PageShell>
    </main>
  );
}
