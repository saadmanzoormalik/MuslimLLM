"use client";

import { ProviderCapability } from "@/lib/context-sync/types";
import { ProviderCard } from "./provider-card";

export function ProviderSelection({ providers, onConnect }: { providers: ProviderCapability[]; onConnect: (provider: ProviderCapability) => void }) {
  return (
    <section aria-label="Available history connections" className="mx-auto w-full max-w-5xl">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {providers.map((provider) => (
          <ProviderCard key={provider.provider_id} provider={provider} onConnect={onConnect} />
        ))}
      </div>
    </section>
  );
}
