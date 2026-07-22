"use client";

import { Copy } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "./ui";

export function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="prose prose-sm max-w-none dark:prose-invert">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre({ children }) {
            const text = String(children);
            return (
              <div className="group relative">
                <Button
                  className="absolute right-2 top-2 h-8 px-2 opacity-80"
                  onClick={() => navigator.clipboard.writeText(text)}
                  title="Copy code"
                >
                  <Copy size={15} />
                </Button>
                <pre>{children}</pre>
              </div>
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
