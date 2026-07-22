"use client";

import { X } from "lucide-react";
import type { Citation } from "@/lib/api";
import { Badge, Button } from "./ui";

export function SourceDrawer({ open, citations, onClose }: { open: boolean; citations: Citation[]; onClose: () => void }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40">
      <button aria-label="Close sources" className="absolute inset-0 cursor-default bg-black/25 backdrop-blur-[1px]" onClick={onClose} type="button" />
      <aside aria-labelledby="sources-title" aria-modal="true" className="absolute inset-y-0 right-0 w-full max-w-md border-l bg-card/95 shadow-2xl backdrop-blur-xl" role="dialog">
        <div className="flex items-center justify-between border-b p-5">
          <div>
            <h2 className="font-semibold" id="sources-title">Sources</h2>
            <p className="text-sm text-muted-foreground">Retrieved evidence.</p>
          </div>
          <Button aria-label="Close sources" className="h-9 w-9 p-0" onClick={onClose} title="Close sources"><X size={17} /></Button>
        </div>
        <div className="h-[calc(100dvh-79px)] overflow-y-auto p-4">
          {citations.length === 0 ? (
            <div className="rounded-lg border bg-background/70 p-4 text-sm text-muted-foreground">
              No sources retrieved.
            </div>
          ) : citations.map((source, index) => (
            <article key={`${source.title}-${index}`} className="mb-3 rounded-lg border bg-background/70 p-4 shadow-sm">
              <div className="mb-2 flex flex-wrap gap-2">
                <Badge>[{index + 1}] {source.source_type}</Badge>
                <Badge>{source.reliability_level}</Badge>
                {source.score ? <Badge>score {source.score}</Badge> : null}
              </div>
              <h3 className="font-medium">{source.title}</h3>
              <p className="text-sm text-muted-foreground">{source.author || "Unknown author"} · {source.reference || "No reference"}</p>
              <p className="mt-3 text-sm leading-6">{source.snippet}</p>
            </article>
          ))}
        </div>
      </aside>
    </div>
  );
}
