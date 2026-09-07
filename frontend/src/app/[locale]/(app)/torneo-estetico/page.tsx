"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, Badge, Button, Card, PageShell, Spinner } from "@/components/ui";
import { photoUrl, torneoEsteticoApi } from "@/lib/api";
import type { PartecipanteTorneo } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import { getUserId } from "@/lib/session";

/**
 * Torneo estetico (v. CLAUDE.md 2026-09-06/07) — spareggio secondario
 * indipendente dal punteggio caratteriale principale, mai presentato
 * all'utente come un test sull'aspetto fisico altrui in astratto: solo
 * come un modo per affinare lo stile visivo generale che preferisce, usato
 * SOLO quando due o più proposte sono già quasi equivalenti per
 * compatibilità (v. testo in messages/*.json, chiave torneoEstetico.intro).
 *
 * Bracket a 8 partecipanti / 7 confronti, nessun bye (8 = potenza di 2):
 * Turno 1 — 4 confronti (posizioni accoppiate a due a due, ordine casuale
 * ad ogni sessione, v. backend) → 4 vincitori.
 * Turno 2 — 2 confronti tra i vincitori del turno 1 → 2 vincitori.
 * Turno 3 — confronto finale → 1 vincitore, il backend calcola ed espone
 * le 10 foto di preferenza risultanti.
 *
 * Un solo confronto per schermata, avanzamento automatico al successivo
 * non appena il backend conferma la scrittura del confronto corrente.
 */

// Vincitore intermedio: basta cluster_id + foto_url per i turni successivi,
// la "posizione" A-H ha significato solo nel bracket originale del turno 1.
interface Vincitore {
  cluster_id: string;
  foto_url: string;
}

type Fase = "caricamento" | "riepilogo" | "intro" | "torneo" | "risultato";

export default function TorneoEsteticoPage() {
  const t = useTranslations("torneoEstetico");
  const tCommon = useTranslations("common");
  const userId = getUserId();

  const [fase, setFase] = useState<Fase>("caricamento");
  const [preferenzaEsistente, setPreferenzaEsistente] = useState<{
    dataCompletamento: string;
    fotoUrls: string[];
  } | null>(null);

  const [sessioneId, setSessioneId] = useState<string | null>(null);
  const [turno, setTurno] = useState(1);
  const [rondaCorrente, setRondaCorrente] = useState<Vincitore[]>([]);
  const [coppiaIndice, setCoppiaIndice] = useState(0);
  const [vincitoriRonda, setVincitoriRonda] = useState<Vincitore[]>([]);
  const [fotoRisultato, setFotoRisultato] = useState<string[]>([]);

  const statoAction = useAsyncAction(torneoEsteticoApi.getPreferenza);
  const iniziaAction = useAsyncAction(torneoEsteticoApi.inizia);
  const confrontoAction = useAsyncAction(torneoEsteticoApi.registraConfronto);

  useEffect(() => {
    if (!userId) return;
    statoAction.run(userId).then((res) => {
      if (!res) return;
      if (res.completato && res.foto_preferenza_urls) {
        setPreferenzaEsistente({
          dataCompletamento: res.data_completamento ?? "",
          fotoUrls: res.foto_preferenza_urls,
        });
        setFase("riepilogo");
      } else {
        setFase("intro");
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function avviaTorneo() {
    if (!userId) return;
    const res = await iniziaAction.run(userId);
    if (!res) return;
    setSessioneId(res.sessione_id);
    setTurno(1);
    setRondaCorrente(
      res.partecipanti.map((p: PartecipanteTorneo) => ({ cluster_id: p.cluster_id, foto_url: p.foto_url }))
    );
    setCoppiaIndice(0);
    setVincitoriRonda([]);
    setFase("torneo");
  }

  async function scegli(vincitore: Vincitore) {
    if (!userId || !sessioneId) return;
    const a = rondaCorrente[coppiaIndice * 2];
    const b = rondaCorrente[coppiaIndice * 2 + 1];

    const res = await confrontoAction.run(userId, {
      sessione_id: sessioneId,
      turno,
      cluster_id_a: a.cluster_id,
      cluster_id_b: b.cluster_id,
      cluster_id_vincitore: vincitore.cluster_id,
    });
    if (!res) return;

    if (res.completato && res.foto_preferenza_urls) {
      setFotoRisultato(res.foto_preferenza_urls);
      setFase("risultato");
      return;
    }

    const nuoviVincitori = [...vincitoriRonda, vincitore];
    const coppieTotali = rondaCorrente.length / 2;
    if (coppiaIndice + 1 < coppieTotali) {
      setVincitoriRonda(nuoviVincitori);
      setCoppiaIndice((i) => i + 1);
    } else {
      setRondaCorrente(nuoviVincitori);
      setVincitoriRonda([]);
      setCoppiaIndice(0);
      setTurno((t) => t + 1);
    }
  }

  if (fase === "caricamento") {
    return (
      <PageShell>
        <Spinner />
      </PageShell>
    );
  }

  if (statoAction.error) {
    return (
      <PageShell>
        <Alert tone="error">{statoAction.error}</Alert>
      </PageShell>
    );
  }

  if (fase === "riepilogo" && preferenzaEsistente) {
    return (
      <PageShell>
        <h1 className="font-display text-3xl text-navy">{t("title")}</h1>
        <p className="mt-2 text-sm text-slate">{t("riepilogoSubtitle")}</p>
        <Card className="mt-6">
          <Badge tone="sage">{t("completatoBadge")}</Badge>
          <div className="mt-4 grid grid-cols-5 gap-2">
            {preferenzaEsistente.fotoUrls.map((url) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={url}
                src={photoUrl(url)}
                alt=""
                className="aspect-square w-full rounded-sm object-cover"
              />
            ))}
          </div>
          <Button className="mt-6" variant="secondary" onClick={() => setFase("intro")}>
            {t("rifaiCta")}
          </Button>
        </Card>
      </PageShell>
    );
  }

  if (fase === "intro") {
    return (
      <PageShell>
        <h1 className="font-display text-3xl text-navy">{t("title")}</h1>
        <Card className="mt-6 flex flex-col gap-4">
          <p className="text-sm text-slate">{t("intro")}</p>
          <p className="text-sm text-slate">{t("introDettaglio")}</p>
          {(iniziaAction.error || statoAction.error) && (
            <Alert tone="error">{iniziaAction.error ?? statoAction.error}</Alert>
          )}
          <Button size="lg" onClick={avviaTorneo} disabled={iniziaAction.loading} className="self-start">
            {iniziaAction.loading ? tCommon("loading") : t("iniziaCta")}
          </Button>
        </Card>
      </PageShell>
    );
  }

  if (fase === "torneo") {
    const a = rondaCorrente[coppiaIndice * 2];
    const b = rondaCorrente[coppiaIndice * 2 + 1];
    const coppieTotali = rondaCorrente.length / 2;
    const confrontoGlobale =
      // Turno 1: 4 confronti, turno 2: 2, turno 3: 1 — indice progressivo su 7 totali per la progress bar.
      (turno === 1 ? 0 : turno === 2 ? 4 : 6) + coppiaIndice + 1;

    return (
      <PageShell>
        <h1 className="font-display text-3xl text-navy">{t("title")}</h1>
        <p className="mt-2 text-xs text-slate">{t("progress", { current: confrontoGlobale, total: 7 })}</p>

        <div className="mt-6 grid grid-cols-2 gap-4">
          {[a, b].map((partecipante) => (
            <button
              key={partecipante.cluster_id}
              type="button"
              disabled={confrontoAction.loading}
              onClick={() => scegli(partecipante)}
              className="group overflow-hidden rounded-md border border-border bg-ivory-light shadow-card transition-colors hover:border-gold disabled:opacity-60"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photoUrl(partecipante.foto_url)}
                alt=""
                className="aspect-[3/4] w-full object-cover"
              />
              <span className="block px-3 py-2 text-center text-sm font-medium text-navy group-hover:text-gold-dark">
                {t("scegliCta")}
              </span>
            </button>
          ))}
        </div>

        {confrontoAction.error && <Alert tone="error" className="mt-4">{confrontoAction.error}</Alert>}
      </PageShell>
    );
  }

  // fase === "risultato"
  return (
    <PageShell>
      <h1 className="font-display text-3xl text-navy">{t("title")}</h1>
      <Card className="mt-6">
        <Badge tone="sage">{t("completatoBadge")}</Badge>
        <p className="mt-3 text-sm text-slate">{t("risultatoBody")}</p>
        <div className="mt-4 grid grid-cols-5 gap-2">
          {fotoRisultato.map((url) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img key={url} src={photoUrl(url)} alt="" className="aspect-square w-full rounded-sm object-cover" />
          ))}
        </div>
      </Card>
    </PageShell>
  );
}
