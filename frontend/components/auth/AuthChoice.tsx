import { Apple, Mail, ShieldCheck, UserRound } from "lucide-react";

const choices = [
  { id: "apple", label: "Continue with Apple", icon: Apple },
  { id: "google", label: "Continue with Google", icon: ShieldCheck },
  { id: "email", label: "Continue with email", icon: Mail },
  { id: "guest", label: "Continue without an account", icon: UserRound }
];

type ProviderAvailability = Record<string, { enabled: boolean; configured: boolean }>;

export function AuthChoice({ busy, onChoose, providers }: { busy?: string; onChoose: (choice: string) => void; providers: ProviderAvailability | null }) {
  const availableChoices = providers
    ? choices.filter(({ id }) => providers[id]?.enabled && providers[id]?.configured)
    : [];

  return <div className="grid gap-2.5">{availableChoices.map(({ id, label, icon: Icon }) => (
    <button key={id} className={`flex h-12 w-full items-center justify-center gap-3 rounded-lg border px-4 text-sm font-semibold transition focus:outline-none focus:ring-2 focus:ring-primary ${id === "guest" ? "mt-1 bg-transparent text-muted-foreground hover:bg-muted/50 hover:text-foreground" : "bg-card shadow-sm hover:border-primary/40 hover:bg-muted/30"}`} disabled={Boolean(busy)} onClick={() => onChoose(id)}>
      <Icon size={18} />{busy === id ? "Opening..." : label}
    </button>
  ))}{!providers ? <div className="h-12 animate-pulse rounded-lg border bg-muted/40" aria-label="Loading sign-in options" /> : null}</div>;
}
