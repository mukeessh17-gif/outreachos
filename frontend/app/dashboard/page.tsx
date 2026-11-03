"use client";

import { ChangeEvent, FormEvent, useCallback, useEffect, useState } from "react";

type Lead = {
  id: number;
  name: string;
  city?: string | null;
  employees: number;
  website?: string | null;
  pipeline_stage: string;
};

type CsvPreview = {
  accepted_count: number;
  accepted: Lead[];
  rejected: { row: number; reason: string }[];
};

export default function DashboardPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [query, setQuery] = useState("");
  const [stage, setStage] = useState("");
  const [csv, setCsv] = useState("");
  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadLeads = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (query.trim()) params.set("search", query.trim());
      if (stage) params.set("stage", stage);
      const response = await fetch(`/api/leads?${params}`, { cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not load leads.");
      setLeads(data);
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Could not load leads.");
    } finally {
      setLoading(false);
    }
  }, [query, stage]);

  useEffect(() => { void loadLeads(); }, [loadLeads]);

  async function loadCsv(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const value = await file.text();
      setCsv(value);
      const response = await fetch("/api/leads/import/preview", {
        method: "POST",
        headers: { "content-type": "text/csv" },
        body: value,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "CSV preview failed.");
      setPreview(data);
      setNotice("");
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "CSV preview failed.");
      setPreview(null);
    } finally {
      setBusy(false);
    }
  }

  async function importCsv() {
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/leads/import", {
        method: "POST",
        headers: { "content-type": "text/csv" },
        body: csv,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "CSV import failed.");
      setNotice(`Imported ${data.inserted} leads; ${data.duplicates} duplicates skipped.`);
      setPreview(null);
      await loadLeads();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "CSV import failed.");
    } finally {
      setBusy(false);
    }
  }

  async function createLead(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/leads", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          name: form.get("name"),
          city: form.get("city") || null,
          employees: Number(form.get("employees") || 0),
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Lead creation failed.");
      event.currentTarget.reset();
      setNotice("Lead created.");
      await loadLeads();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Lead creation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function enqueue(leadId: number, step: "research" | "email-sequences") {
    setBusy(true);
    setError("");
    try {
      const url = step === "research" ? `/api/leads/${leadId}/research` : `/api/email-sequences?lead_id=${leadId}`;
      const response = await fetch(url, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not queue this task.");
      setNotice(`Job ${data.job_id} queued. Follow its status on the Jobs page.`);
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Could not queue this task.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-bold uppercase tracking-widest text-moss">Workspace</p>
        <h1 className="mt-2 text-4xl font-bold">Leads</h1>
      </div>
      <section className="rounded-2xl bg-white p-5">
        <h2 className="text-lg font-bold">Add one lead</h2>
        <form onSubmit={createLead} className="mt-3 grid gap-3 md:grid-cols-4">
          <input required minLength={2} name="name" placeholder="Fictional Company" className="rounded-lg border p-3" />
          <input name="city" placeholder="City (optional)" className="rounded-lg border p-3" />
          <input type="number" min={0} name="employees" placeholder="Employees" className="rounded-lg border p-3" />
          <button disabled={busy} className="rounded-lg bg-moss px-4 py-3 font-semibold text-white">Add lead</button>
        </form>
      </section>
      <section className="rounded-2xl bg-white p-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold">Import a CSV</h2>
            <p className="text-sm text-ink/60">Required columns: name, employees. Optional: city, website.</p>
          </div>
          <label className="cursor-pointer rounded-lg border px-4 py-2 font-semibold">
            Choose CSV
            <input type="file" accept=".csv,text/csv" onChange={loadCsv} className="sr-only" />
          </label>
        </div>
        {preview && <div className="mt-5 space-y-3">
          <p>Preview: {preview.accepted_count} valid rows; {preview.rejected.length} rejected.</p>
          {preview.rejected.length > 0 && <ul className="list-inside list-disc rounded-lg bg-red-50 p-4 text-sm text-red-800">
            {preview.rejected.map((row) => <li key={row.row}>Row {row.row}: {row.reason}</li>)}
          </ul>}
          <button disabled={busy || preview.accepted_count === 0} onClick={importCsv} className="rounded-lg bg-moss px-4 py-2 font-semibold text-white">
            {busy ? "Importing…" : `Import ${preview.accepted_count} valid rows`}
          </button>
        </div>}
      </section>
      <section>
        <div className="mb-4 flex flex-wrap gap-3">
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search company name" className="rounded-lg border bg-white p-3" />
          <select value={stage} onChange={(event) => setStage(event.target.value)} className="rounded-lg border bg-white p-3">
            <option value="">All stages</option>
            {["new", "contacted", "replied", "meeting", "closed"].map((item) => <option key={item}>{item}</option>)}
          </select>
        </div>
        {error && <p role="alert" className="mb-3 rounded-lg bg-red-50 p-3 text-red-800">{error}</p>}
        {notice && <p role="status" className="mb-3 rounded-lg bg-lime/40 p-3">{notice}</p>}
        <div className="overflow-x-auto rounded-2xl bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-ink/5"><tr>{["Company", "City", "Employees", "Stage", "Actions"].map((label) => <th key={label} className="p-4">{label}</th>)}</tr></thead>
            <tbody>
              {loading ? <tr><td className="p-5" colSpan={5}>Loading leads…</td></tr>
                : leads.length === 0 ? <tr><td className="p-5" colSpan={5}>No leads found.</td></tr>
                : leads.map((lead) => <tr key={lead.id} className="border-t border-ink/10">
                  <td className="p-4 font-semibold">{lead.name}</td>
                  <td className="p-4">{lead.city ?? "—"}</td>
                  <td className="p-4">{lead.employees}</td>
                  <td className="p-4 capitalize">{lead.pipeline_stage}</td>
                  <td className="flex flex-wrap gap-2 p-4">
                    <button disabled={busy || !lead.website} title={!lead.website ? "Add a website first" : ""} onClick={() => enqueue(lead.id, "research")} className="rounded border px-3 py-1">Research</button>
                    <button disabled={busy} onClick={() => enqueue(lead.id, "email-sequences")} className="rounded border px-3 py-1">Draft emails</button>
                  </td>
                </tr>)}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
