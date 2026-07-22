import type { Metadata } from "next";
import "./globals.css";
import { AuthBoundary } from "@/components/auth/AuthBoundary";

export const metadata: Metadata = {
  title: "Muslim LLM",
  description: "General-purpose AI assistant with Islamic-civilizational grounding"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body><AuthBoundary>{children}</AuthBoundary></body>
    </html>
  );
}
