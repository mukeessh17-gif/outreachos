"use client";

import { useCallback, useEffect, useState } from "react";

type Job = {
  id: number;
  lead_id: number;
  step: string;
  status: string;
  attempts: number;
  max_attempts: number;
  last_error?: string | null;
};

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/jobs", { cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not load jobs.");
      setJobs(data);
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Could not load jobs.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  return (
    <section className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div><p className="text-sm font-bold uppercase tracking-widest text-moss">Background work</p><h1 className="mt-2 text-4xl font-bold">Job status</h1></div>
        <button onClick={refresh} className="rounded border bg-white px-4 py-2">Refresh</button>
      </div>
      <p className="rounded-xl bg-lime/40 p-4 text-sm">Run one worker process per organization: <code>python -m week4.worker --org-id 1</code></p>
      {error && <p role="alert" className="text-red-700">{error}</p>}
      {loading ? <p>Loading jobs…</p> : jobs.length === 0 ? <p>No jobs queued.</p> : <div className="overflow-x-auto rounded-2xl bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-ink/5"><tr>{["Job", "Lead", "Step", "Status", "Attempts", "Error type"].map((item) => <th key={item} className="p-4">{item}</th>)}</tr></thead>
          <tbody>{jobs.map((job) => <tr key={job.id} className="border-t border-ink/10">
            <td className="p-4">#{job.id}</td><td className="p-4">#{job.lead_id}</td>
            <td className="p-4">{job.step}</td><td className="p-4 capitalize">{job.status}</td>
            <td className="p-4">{job.attempts}/{job.max_attempts}</td><td className="p-4">{job.last_error ?? "—"}</td>
          </tr>)}</tbody>
        </table>
      </div>}
    </section>
  );
}
