"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ShieldCheck } from "lucide-react";
import { apiGet } from "@/lib/api";

export default function AuthDiagnosticsPage() {
  const [data, setData] = useState<Record<string, any> | null>(null);
  useEffect(() => { apiGet<Record<string, any>>("/auth/diagnostics").then(setData).catch(() => setData({ unavailable: true })); }, []);
  return <main className="mx-auto min-h-dvh max-w-2xl px-5 py-10"><Link className="inline-flex items-center gap-2 text-sm text-muted-foreground" href="/settings"><ArrowLeft size={15} /> Settings</Link><h1 className="display-type mt-8 flex items-center gap-3 text-3xl font-semibold"><ShieldCheck size={25} className="text-primary" /> Auth diagnostics</h1><p className="mt-2 text-sm text-muted-foreground">Configuration status only. Secrets and tokens are never shown.</p><div className="mt-7 grid gap-2">{data ? Object.entries(data).map(([key, value]) => <div key={key} className="rounded-lg border bg-card px-4 py-3"><div className="text-xs font-semibold uppercase text-muted-foreground">{key.replaceAll("_", " ")}</div><pre className="mt-2 whitespace-pre-wrap bg-transparent p-0 text-xs text-foreground">{typeof value === "string" ? value : JSON.stringify(value, null, 2)}</pre></div>) : <p className="text-sm text-muted-foreground">Checking...</p>}</div></main>;
}
