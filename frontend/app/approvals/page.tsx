"use client";

import { useCallback, useEffect, useState } from "react";

type EmailDraft = { id: number; subject: string; body: string; send_delay_days: number };
type Sequence = { id: number; lead_id: number; company_name: string; status: string; tokens_used: number; cost_usd: number };

export default function ApprovalsPage() {
  const [sequences, setSequences] = useState<Sequence[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [drafts, setDrafts] = useState<EmailDraft[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const response = await fetch("/api/email-sequences?status=draft", { cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not load approval queue.");
      setSequences(data);
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Could not load approval queue.");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function open(id: number) {
    setSelected(id);
    setError("");
    const response = await fetch(`/api/email-sequences/${id}`);
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? "Could not load drafts.");
      return;
    }
    setDrafts(data.emails);
  }

  async function act(id: number, status: "approved" | "rejected") {
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/email-sequences/${id}/status`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ status }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Approval update failed.");
      setMessage(`Sequence ${status}. No email was sent.`);
      setSelected(null);
      await load();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Approval update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function bulkApprove() {
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/email-sequences/bulk-approve", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ sequence_ids: sequences.map((sequence) => sequence.id) }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Bulk approval failed.");
      setMessage(`${data.approved} sequence(s) approved. No email was sent.`);
      await load();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Bulk approval failed.");
    } finally {
      setBusy(false);
    }
  }

  async function saveDraft(draft: EmailDraft) {
    if (selected === null) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/email-sequences/${selected}/drafts/${draft.id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(draft),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Draft edit failed.");
      setMessage("Draft saved and safety checks passed.");
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Draft edit failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-sm font-bold uppercase tracking-widest text-moss">Human review</p><h1 className="mt-2 text-4xl font-bold">Approval queue</h1></div>
        <button disabled={busy || sequences.length === 0} onClick={bulkApprove} className="rounded-full bg-moss px-5 py-3 font-semibold text-white">Bulk approve all drafts</button>
      </div>
      <p className="rounded-xl bg-lime/40 p-4 text-sm">Approval only changes draft status. Sending stays dry-run unless configured separately.</p>
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-800">{error}</p>}
      {message && <p role="status" className="rounded-lg bg-white p-3">{message}</p>}
      <div className="grid gap-4">
        {sequences.length === 0 && <p>No drafts awaiting approval.</p>}
        {sequences.map((sequence) => <article key={sequence.id} className="rounded-2xl bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div><h2 className="text-xl font-bold">{sequence.company_name}</h2><p className="text-sm text-ink/60">Lead #{sequence.lead_id} · {sequence.tokens_used} tokens · ${sequence.cost_usd.toFixed(2)}</p></div>
            <div className="flex gap-2">
              <button onClick={() => open(sequence.id)} className="rounded border px-4 py-2">Review / edit</button>
              <button disabled={busy} onClick={() => act(sequence.id, "approved")} className="rounded bg-moss px-4 py-2 text-white">Approve</button>
              <button disabled={busy} onClick={() => act(sequence.id, "rejected")} className="rounded border px-4 py-2">Reject</button>
            </div>
          </div>
          {selected === sequence.id && <div className="mt-5 space-y-4 border-t pt-4">
            {drafts.map((draft, index) => <div key={draft.id} className="rounded-xl border p-4">
              <p className="mb-2 text-xs font-bold uppercase tracking-widest">Email {index + 1} · day {draft.send_delay_days}</p>
              <label className="block text-sm font-semibold">Subject
                <input value={draft.subject} onChange={(event) => setDrafts((old) => old.map((item) => item.id === draft.id ? { ...item, subject: event.target.value } : item))} className="mt-1 w-full rounded border p-2" />
              </label>
              <label className="mt-3 block text-sm font-semibold">Body
                <textarea rows={5} value={draft.body} onChange={(event) => setDrafts((old) => old.map((item) => item.id === draft.id ? { ...item, body: event.target.value } : item))} className="mt-1 w-full rounded border p-2" />
              </label>
              <button disabled={busy} onClick={() => saveDraft(draft)} className="mt-3 rounded border px-4 py-2">Save changes</button>
            </div>)}
          </div>}
        </article>)}
      </div>
    </div>
  );
}
