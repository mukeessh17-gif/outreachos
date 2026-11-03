"use client";

import { useEffect, useState } from "react";

type Dashboard = { sent: number; replies: number; reply_rate: number; meetings: number; cost_per_lead: number; lead_count: number };

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    fetch("/api/analytics/dashboard", { cache: "no-store" })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail ?? "Analytics unavailable.");
        setMetrics(data);
      })
      .catch((issue: unknown) => setError(issue instanceof Error ? issue.message : "Analytics unavailable."));
  }, []);

  return (
    <section className="space-y-6">
      <div><p className="text-sm font-bold uppercase tracking-widest text-moss">Workspace overview</p><h1 className="mt-2 text-4xl font-bold">Analytics</h1></div>
      {error && <p role="alert" className="text-red-700">{error}</p>}
      {!metrics ? <p>Loading dashboard…</p> : <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          ["Leads", metrics.lead_count],
          ["Sent (live)", metrics.sent],
          ["Replies", metrics.replies],
          ["Reply rate", `${(metrics.reply_rate * 100).toFixed(1)}%`],
          ["Meetings", metrics.meetings],
          ["Cost per lead", `$${metrics.cost_per_lead.toFixed(2)}`],
        ].map(([label, value]) => <article key={label} className="rounded-2xl bg-white p-6"><p className="text-sm text-ink/60">{label}</p><p className="mt-2 text-3xl font-bold">{value}</p></article>)}
      </div>}
      <p className="text-sm text-ink/60">A/B versions are tracked per lead. Dry-run messages are not counted as sent.</p>
    </section>
  );
}
