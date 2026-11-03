"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

type Sequence = { id: number; company_name: string; lead_id: number };
type Draft = { id: number; subject: string; send_delay_days: number };
type Inbox = { id: number; email: string; connected: boolean };
type OutboxItem = { id: number; recipient: string; subject: string; status: string };

export default function OutboxPage() {
  const [sequences, setSequences] = useState<Sequence[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [inboxes, setInboxes] = useState<Inbox[]>([]);
  const [items, setItems] = useState<OutboxItem[]>([]);
  const [sequenceId, setSequenceId] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const responses = await Promise.all([
        fetch("/api/email-sequences?status=approved", { cache: "no-store" }),
        fetch("/api/inboxes", { cache: "no-store" }),
        fetch("/api/outbox", { cache: "no-store" }),
      ]);
      const values = await Promise.all(responses.map((response) => response.json()));
      const failed = responses.findIndex((response) => !response.ok);
      if (failed >= 0) throw new Error(values[failed].detail ?? "Outbox data could not be loaded.");
      setSequences(values[0]);
      setInboxes(values[1]);
      setItems(values[2]);
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Outbox data could not be loaded.");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function selectSequence(value: string) {
    setSequenceId(value);
    setDrafts([]);
    if (!value) return;
    const response = await fetch(`/api/email-sequences/${value}`);
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? "Approved drafts could not be loaded.");
      return;
    }
    setDrafts(data.emails);
  }

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/outbox/send", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          draft_id: Number(form.get("draft_id")),
          inbox_id: Number(form.get("inbox_id")),
          recipient: form.get("recipient"),
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Outbox action failed.");
      setMessage(data.status === "dry_run" ? "Dry-run saved. No email was sent." : `Outbox status: ${data.status}.`);
      await load();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Outbox action failed.");
    } finally {
      setBusy(false);
    }
  }

  async function schedule(form: HTMLFormElement) {
    if (!sequenceId) return;
    const values = new FormData(form);
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/email-sequences/${sequenceId}/schedule`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          inbox_id: Number(values.get("inbox_id")),
          recipient: values.get("recipient"),
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Sequence scheduling failed.");
      setMessage(`${data.scheduled.length} email(s) scheduled. Delivery uses the configured dry-run/live mode.`);
      await load();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Sequence scheduling failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-6">
      <div><p className="text-sm font-bold uppercase tracking-widest text-moss">Dry-run first</p><h1 className="mt-2 text-4xl font-bold">Outbox</h1></div>
      <p className="rounded-xl bg-lime/40 p-4 text-sm">Default mode stores messages here and never sends. Live sends require an OAuth-connected inbox, your own allowlisted recipient address, and the sender postal address.</p>
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-800">{error}</p>}
      {message && <p role="status" className="rounded-lg bg-white p-3">{message}</p>}
      <form onSubmit={send} className="space-y-4 rounded-2xl bg-white p-5">
        <h2 className="text-lg font-bold">Create outbox entry</h2>
        <label className="block text-sm font-semibold">Approved sequence
          <select required value={sequenceId} onChange={(event) => void selectSequence(event.target.value)} className="mt-1 w-full rounded border p-3">
            <option value="">Select sequence</option>{sequences.map((item) => <option key={item.id} value={item.id}>{item.company_name} · #{item.id}</option>)}
          </select>
        </label>
        <label className="block text-sm font-semibold">Email draft
          <select required name="draft_id" className="mt-1 w-full rounded border p-3">
            <option value="">Select draft</option>{drafts.map((draft) => <option key={draft.id} value={draft.id}>Day {draft.send_delay_days}: {draft.subject}</option>)}
          </select>
        </label>
        <label className="block text-sm font-semibold">Sender inbox
          <select required name="inbox_id" className="mt-1 w-full rounded border p-3">
            {inboxes.map((inbox) => <option key={inbox.id} value={inbox.id}>{inbox.email}{inbox.connected ? " (connected)" : " (dry-run only)"}</option>)}
          </select>
        </label>
        <label className="block text-sm font-semibold">Recipient address
          <input required type="email" name="recipient" className="mt-1 w-full rounded border p-3" />
        </label>
        <button disabled={busy || drafts.length === 0 || inboxes.length === 0} className="rounded-full bg-moss px-5 py-3 font-semibold text-white">{busy ? "Saving…" : "Add to outbox"}</button>
        <button type="button" disabled={busy || !sequenceId || inboxes.length === 0} onClick={(event) => {
          const form = event.currentTarget.form;
          if (form) void schedule(form);
        }} className="ml-2 rounded-full border px-5 py-3 font-semibold">Schedule full sequence</button>
      </form>
      <section className="space-y-3">
        <h2 className="text-xl font-bold">Recent messages</h2>
        {items.map((item) => <article key={item.id} className="flex flex-wrap justify-between gap-3 rounded-xl bg-white p-4">
          <div><p className="font-semibold">{item.subject}</p><p className="text-sm text-ink/60">To {item.recipient}</p></div><span className="rounded-full bg-ink/5 px-3 py-1 text-sm">{item.status}</span>
        </article>)}
        {items.length === 0 && <p>No outbox entries yet.</p>}
      </section>
    </section>
  );
}
