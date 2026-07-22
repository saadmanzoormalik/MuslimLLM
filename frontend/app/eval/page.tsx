"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Play } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import { Input, Panel, PrimaryButton, Textarea } from "@/components/ui";

type EvalQuestion = { id: string; question: string; category: string; ideal_answer?: string; source_expectation?: string };
type EvalRun = {
  id: string;
  overall_score: number;
  citation_accuracy: number;
  hallucination_risk: number;
  islamic_nuance: number;
  madhab_awareness: number;
  historical_accuracy: number;
  general_usefulness: number;
  refusal_correctness: number;
  notes: string;
};

export default function EvalPage() {
  const [questions, setQuestions] = useState<EvalQuestion[]>([]);
  const [runs, setRuns] = useState<EvalRun[]>([]);

  function load() {
    apiGet<EvalQuestion[]>("/eval/questions").then(setQuestions).catch(() => setQuestions([]));
    apiGet<EvalRun[]>("/eval/runs").then(setRuns).catch(() => setRuns([]));
  }

  useEffect(load, []);

  async function createQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await apiPost("/eval/questions", {
      question: form.get("question"),
      ideal_answer: form.get("ideal_answer"),
      source_expectation: form.get("source_expectation"),
      category: form.get("category") || "General"
    });
    event.currentTarget.reset();
    load();
  }

  async function runEval(id: string) {
    await apiPost("/eval/run", { eval_question_id: id });
    load();
  }

  return (
    <main className="min-h-dvh px-4 py-6">
      <div className="mx-auto max-w-6xl">
        <Link className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground" href="/"><ArrowLeft size={16} /> Back to chat</Link>
        <h1 className="text-2xl font-semibold">Evaluation</h1>
        <p className="mt-2 text-muted-foreground">Track citation accuracy, hallucination risk, Islamic nuance, madhab awareness, and usefulness.</p>

        <Panel className="mt-6 p-4">
          <form className="grid gap-3" onSubmit={createQuestion}>
            <Input name="category" placeholder="Category" defaultValue="Islamic nuance" />
            <Textarea name="question" placeholder="Evaluation question" required />
            <Textarea name="ideal_answer" placeholder="Ideal answer or rubric notes" />
            <Textarea name="source_expectation" placeholder="Expected source type, citation, or evidence standard" />
            <PrimaryButton type="submit">Add eval question</PrimaryButton>
          </form>
        </Panel>

        <section className="mt-6 grid gap-3">
          {questions.map((question) => (
            <Panel key={question.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">{question.category}</p>
                  <h2 className="mt-1 font-medium">{question.question}</h2>
                  {question.source_expectation ? <p className="mt-2 text-sm text-muted-foreground">{question.source_expectation}</p> : null}
                </div>
                <PrimaryButton onClick={() => runEval(question.id)}><Play size={16} /> Run</PrimaryButton>
              </div>
            </Panel>
          ))}
        </section>

        <h2 className="mt-8 text-lg font-semibold">Recent runs</h2>
        <div className="mt-3 overflow-x-auto rounded-lg border">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="bg-muted">
              <tr>
                {["Overall","Citation","Hallucination risk","Islamic nuance","Madhab","History","Useful","Refusal","Notes"].map((h) => <th key={h} className="p-3">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} className="border-t">
                  <td className="p-3">{run.overall_score}</td>
                  <td className="p-3">{run.citation_accuracy}</td>
                  <td className="p-3">{run.hallucination_risk}</td>
                  <td className="p-3">{run.islamic_nuance}</td>
                  <td className="p-3">{run.madhab_awareness}</td>
                  <td className="p-3">{run.historical_accuracy}</td>
                  <td className="p-3">{run.general_usefulness}</td>
                  <td className="p-3">{run.refusal_correctness}</td>
                  <td className="p-3">{run.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
