"use client";

import { BookOpenCheck, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";

function Callback() {
  const params = useSearchParams();
  const error = params.get("error");
  const returnTo = params.get("return_to") || "/";
  useEffect(() => { if (!error) window.location.replace(returnTo.startsWith("/") ? returnTo : "/"); }, [error, returnTo]);
  return <main className="auth-surface grid min-h-dvh place-items-center px-5"><div className="w-full max-w-sm rounded-xl border bg-card p-7 text-center shadow-xl"><div className="mx-auto grid h-11 w-11 place-items-center rounded-xl border text-primary"><BookOpenCheck size={20} /></div>{error ? <><h1 className="display-type mt-5 text-2xl font-semibold">We couldn’t complete sign-in</h1><p className="mt-2 text-sm text-muted-foreground">The authorization was cancelled or expired.</p><Link className="mt-6 inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-primary px-5 text-sm font-semibold text-primary-foreground" href="/auth"><RotateCcw size={15} /> Try again</Link></> : <><h1 className="display-type mt-5 text-2xl font-semibold">Opening Muslim LLM</h1><p className="mt-2 text-sm text-muted-foreground">Your workspace is ready.</p></>}</div></main>;
}

export default function CallbackPage() { return <Suspense><Callback /></Suspense>; }
