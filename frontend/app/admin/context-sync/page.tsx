"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ShieldCheck } from "lucide-react";
import { apiGet } from "@/lib/api";
import { ProviderCapability } from "@/lib/context-sync/types";
import { Badge, Panel } from "@/components/ui";

export default function AdminContextSyncPage() {
  const [providers, setProviders] = useState<ProviderCapability[]>([]);
  useEffect(() => {
    apiGet<ProviderCapability[]>("/context-sync/providers").then(setProviders).catch(() => setProviders([]));
  }, []);
  return (
    <main className="min-h-dvh px-4 py-6">
      <div className="mx-auto max-w-5xl">
        <Link className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground" href="/"><ArrowLeft size={16} /> Back</Link>
        <Badge className="mb-3"><ShieldCheck size={13} /> Integration verification</Badge>
        <h1 className="text-3xl font-semibold">Context Sync Admin</h1>
        <div className="mt-6 overflow-hidden rounded-xl border">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="p-3">Provider</th>
                <th className="p-3">Method</th>
                <th className="p-3">Conversations</th>
                <th className="p-3">Projects</th>
                <th className="p-3">Files</th>
                <th className="p-3">Direct tested</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((provider) => (
                <tr key={provider.provider_id} className="border-t">
                  <td className="p-3 font-medium">{provider.display_name}</td>
                  <td className="p-3">{provider.compact_status}</td>
                  <td className="p-3">{provider.capabilities?.conversations || "unknown"}</td>
                  <td className="p-3">{provider.capabilities?.projects || "unknown"}</td>
                  <td className="p-3">{provider.capabilities?.files || "unknown"}</td>
                  <td className="p-3">No</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Panel className="mt-5 p-4 text-sm text-muted-foreground">
          Direct sync cannot be promoted unless official connector contract tests prove access to user-owned historical data.
        </Panel>
      </div>
    </main>
  );
}
