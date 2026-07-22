"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Search } from "lucide-react";
import { Citation, apiGet } from "@/lib/api";
import { Badge, Button, Input, Panel, PrimaryButton } from "@/components/ui";

export default function SourcesPage() {
  const [query, setQuery] = useState("What does the corpus say about Muslim trade networks?");
  const [sources, setSources] = useState<Citation[]>([]);
  const [loading, setLoading] = useState(false);

  async function search() {
    setLoading(true);
    try {
      const data = await apiGet<{ sources: Citation[] }>(`/sources/search?q=${encodeURIComponent(query)}&top_k=8`);
      setSources(data.sources);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-dvh px-4 py-6">
      <div className="mx-auto max-w-5xl">
        <Link className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground" href="/"><ArrowLeft size={16} /> Back to chat</Link>
        <h1 className="text-2xl font-semibold">Sources</h1>
        <p className="mt-2 text-muted-foreground">Search the Islamic-civilizational memory layer and inspect citation metadata.</p>
        <div className="mt-5 flex gap-2">
          <Input className="flex-1" value={query} onChange={(e) => setQuery(e.target.value)} />
          <PrimaryButton onClick={search} disabled={loading}><Search size={16} /> Search</PrimaryButton>
        </div>
        <div className="mt-6 grid gap-3">
          {sources.map((source, index) => (
            <Panel key={`${source.title}-${index}`} className="p-4">
              <div className="mb-2 flex flex-wrap gap-2">
                <Badge>[{index + 1}] {source.source_type}</Badge>
                <Badge>{source.reliability_level}</Badge>
                {source.score ? <Badge>{source.score}</Badge> : null}
              </div>
              <h2 className="font-semibold">{source.title}</h2>
              <p className="text-sm text-muted-foreground">{source.author || "Unknown author"} · {source.reference || "No reference"}</p>
              <p className="mt-3 text-sm leading-6">{source.snippet}</p>
            </Panel>
          ))}
        </div>
      </div>
    </main>
  );
}
