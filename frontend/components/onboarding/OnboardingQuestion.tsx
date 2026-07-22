import { Check, ChevronRight } from "lucide-react";

export function OnboardingQuestion({ title, options, selected, busy, onSelect }: {
  title: string;
  options: Array<{ value: string; label: string; note?: string }>;
  selected?: string;
  busy?: boolean;
  onSelect: (value: string) => void;
}) {
  return (
    <section aria-labelledby="onboarding-question">
      <h1 id="onboarding-question" className="display-type mx-auto max-w-2xl text-center text-4xl font-semibold leading-tight text-foreground sm:text-5xl">{title}</h1>
      <div className="mx-auto mt-10 grid max-w-xl gap-2.5" role="radiogroup" aria-label={title}>
        {options.map((option) => (
          <button
            key={option.value}
            className={`group flex min-h-16 w-full items-center justify-between gap-4 rounded-lg border bg-card px-5 py-4 text-left shadow-sm transition hover:border-primary/45 hover:bg-muted/30 focus:outline-none focus:ring-2 focus:ring-primary ${selected === option.value ? "border-primary bg-primary/[0.04]" : ""}`}
            disabled={busy}
            onClick={() => onSelect(option.value)}
            role="radio"
            aria-checked={selected === option.value}
          >
            <span><span className="block text-[15px] font-semibold">{option.label}</span>{option.note ? <span className="mt-0.5 block text-xs text-muted-foreground">{option.note}</span> : null}</span>
            {selected === option.value ? <Check className="shrink-0 text-primary" size={18} /> : <ChevronRight className="shrink-0 text-muted-foreground transition group-hover:translate-x-0.5 group-hover:text-primary" size={18} />}
          </button>
        ))}
      </div>
    </section>
  );
}
