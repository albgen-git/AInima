import { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function PageShell({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("mx-auto w-full max-w-[720px] px-6 py-12", className)}
      {...props}
    />
  );
}
