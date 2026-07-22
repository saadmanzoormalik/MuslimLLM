"use client";

import { ReactNode, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  DatabaseZap,
  Download,
  FileText,
  Gauge,
  Layers,
  Play,
  RefreshCcw,
  Scale,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  XCircle
} from "lucide-react";
import { API_BASE, apiGet, apiPost } from "@/lib/api";
import { Button, Panel, PrimaryButton } from "@/components/ui";

type EvalModel = { id: string; display_name: string; is_local: boolean };
type EvalRun = {
  id: string;
  run_name?: string;
  aggregate_score?: number;
  weighted_score?: number;
  pass_rate?: number;
  total_questions: number;
  completed_at?: string;
  eval_set_version?: string;
  confidence_level?: string;
  critical_failures_count?: number;
  fabricated_religious_source_flags_count?: number;
  science_overframing_count?: number;
  average_latency_ms?: number;
};
type RunItem = {
  id: string;
  prompt: string;
  model_answer?: string;
  score?: number;
  category?: string;
  failure_type?: string;
  critical_failure?: boolean;
  recommended_fix?: string;
  scholar_review_status?: string;
};
type DashboardSummary = {
  overall_score?: number | null;
  critical_pass_rate?: number | null;
  source_discipline_score?: number | null;
  islamic_values_score?: number | null;
  fiqh_sensitivity_score?: number | null;
  last_eval_run?: string | null;
  eval_set_version: string;
  release_gate: ReleaseGate;
  coverage: { external_coverage: number; internal_coverage: number; islamic_specific_coverage: number };
  trend: { last?: number | null; seven_day_change?: number | null; thirty_day_change?: number | null; best?: number | null; worst?: number | null };
};
type ReleaseGate = { status: string; label: string; blocking_failures: string[]; thresholds?: Record<string, number>; run_id?: string };
type Suite = { id: string; name: string; category: string; version: string; question_count: number; last_run?: string; latest_score?: number };
type Freshness = { provider: string; display_name: string; source_type: string; last_refresh?: string; freshness_status: string; confidence_level: string; score_records: number };
type ComparePayload = {
  run: EvalRun | null;
  category_scores: { category: string; score: number; count: number }[];
  dimension_scores: Record<string, number>;
  external_scores: {
    provider: string;
    display_name: string;
    benchmark: string;
    benchmark_category: string;
    score?: number | null;
    normalized_score_0_100?: number | null;
    source_type: string;
    confidence_level: string;
    freshness_status: string;
    fetched_at?: string;
  }[];
  comparison_matrix: { capability: string; muslim_llm?: number | null; best_external?: number | null; gap?: number | null; confidence: string; external_status: string }[];
  insights: string[];
  warning?: string;
};

export default function EvalsDashboardPage() {
  const [models, setModels] = useState<EvalModel[]>([]);
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [items, setItems] = useState<RunItem[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [compare, setCompare] = useState<ComparePayload | null>(null);
  const [suites, setSuites] = useState<Suite[]>([]);
  const [freshness, setFreshness] = useState<Freshness[]>([]);
  const [failures, setFailures] = useState<RunItem[]>([]);
  const [running, setRunning] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const localModel = models.find((model) => model.is_local);
  const latestRun = compare?.run || runs[0];
  const dimensions = compare?.dimension_scores || {};
  const categoryScores = compare?.category_scores || [];
  const matrix = compare?.comparison_matrix || [];
  const weakRows = useMemo(
    () => [...categoryScores].filter((row) => Number(row.score) < 80).sort((a, b) => Number(a.score) - Number(b.score)).slice(0, 8),
    [categoryScores]
  );
  const radar = [
    { label: "Values", value: summary?.islamic_values_score ?? dimensions.islamic_values_alignment ?? 0 },
    { label: "Sources", value: summary?.source_discipline_score ?? dimensions.quran_hadith_discipline ?? 0 },
    { label: "Fiqh", value: summary?.fiqh_sensitivity_score ?? dimensions.fiqh_nuance ?? 0 },
    { label: "Useful", value: dimensions.practical_usefulness ?? summary?.overall_score ?? 0 },
    { label: "Truth", value: dimensions.factual_accuracy ?? summary?.overall_score ?? 0 },
    { label: "Safety", value: dimensions.safety_correctness ?? summary?.overall_score ?? 0 }
  ];

  function load() {
    apiGet<EvalModel[]>("/evals/models").then(setModels).catch(() => setModels([]));
    apiGet<{ runs: EvalRun[]; items: RunItem[] }>("/evals/runs")
      .then((data) => {
        setRuns(data.runs);
        setItems(data.items);
      })
      .catch(() => {
        setRuns([]);
        setItems([]);
      });
    apiGet<DashboardSummary>("/evals/dashboard-summary").then(setSummary).catch(() => setSummary(null));
    apiGet<ComparePayload>("/evals/compare").then(setCompare).catch(() => setCompare(null));
    apiGet<Suite[]>("/evals/suites").then(setSuites).catch(() => setSuites([]));
    apiGet<Freshness[]>("/evals/external-freshness").then(setFreshness).catch(() => setFreshness([]));
  }

  useEffect(load, []);

  useEffect(() => {
    if (!latestRun?.id) {
      setFailures([]);
      return;
    }
    apiGet<RunItem[]>(`/evals/runs/${latestRun.id}/failures`).then(setFailures).catch(() => setFailures([]));
  }, [latestRun?.id]);

  async function runEval() {
    setRunning(true);
    try {
      await apiPost("/evals/run", {
        model_id: localModel?.id,
        run_name: "Muslim LLM lab eval",
        temperature: 0.2,
        max_questions: 24,
        use_llm_judge: false
      });
      load();
    } finally {
      setRunning(false);
    }
  }

  async function refreshExternal() {
    setRefreshing(true);
    try {
      await apiPost("/evals/refresh-external", {});
      load();
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <main className="civilizational-surface min-h-dvh px-4 py-5 text-foreground">
      <div className="mx-auto max-w-[1500px]">
        <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <Link className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" href="/">
            <ArrowLeft size={16} /> Chat
          </Link>
          <div className="flex flex-wrap gap-2">
            <ExportButton href="/evals/report/latest.json" label="JSON" />
            <ExportButton href="/evals/report/latest.csv" label="CSV" />
            <ExportButton href="/evals/report/latest.md" label="MD" />
            <Button className="h-9 rounded-full" onClick={refreshExternal} disabled={refreshing}>
              <RefreshCcw size={15} /> {refreshing ? "Refreshing" : "Refresh"}
            </Button>
            <PrimaryButton className="h-9 rounded-full" onClick={runEval} disabled={running || !localModel}>
              <Play size={15} /> {running ? "Running" : "Run eval"}
            </PrimaryButton>
          </div>
        </header>

        <section className="mb-5 grid gap-4 lg:grid-cols-[1fr_420px]">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border bg-card/75 px-3 py-1 text-xs font-medium text-muted-foreground shadow-sm">
              <ShieldCheck size={14} /> Muslim LLM evaluation lab
            </div>
            <h1 className="display-type mt-3 text-4xl font-semibold leading-none sm:text-6xl">Release Readiness</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
              Internal alignment, source discipline, model quality, and external benchmark context.
            </p>
          </div>
          <GateCard gate={summary?.release_gate} />
        </section>

        <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <Metric icon={<Gauge size={18} />} label="Overall" value={score(summary?.overall_score)} detail={latestRun ? `${latestRun.total_questions} questions` : "No run"} />
          <Metric icon={<CheckCircle2 size={18} />} label="Pass rate" value={score(summary?.critical_pass_rate)} detail={summary?.trend?.seven_day_change != null ? `${signed(summary.trend.seven_day_change)} trend` : "Latest run"} />
          <Metric icon={<DatabaseZap size={18} />} label="Sources" value={score(summary?.source_discipline_score)} detail="Qur'an / Hadith discipline" />
          <Metric icon={<Scale size={18} />} label="Fiqh" value={score(summary?.fiqh_sensitivity_score)} detail={`Set ${summary?.eval_set_version || "v1"}`} />
        </section>

        <section className="mt-4 grid gap-4 xl:grid-cols-[0.9fr_1.15fr_0.95fr]">
          <Panel className="glass-panel p-4">
            <SectionTitle icon={<Activity size={16} />} title="Capability Shape" hint="0-100" />
            <RadarChart values={radar} />
          </Panel>

          <Panel className="glass-panel overflow-hidden">
            <SectionTitle className="p-4 pb-3" icon={<TrendingUp size={16} />} title="Comparison Matrix" hint="Directional" />
            <div className="max-h-[390px] overflow-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="border-y bg-muted/50 text-xs text-muted-foreground">
                  <tr>
                    {["Capability", "Muslim LLM", "External best", "Gap", "Confidence"].map((head) => <th key={head} className="p-3">{head}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {matrix.length === 0 ? (
                    <tr><td className="p-4 text-muted-foreground" colSpan={5}>Run an eval to build comparison rows.</td></tr>
                  ) : matrix.slice(0, 16).map((row) => (
                    <tr key={row.capability} className="border-t">
                      <td className="p-3 font-medium">{row.capability}</td>
                      <td className="p-3">{score(row.muslim_llm)}</td>
                      <td className="p-3">{score(row.best_external)}</td>
                      <td className={row.gap == null ? "p-3 text-muted-foreground" : row.gap >= 0 ? "p-3 text-primary" : "p-3 text-amber-700"}>{row.gap == null ? "-" : signed(row.gap)}</td>
                      <td className="p-3 capitalize text-muted-foreground">{row.confidence}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel className="glass-panel p-4">
            <SectionTitle icon={<Sparkles size={16} />} title="Lab Notes" hint="Latest" />
            <div className="mt-3 space-y-3">
              {(compare?.insights?.length ? compare.insights : ["Run evals to generate scored insights."]).slice(0, 5).map((item, index) => (
                <div key={index} className="rounded-lg border bg-background/55 p-3 text-sm leading-6">{item}</div>
              ))}
              {compare?.warning ? <p className="text-xs leading-5 text-muted-foreground">{compare.warning}</p> : null}
            </div>
          </Panel>
        </section>

        <section className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
          <Panel className="glass-panel overflow-hidden">
            <SectionTitle className="p-4 pb-3" icon={<Layers size={16} />} title="Eval Suites" hint={`${suites.reduce((sum, suite) => sum + Number(suite.question_count || 0), 0)} questions`} />
            <div className="grid max-h-[430px] gap-2 overflow-auto p-4 pt-0">
              {suites.length === 0 ? <Empty text="No suites loaded." /> : suites.map((suite) => (
                <div key={suite.id} className="rounded-lg border bg-background/55 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold">{labelize(suite.name)}</p>
                      <p className="text-xs text-muted-foreground">{suite.question_count} questions · {suite.version}</p>
                    </div>
                    <span className="rounded-full border px-2 py-1 text-xs">{suite.latest_score == null ? "new" : score(suite.latest_score)}</span>
                  </div>
                </div>
              ))}
            </div>
          </Panel>

          <Panel className="glass-panel overflow-hidden">
            <SectionTitle className="p-4 pb-3" icon={<AlertTriangle size={16} />} title="Weakness Explorer" hint={`${failures.length} open`} />
            <div className="max-h-[430px] overflow-auto">
              {(failures.length ? failures : items.filter((item) => Number(item.score || 0) < 80)).slice(0, 10).map((item) => (
                <div key={item.id} className="border-t p-4">
                  <div className="flex items-center justify-between gap-3 text-xs">
                    <span className="rounded-full border px-2 py-1 text-muted-foreground">{item.category || "General"}</span>
                    <span className={item.critical_failure ? "font-semibold text-red-700" : "text-muted-foreground"}>{score(item.score)}</span>
                  </div>
                  <p className="mt-2 text-sm font-medium leading-6">{item.prompt}</p>
                  <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.recommended_fix || item.failure_type || item.model_answer || "Review answer and rubric."}</p>
                </div>
              ))}
              {failures.length === 0 && items.length === 0 ? <Empty text="No scored failures yet." /> : null}
            </div>
          </Panel>
        </section>

        <section className="mt-4 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <Panel className="glass-panel p-4">
            <SectionTitle icon={<FileText size={16} />} title="Freshness" hint={`${freshness.length} sources`} />
            <div className="mt-3 grid gap-2">
              {freshness.length === 0 ? <Empty text="Refresh external benchmarks." /> : freshness.slice(0, 12).map((row) => (
                <div key={`${row.provider}-${row.display_name}-${row.source_type}`} className="flex items-center justify-between gap-3 rounded-lg border bg-background/55 p-3 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{row.display_name}</p>
                    <p className="text-xs text-muted-foreground">{row.source_type} · {row.score_records} records</p>
                  </div>
                  <span className={row.freshness_status === "Fresh" ? "text-primary" : "text-muted-foreground"}>{row.freshness_status}</span>
                </div>
              ))}
            </div>
          </Panel>

          <Panel className="glass-panel p-4">
            <SectionTitle icon={<DatabaseZap size={16} />} title="Coverage" hint="Bench depth" />
            <div className="mt-4 grid gap-3">
              <Progress label="External coverage" value={summary?.coverage?.external_coverage} />
              <Progress label="Internal coverage" value={summary?.coverage?.internal_coverage} />
              <Progress label="Islamic-specific coverage" value={summary?.coverage?.islamic_specific_coverage} />
            </div>
          </Panel>
        </section>
      </div>
    </main>
  );
}

function GateCard({ gate }: { gate?: ReleaseGate }) {
  const passed = gate?.status === "passed";
  const notRun = !gate || gate.status === "not_run";
  return (
    <Panel className="glass-panel p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Release gate</p>
          <h2 className="mt-1 text-xl font-semibold">{gate?.label || "Not run"}</h2>
        </div>
        {passed ? <CheckCircle2 className="text-primary" size={26} /> : notRun ? <ShieldCheck className="text-muted-foreground" size={26} /> : <XCircle className="text-red-700" size={26} />}
      </div>
      <div className="mt-3 space-y-2">
        {(gate?.blocking_failures?.length ? gate.blocking_failures : [passed ? "No blocking failures." : "Run the eval suite."]).map((item) => (
          <div key={item} className="rounded-lg border bg-background/55 px-3 py-2 text-sm">{item}</div>
        ))}
      </div>
    </Panel>
  );
}

function Metric({ icon, label, value, detail }: { icon: ReactNode; label: string; value: string; detail: string }) {
  return (
    <Panel className="glass-panel p-4">
      <div className="flex items-center justify-between text-muted-foreground">{icon}<span className="text-xs">{label}</span></div>
      <div className="mt-4 text-3xl font-semibold">{value}</div>
      <div className="mt-1 text-xs text-muted-foreground">{detail}</div>
    </Panel>
  );
}

function SectionTitle({ icon, title, hint, className = "" }: { icon: ReactNode; title: string; hint?: string; className?: string }) {
  return (
    <div className={`flex items-center justify-between gap-3 ${className}`}>
      <h2 className="inline-flex items-center gap-2 text-sm font-semibold">{icon}{title}</h2>
      {hint ? <span className="text-xs text-muted-foreground">{hint}</span> : null}
    </div>
  );
}

function RadarChart({ values }: { values: { label: string; value: number }[] }) {
  const points = values.map((item, index) => {
    const angle = (-90 + index * (360 / values.length)) * Math.PI / 180;
    const radius = 34 + (Math.max(0, Math.min(100, Number(item.value || 0))) / 100) * 66;
    return `${110 + Math.cos(angle) * radius},${110 + Math.sin(angle) * radius}`;
  }).join(" ");
  return (
    <div className="mt-4 grid place-items-center">
      <svg viewBox="0 0 220 220" className="h-64 w-full max-w-[320px]">
        {[35, 60, 85, 110].map((radius) => <circle key={radius} cx="110" cy="110" r={radius} fill="none" stroke="currentColor" className="text-border" />)}
        <polygon points={points} className="fill-primary/20 stroke-primary" strokeWidth="2" />
        {values.map((item, index) => {
          const angle = (-90 + index * (360 / values.length)) * Math.PI / 180;
          return (
            <g key={item.label}>
              <text x={110 + Math.cos(angle) * 100} y={114 + Math.sin(angle) * 100} textAnchor="middle" className="fill-muted-foreground text-[9px]">{item.label}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function Progress({ label, value }: { label: string; value?: number }) {
  const safe = Math.max(0, Math.min(100, Number(value || 0)));
  return (
    <div>
      <div className="mb-2 flex justify-between text-sm"><span>{label}</span><span>{safe.toFixed(1)}</span></div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary" style={{ width: `${safe}%` }} />
      </div>
    </div>
  );
}

function ExportButton({ href, label }: { href: string; label: string }) {
  return (
    <a className="inline-flex h-9 items-center justify-center gap-2 rounded-full border bg-card px-3 text-sm font-medium transition hover:bg-muted" href={`${API_BASE}${href}`} target="_blank">
      <Download size={14} /> {label}
    </a>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="p-4 text-sm text-muted-foreground">{text}</div>;
}

function score(value?: number | null) {
  return value == null ? "-" : Number(value).toFixed(1);
}

function signed(value: number) {
  return `${value >= 0 ? "+" : ""}${Number(value).toFixed(1)}`;
}

function labelize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
