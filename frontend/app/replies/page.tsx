"use client";

import { useCallback, useEffect, useState } from "react";

type Reply = {
  id: number;
  lead_id: number;
  sender_email: string | null;
  category: string;
  body: string;
  draft_response: string | null;
  status: string;
};

type Inbox = { id: number; email: string; connected: boolean };

export default function RepliesPage() {
  const [replies, setReplies] = useState<Reply[]>([]);
  const [inboxes, setInboxes] = useState<Inbox[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [replyResponse, inboxResponse] = await Promise.all([
        fetch("/api/replies?status=draft", { cache: "no-store" }),
        fetch("/api/inboxes", { cache: "no-store" }),
      ]);
      const replyData = await replyResponse.json();
      const inboxData = await inboxResponse.json();
      if (!replyResponse.ok) throw new Error(replyData.detail ?? "Replies could not be loaded.");
      if (!inboxResponse.ok) throw new Error(inboxData.detail ?? "Connected inboxes could not be loaded.");
      setReplies(replyData);
      setInboxes(inboxData);
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Replies could not be loaded.");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function sync() {
    const inbox = inboxes.find((item) => item.connected);
    if (!inbox) {
      setError("Connect a Google inbox in Settings before synchronizing replies.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/integrations/google/replies/sync?inbox_id=${inbox.id}`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Reply synchronization failed.");
      setMessage(`Processed ${data.processed} replies; ignored ${data.ignored}.`);
      await load();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Reply synchronization failed.");
    } finally {
      setBusy(false);
    }
  }

  async function decide(id: number, decision: "approve" | "reject") {
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/replies/${id}/${decision}`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Reply review failed.");
      setMessage(`Response ${decision}d. No email was sent.`);
      await load();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Reply review failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-sm font-bold uppercase tracking-widest text-moss">Human review</p><h1 className="mt-2 text-4xl font-bold">Reply queue</h1></div>
        <button disabled={busy} onClick={sync} className="rounded-full bg-moss px-5 py-3 font-semibold text-white">{busy ? "Syncing…" : "Sync Gmail replies"}</button>
      </header>
      <p className="rounded-xl bg-lime/40 p-4 text-sm">Unsubscribe replies are suppressed automatically. Other response drafts wait for your review and are never sent automatically.</p>
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-800">{error}</p>}
      {message && <p role="status" className="rounded-lg bg-white p-3">{message}</p>}
      {replies.length === 0 && <p>No reply drafts need review.</p>}
      <div className="space-y-4">
        {replies.map((reply) => <article key={reply.id} className="space-y-4 rounded-2xl bg-white p-5">
          <div className="flex flex-wrap justify-between gap-3">
            <div><h2 className="text-lg font-bold capitalize">{reply.category.replaceAll("-", " ")}</h2><p className="text-sm text-ink/60">{reply.sender_email ?? "Sender unknown"} · Lead #{reply.lead_id}</p></div>
            <div className="flex gap-2"><button disabled={busy} onClick={() => decide(reply.id, "approve")} className="rounded bg-moss px-4 py-2 text-white">Approve</button><button disabled={busy} onClick={() => decide(reply.id, "reject")} className="rounded border px-4 py-2">Reject</button></div>
          </div>
          <blockquote className="whitespace-pre-wrap border-l-2 border-ink/20 pl-4 text-sm">{reply.body}</blockquote>
          {reply.draft_response && <p className="rounded-lg bg-ink/5 p-4 text-sm"><strong>Suggested response:</strong><br />{reply.draft_response}</p>}
        </article>)}
      </div>
    </section>
  );
}
