export function OnboardingProgress({ step, total = 3 }: { step: number; total?: number }) {
  return (
    <div className="flex items-center justify-center gap-2" aria-label={`Step ${step + 1} of ${total}`}>
      {Array.from({ length: total }).map((_, index) => (
        <span key={index} className={`h-1.5 rounded-full transition-all ${index === step ? "w-7 bg-primary" : index < step ? "w-2.5 bg-primary/45" : "w-2.5 bg-border"}`} />
      ))}
    </div>
  );
}
