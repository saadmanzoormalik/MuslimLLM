"use client";

import Link from "next/link";
import { ArrowRight, Check } from "lucide-react";

export function SyncComplete({ href }: { href: string }) {
  return (
    <section className="mx-auto flex min-h-[52vh] w-full max-w-xl flex-col items-center justify-center text-center" aria-live="polite">
      <span className="grid h-20 w-20 place-items-center rounded-full bg-primary text-primary-foreground shadow-[0_20px_55px_rgba(18,70,52,0.18)]">
        <Check size={34} strokeWidth={2.2} />
      </span>
      <h1 className="display-type mt-7 text-4xl font-semibold">Your context is ready</h1>
      <p className="mt-3 max-w-md text-sm leading-6 text-muted-foreground">Your available conversations and projects have been transferred. You can continue where you left off.</p>
      <Link className="mt-7 inline-flex h-11 items-center gap-2 rounded-md bg-primary px-5 text-sm font-semibold text-primary-foreground transition hover:opacity-90" href={href}>
        Open Muslim LLM <ArrowRight size={16} />
      </Link>
    </section>
  );
}
