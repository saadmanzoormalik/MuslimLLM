"use client";

import { ArrowLeft, BookOpenCheck, Check, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { OnboardingProgress } from "@/components/onboarding/OnboardingProgress";
import { OnboardingQuestion } from "@/components/onboarding/OnboardingQuestion";
import { API_BASE } from "@/lib/api";

const questions = [
  {
    key: "primary_use",
    title: "What would you like help with?",
    options: [
      { value: "everyday", label: "Everyday life" }, { value: "work", label: "Work and business" },
      { value: "learning", label: "Learning and research" }, { value: "islamic", label: "Islamic knowledge" },
      { value: "mixed", label: "A mix of everything" }
    ]
  },
  {
    key: "response_preference",
    title: "How should answers feel?",
    options: [
      { value: "concise", label: "Concise", note: "Clear and brief" },
      { value: "balanced", label: "Balanced", note: "Enough context, without the noise" },
      { value: "detailed", label: "Detailed", note: "More depth and explanation" }
    ]
  },
  {
    key: "privacy_preference",
    title: "Where should your AI data be processed?",
    options: [
      { value: "local", label: "Private processing", note: "Runs on this Muslim LLM server" },
      { value: "best", label: "Best available experience", note: "Use trusted services when helpful" }
    ]
  }
] as const;

type State = { current_step: number; answers: Record<string, string>; completed: boolean };

async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit = {}) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15000);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    window.clearTimeout(timeout);
  }
}

export default function OnboardingPage() {
  const router = useRouter();
  const [state, setState] = useState<State>({ current_step: 0, answers: {}, completed: false });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [previewMode, setPreviewMode] = useState(false);
  const step = Math.max(0, Math.min(Number(state.current_step ?? 0), 2));
  const question = questions[step] ?? questions[0];

  useEffect(() => {
    const preview = new URLSearchParams(window.location.search).get("preview") === "1";
    setPreviewMode(preview);
    if (preview) return;
    fetch(`${API_BASE}/onboarding`, { credentials: "include", cache: "no-store" })
      .then((response) => response.json()).then((data) => {
        if (data.authenticated || data.completed) router.replace(data.authenticated ? "/" : "/auth");
        else setState({ current_step: Number(data.current_step ?? 0), answers: data.answers ?? {}, completed: false });
      });
  }, []);

  async function select(value: string) {
    if (busy) return;
    setBusy(true);
    setError("");
    if (previewMode) {
      setState((current) => ({
        answers: { ...current.answers, [question.key]: value },
        completed: step === 2,
        current_step: step === 2 ? 3 : step + 1
      }));
      setBusy(false);
      return;
    }
    try {
      const response = await fetchWithTimeout(`${API_BASE}/onboarding/answer`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: question.key, value, step })
      });
      if (!response.ok) {
        setError("We couldn’t save that choice. Check your connection and try again.");
        return;
      }
      const next = await response.json();
      setState((current) => ({ ...current, ...next }));
      if (step === 2) {
        const completed = await fetchWithTimeout(`${API_BASE}/onboarding/complete`, {
          method: "POST", credentials: "include"
        });
        if (completed.ok) router.push("/auth");
        else setError("Your choices are saved. Tap again to finish setup.");
      }
    } catch {
      setError("We couldn’t reach Muslim LLM. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  function back() {
    setState((current) => ({ ...current, current_step: Math.max(0, step - 1) }));
  }

  function restartPreview() {
    setState({ current_step: 0, answers: {}, completed: false });
  }

  return (
    <main className="auth-surface relative min-h-dvh overflow-hidden px-5 py-6 sm:px-8">
      <div className="relative z-10 mx-auto flex min-h-[calc(100dvh-3rem)] max-w-5xl flex-col">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2.5 text-sm font-semibold"><span className="grid h-9 w-9 place-items-center rounded-lg border bg-card text-primary shadow-sm"><BookOpenCheck size={17} /></span>Muslim LLM {previewMode ? <span className="rounded-full bg-primary/10 px-2 py-1 text-[10px] uppercase text-primary">Preview</span> : null}</div>
          <span className="text-xs text-muted-foreground">{state.completed ? "Complete" : `${step + 1} of 3`}</span>
        </header>
        <div className="mt-7"><OnboardingProgress step={state.completed ? 2 : step} /></div>
        {previewMode && state.completed ? (
          <div className="flex flex-1 items-center py-10">
            <section className="mx-auto w-full max-w-xl text-center" aria-labelledby="preview-complete-title">
              <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-primary/10 text-primary"><Check size={22} /></span>
              <h1 className="display-type mt-6 text-4xl font-semibold sm:text-5xl" id="preview-complete-title">Ready to begin.</h1>
              <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-muted-foreground">Preview complete. Your current workspace and saved preferences were not changed.</p>
              <div className="mt-8 flex flex-col justify-center gap-2 sm:flex-row">
                <Link className="inline-flex h-11 items-center justify-center rounded-md bg-primary px-5 text-sm font-semibold text-primary-foreground" href="/">Back to chat</Link>
                <button className="inline-flex h-11 items-center justify-center gap-2 rounded-md border bg-card px-5 text-sm font-semibold hover:bg-muted" onClick={restartPreview} type="button"><RotateCcw size={15} /> Restart preview</button>
              </div>
            </section>
          </div>
        ) : (
          <div className="flex flex-1 items-center py-10"><div className="w-full"><OnboardingQuestion title={question.title} options={[...question.options]} selected={state.answers[question.key]} busy={busy} onSelect={select} />{error ? <p className="mx-auto mt-4 max-w-xl rounded-md border border-red-300/60 bg-red-50 px-4 py-3 text-center text-sm text-red-800" role="alert">{error}</p> : null}</div></div>
        )}
        <footer className="flex min-h-10 items-center justify-between gap-3 text-xs text-muted-foreground">
          {!state.completed && step > 0 ? <button className="inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 hover:bg-muted hover:text-foreground" onClick={back} type="button"><ArrowLeft size={14} /> Back</button> : <span />}
          {!state.completed && step === 2 ? <span>You can change this later.</span> : previewMode ? <Link className="rounded-md px-2 py-1.5 hover:bg-muted hover:text-foreground" href="/">Exit preview</Link> : null}
        </footer>
      </div>
    </main>
  );
}
