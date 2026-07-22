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
    <article className="mb-7 flex justify-end gap-3 sm:mb-8 sm:gap-4" aria-label="You said" data-message-role="user">
      <div className="max-w-[90%] sm:max-w-[78%]">
        <div className="rounded-[20px] bg-primary px-4 py-2.5 text-primary-foreground shadow-sm sm:rounded-2xl sm:py-3 sm:shadow-lg">
          <p className="whitespace-pre-wrap text-[15px] leading-6 sm:text-base sm:leading-7">{content}</p>
        </div>
        <div className="mt-1.5 flex items-center justify-end gap-1 sm:mt-2">
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
