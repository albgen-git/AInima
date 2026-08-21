import { ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

// Bottone primario: sfondo oro pieno, testo avorio chiaro (guida §5) — l'oro
// va sempre su bottoni pieni, mai come colore di testo su sfondo chiaro.
const variantClasses: Record<Variant, string> = {
  primary:
    "bg-gold text-ivory-light hover:bg-gold-dark disabled:bg-gold/50 shadow-card",
  secondary:
    "border border-navy text-navy bg-transparent hover:bg-border disabled:opacity-50",
  ghost: "text-navy hover:bg-border disabled:opacity-50",
  danger:
    "bg-terracotta text-ivory-light hover:opacity-90 disabled:opacity-50",
};

const sizeClasses: Record<Size, string> = {
  md: "px-5 py-2.5 text-sm",
  lg: "px-7 py-3.5 text-base",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-sm font-medium tracking-wide transition-colors cursor-pointer disabled:cursor-not-allowed",
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
