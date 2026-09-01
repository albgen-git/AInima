"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { Alert, Badge, Button, Card, CompatibilityBar, PageShell, Spinner } from "@/components/ui";
import {
  contactsApi,
  matchingApi,
  paymentsApi,
  photoUrl,
  type ProposalAnalysisOut,
  type ProposalOut,
} from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import { getUserId } from "@/lib/session";

function daysRemaining(dataScadenza: string | null): number | null {
  if (!dataScadenza) return null;
  const diffMs = new Date(dataScadenza).getTime() - Date.now();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

export default function ProposalPage() {
  const t = useTranslations("proposal");
  const tCommon = useTranslations("common");
  const userId = getUserId();

  const [proposal, setProposal] = useState<ProposalOut | null | undefined>(undefined);
  const [analysis, setAnalysis] = useState<ProposalAnalysisOut | null>(null);
  const [vcardReady, setVcardReady] = useState(false);
  const [payResult, setPayResult] = useState<{ contatti_sbloccati: boolean; fee_eur: string } | null>(null);

  const proposalAction = useAsyncAction(matchingApi.getProposal);
  const decisionAction = useAsyncAction(matchingApi.decideMatch);
  const payAction = useAsyncAction(paymentsApi.payMatch);

  async function loadProposal() {
    if (!userId) return;
    const result = await proposalAction.run(userId);
    setProposal(result ?? null);

    if (result?.stato === "Confermato") {
      const rubrica = await contactsApi.getRubrica(userId);
      setVcardReady(rubrica.some((r) => r.match_id === result.match_id));
    }

    if (result) {
      matchingApi.getProposalAnalysis(userId).then(setAnalysis).catch(() => {});
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadProposal();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleDecision(accetta: boolean) {
    if (!userId || !proposal) return;
    const result = await decisionAction.run(userId, proposal.match_id, { accetta });
    if (result) await loadProposal();
  }

  async function handlePay() {
    if (!userId || !proposal) return;
    const result = await payAction.run(userId, proposal.match_id);
    if (result) {
      setPayResult({ contatti_sbloccati: result.contatti_sbloccati, fee_eur: result.fee_eur });
      if (result.contatti_sbloccati) setVcardReady(true);
    }
  }

  if (proposal === undefined) {
    return (
      <PageShell>
        <Spinner />
      </PageShell>
    );
  }

  if (proposal === null) {
    return (
      <PageShell className="text-center">
        <h1 className="font-display text-2xl text-navy">{t("noProposalTitle")}</h1>
        <p className="mt-3 text-sm text-slate">{t("noProposalSubtitle")}</p>
      </PageShell>
    );
  }

  const remaining = daysRemaining(proposal.data_scadenza_risposta);
  const isFinal = proposal.stato === "Rifiutato" || proposal.stato === "Scaduto";
  const isConfirmed = proposal.stato === "Confermato";
  // 'Accettato_A'/'Accettato_B' da soli sono ambigui: solo il backend sa
  // se questo utente è il lato che ha già risposto o quello in attesa
  // (proposta anonima, v. ProposalOut.in_attesa_di_te).
  const isWaitingMe = !isFinal && !isConfirmed && proposal.in_attesa_di_te;
  const isWaitingOther = !isFinal && !isConfirmed && !proposal.in_attesa_di_te;

  return (
    <PageShell>
      <h1 className="font-display text-3xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-xs text-slate">{t("anonymousNote")}</p>

      <Card className="mt-6">
        <div className="flex gap-5">
          {proposal.foto_profilo_url && (
            <Image
              src={photoUrl(proposal.foto_profilo_url)}
              alt=""
              width={112}
              height={112}
              className="h-28 w-28 shrink-0 rounded-2xl object-cover"
            />
          )}
          <div className="flex flex-col gap-1">
            <p className="font-display text-xl text-navy">{t("eta", { age: proposal.eta })}</p>
            {proposal.corporatura && <p className="text-sm text-slate">{proposal.corporatura}</p>}
            {proposal.titolo_studio && <p className="text-sm text-slate">{proposal.titolo_studio}</p>}
            {proposal.distanza_km != null && (
              <p className="text-sm text-slate">{t("distanza", { km: Math.round(proposal.distanza_km) })}</p>
            )}
          </div>
        </div>

        {remaining !== null && isWaitingMe && (
          <Badge tone={remaining > 0 ? "gold" : "terracotta"} className="mt-4">
            {remaining > 0
              ? t("expiresIn", { date: proposal.data_scadenza_risposta?.slice(0, 10) ?? "" })
              : t("expired")}
          </Badge>
        )}

        {decisionAction.error && <Alert tone="error" className="mt-4">{decisionAction.error}</Alert>}

        {isWaitingMe && (
          <div className="mt-5 flex gap-3">
            <Button variant="secondary" onClick={() => handleDecision(false)} disabled={decisionAction.loading}>
              {t("reject")}
            </Button>
            <Button onClick={() => handleDecision(true)} disabled={decisionAction.loading}>
              {t("accept")}
            </Button>
          </div>
        )}
        {isWaitingOther && <Alert tone="info" className="mt-5">{t("youAccepted")}</Alert>}
        {isFinal && <Alert tone="info" className="mt-5">{t("rejected")}</Alert>}
        {isConfirmed && <Alert tone="success" className="mt-5">{t("confirmed")}</Alert>}
      </Card>

      <Card className="mt-6">
        <h2 className="font-display text-xl text-navy">{t("analysisTitle")}</h2>
        <div className="mt-3">
          <CompatibilityBar
            analysis={analysis}
            loadingText={t("analysisLoading")}
            notReadyText={t("analysisNotReady")}
            hintText={t("narrativeScoreHint")}
          />
        </div>
      </Card>

      {isConfirmed && (
        <Card className="mt-6">
          <h2 className="font-display text-xl text-navy">{t("payTitle")}</h2>
          <p className="mt-2 text-sm text-slate">{t("paySubtitle")}</p>

          {!vcardReady && <Alert tone="info" className="mt-4">{t("emailPrivacyNote")}</Alert>}

          {payAction.error && <Alert tone="error" className="mt-4">{payAction.error}</Alert>}

          {vcardReady ? (
            <div className="mt-4 flex flex-col gap-3">
              <Badge tone="sage">{t("contactsUnlocked")}</Badge>
              <a
                href={contactsApi.vcardUrl(userId!, proposal.match_id)}
                className="inline-flex w-fit items-center justify-center gap-2 rounded-sm bg-gold px-5 py-2.5 text-sm font-medium text-ivory-light hover:bg-gold-dark"
              >
                {t("downloadVcard")}
              </a>
            </div>
          ) : payResult ? (
            <div className="mt-4 flex flex-col gap-2">
              <Badge tone="sage">{t("paid", { fee: payResult.fee_eur })}</Badge>
              <Alert tone="info">{t("waitingOtherPayment")}</Alert>
            </div>
          ) : (
            <Button className="mt-4" onClick={handlePay} disabled={payAction.loading}>
              {payAction.loading ? tCommon("loading") : t("payButton")}
            </Button>
          )}
        </Card>
      )}
    </PageShell>
  );
}
