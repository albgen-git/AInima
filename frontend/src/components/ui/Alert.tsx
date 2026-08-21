import { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Tone = "error" | "success" | "info";

// Niente oro come colore di testo (guida §7) — i toni informativi usano
// blu notte, non oro, anche se "info" non ha un colore dedicato in guida.
const toneClasses: Record<Tone, string> = {
  error: "bg-terracotta/10 text-terracotta border-terracotta/25",
  success: "bg-sage/10 text-sage border-sage/25",
  info: "bg-border text-navy border-border-dark/10",
};

interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  tone?: Tone;
}

export function Alert({ tone = "info", className, ...props }: AlertProps) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cn(
        "rounded-sm border px-4 py-3 text-sm",
        toneClasses[tone],
        className
      )}
      {...props}
    />
  );
}
