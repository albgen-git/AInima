"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, Button, Card, TextField } from "@/components/ui";
import { cn } from "@/lib/cn";
import { psychometricApi } from "@/lib/api";
import { useAsyncAction } from "@/lib/useAsyncAction";
import type { StepProps } from "@/lib/wizard/types";

interface ChatTurn {
  ruolo: "utente" | "assistente";
  testo: string;
}

export function StepInterview({ state, update, onNext, onBack }: StepProps) {
  const t = useTranslations("onboarding.interview");
  const tCommon = useTranslations("common");
  const [messages, setMessages] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [completed, setCompleted] = useState(state.chatCompletata);
  const startedRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { run, loading, error } = useAsyncAction(psychometricApi.sendChatMessage);

  useEffect(() => {
    if (startedRef.current || completed || !state.userId) return;
    startedRef.current = true;
    run(state.userId, {}).then((result) => {
      if (result) {
        setMessages([{ ruolo: "assistente", testo: result.testo }]);
        if (result.conversazione_completata) setCompleted(true);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || !state.userId) return;
    const testo = input.trim();
    setMessages((m) => [...m, { ruolo: "utente", testo }]);
    setInput("");

    const result = await run(state.userId, { testo });
    if (result) {
      setMessages((m) => [...m, { ruolo: "assistente", testo: result.testo }]);
      if (result.conversazione_completata) {
        setCompleted(true);
        update("chatCompletata", true);
      }
    }
  }

  return (
    <Card>
      <h1 className="font-display text-2xl text-navy">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate">{t("subtitle")}</p>

      <div className="mt-6 flex max-h-96 flex-col gap-3 overflow-y-auto rounded-xl bg-border p-4">
        {messages.length === 0 && loading && (
          <p className="text-sm text-slate">{t("starting")}</p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm",
              msg.ruolo === "assistente"
                ? "self-start bg-ivory-light text-navy"
                : "self-end bg-navy text-ivory-light"
            )}
          >
            {msg.testo}
          </div>
        ))}
        {loading && messages.length > 0 && (
          <p className="self-start text-xs text-slate">{t("thinking")}</p>
        )}
        <div ref={bottomRef} />
      </div>

      {error && <Alert tone="error" className="mt-4">{error}</Alert>}

      {completed ? (
        <div className="mt-6 flex flex-col gap-4">
          <Alert tone="success">{t("completed")}</Alert>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={onBack}>
              {tCommon("back")}
            </Button>
            <Button onClick={onNext}>{t("continueAfter")}</Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSend} className="mt-4 flex gap-3">
          <div className="flex-1">
            <TextField
              placeholder={t("inputPlaceholder")}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading || messages.length === 0}
            />
          </div>
          <Button type="submit" disabled={loading || !input.trim()}>
            {t("send")}
          </Button>
        </form>
      )}
    </Card>
  );
}
