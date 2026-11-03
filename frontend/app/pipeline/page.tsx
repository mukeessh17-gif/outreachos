"use client";

import { useCallback, useEffect, useState } from "react";

type Lead = { id: number; name: string; city: string | null; pipeline_stage: string };
type Board = Record<string, Lead[]>;
const stages = ["new", "contacted", "replied", "meeting", "closed"];

export default function PipelinePage() {
  const [board, setBoard] = useState<Board>({});
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const response = await fetch("/api/pipeline", { cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Pipeline unavailable.");
      setBoard(data);
      setError("");
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Pipeline unavailable.");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function advance(lead: Lead) {
    const next = stages[Math.min(stages.indexOf(lead.pipeline_stage) + 1, stages.length - 1)];
    if (next === lead.pipeline_stage) return;
    const response = await fetch(`/api/leads/${lead.id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ pipeline_stage: next }),
    });
    const data = await response.json();
    if (!response.ok) setError(data.detail ?? "Could not update stage.");
    else await load();
  }

  return (
    <section className="space-y-6">
      <div><p className="text-sm font-bold uppercase tracking-widest text-moss">Sales workflow</p><h1 className="mt-2 text-4xl font-bold">Pipeline</h1></div>
      {error && <p role="alert" className="text-red-700">{error}</p>}
      <div className="grid gap-4 md:grid-cols-5">
        {stages.map((stage) => <div key={stage} className="min-h-64 rounded-2xl bg-ink/5 p-3">
          <h2 className="mb-3 px-2 font-bold capitalize">{stage} <span className="text-sm text-ink/50">{board[stage]?.length ?? 0}</span></h2>
          <div className="space-y-2">{(board[stage] ?? []).map((lead) => <article key={lead.id} className="rounded-xl bg-white p-3">
            <h3 className="font-semibold">{lead.name}</h3><p className="text-sm text-ink/60">{lead.city ?? "—"}</p>
            {stage !== "closed" && <button onClick={() => advance(lead)} className="mt-2 text-sm text-moss underline">Move to next stage</button>}
          </article>)}</div>
        </div>)}
      </div>
    </section>
  );
}
