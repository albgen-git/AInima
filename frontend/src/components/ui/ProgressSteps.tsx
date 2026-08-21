import { cn } from "@/lib/cn";

interface ProgressStepsProps {
  steps: string[];
  currentIndex: number;
}

export function ProgressSteps({ steps, currentIndex }: ProgressStepsProps) {
  return (
    <div className="w-full">
      <div className="flex items-center gap-1.5">
        {steps.map((step, i) => (
          <div
            key={step}
            className={cn(
              "h-1.5 flex-1 rounded-full transition-colors",
              i <= currentIndex ? "bg-gold" : "bg-border"
            )}
          />
        ))}
      </div>
      <p className="mt-2 text-xs font-medium uppercase tracking-wide text-slate">
        {steps[currentIndex]} · {currentIndex + 1}/{steps.length}
      </p>
    </div>
  );
}
