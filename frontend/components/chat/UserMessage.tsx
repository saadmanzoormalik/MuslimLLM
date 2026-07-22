"use client";

import { Copy, Edit3, User } from "lucide-react";
import { Button } from "@/components/ui";

type Props = {
  content: string;
  onCopy: () => void;
  onEdit: () => void;
};

export function UserMessage({ content, onCopy, onEdit }: Props) {
  if (!content.trim()) return null;

  return (
    <article className="mb-8 flex justify-end gap-3 sm:gap-4" aria-label="You said" data-message-role="user">
      <div className="max-w-[88%] sm:max-w-[78%]">
        <div className="rounded-2xl bg-primary px-4 py-3 text-primary-foreground shadow-lg">
          <p className="whitespace-pre-wrap leading-7">{content}</p>
        </div>
        <div className="mt-2 flex items-center justify-end gap-1">
          <Button className="h-8 px-2 opacity-70 hover:opacity-100" title="Copy prompt" onClick={onCopy}><Copy size={13} /></Button>
          <Button className="h-8 px-2 opacity-70 hover:opacity-100" title="Edit prompt" onClick={onEdit}><Edit3 size={13} /></Button>
        </div>
      </div>
      <div className="mt-1 hidden h-9 w-9 shrink-0 place-items-center rounded-xl border bg-card shadow-sm sm:grid" aria-hidden="true">
        <User size={17} />
      </div>
    </article>
  );
}
