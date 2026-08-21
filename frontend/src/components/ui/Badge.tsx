import { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Tone = "navy" | "gold" | "sage" | "terracotta" | "neutral";

// L'oro è ammesso solo su elementi pieni (mai come colore di testo su
// sfondo chiaro, guida §7) — qui reso come chip pieno, non testo su tinta.
const toneClasses: Record<Tone, string> = {
  navy: "bg-navy text-ivory-light",
  gold: "bg-gold text-ivory-light",
  sage: "bg-sage/12 text-sage",
  terracotta: "bg-terracotta/12 text-terracotta",
  neutral: "bg-border text-slate",
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

export function Badge({ tone = "neutral", className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm px-3 py-1 text-xs font-semibold uppercase tracking-wide",
        toneClasses[tone],
        className
      )}
      {...props}
    />
  );
}
