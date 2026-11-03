"use client";

import { FormEvent, useEffect, useState } from "react";

type Settings = {
  tone: string;
  sample_emails: string[];
  banned_phrases: string[];
  sender_postal_address: string;
  calendar_link: string;
  daily_token_budget: number;
  per_lead_token_budget: number;
  daily_lead_limit: number;
};

type Inbox = { id: number; email: string; daily_limit: number; connected: boolean };
type Identity = { org_name: string; role: string };

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [inboxes, setInboxes] = useState<Inbox[]>([]);
  const [inboxEmail, setInboxEmail] = useState("");
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/settings", { cache: "no-store" })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail ?? "Settings unavailable.");
        setSettings(data);
      })
      .catch((issue: unknown) => setError(issue instanceof Error ? issue.message : "Settings unavailable."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetch("/api/auth/me", { cache: "no-store" })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail ?? "Workspace identity unavailable.");
        setIdentity(data);
      })
      .catch((issue: unknown) => setError(issue instanceof Error ? issue.message : "Workspace identity unavailable."));
  }, []);

  useEffect(() => {
    fetch("/api/inboxes", { cache: "no-store" })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail ?? "Inbox list unavailable.");
        setInboxes(data);
      })
      .catch((issue: unknown) => setError(issue instanceof Error ? issue.message : "Inbox list unavailable."));
  }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!settings) return;
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setMessage("");
    setError("");
    const payload = {
      tone: String(form.get("tone")),
      sample_emails: String(form.get("sample_emails")).split("\n").map((value) => value.trim()).filter(Boolean),
      banned_phrases: String(form.get("banned_phrases")).split("\n").map((value) => value.trim()).filter(Boolean),
      sender_postal_address: String(form.get("sender_postal_address")),
      calendar_link: String(form.get("calendar_link")),
      daily_token_budget: Number(form.get("daily_token_budget")),
      per_lead_token_budget: Number(form.get("per_lead_token_budget")),
      daily_lead_limit: Number(form.get("daily_lead_limit")),
    };
    try {
      const response = await fetch("/api/settings", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Settings save failed.");
      setSettings(data);
      setMessage("Settings saved.");
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Settings save failed.");
    } finally {
      setBusy(false);
    }
  }

  async function addDryRunInbox() {
    setError("");
    try {
      const response = await fetch("/api/inboxes", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: inboxEmail }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Inbox could not be added.");
      setInboxEmail("");
      setInboxes((current) => [data, ...current.filter((inbox) => inbox.id !== data.id)]);
      setMessage(data.connected ? "Inbox already connected." : "Dry-run inbox saved; no email can be sent from it.");
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Inbox could not be added.");
    }
  }

  if (loading) return <p>Loading settings…</p>;
  if (!settings) return <p role="alert" className="text-red-700">{error}</p>;
  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <div><p className="text-sm font-bold uppercase tracking-widest text-moss">Workspace</p><h1 className="mt-2 text-4xl font-bold">Settings</h1></div>
      <form onSubmit={save} className="space-y-5 rounded-2xl bg-white p-6">
        <label className="block font-semibold">Brand tone
          <input name="tone" required maxLength={80} defaultValue={settings.tone} className="mt-1 w-full rounded-lg border p-3" />
        </label>
        <label className="block font-semibold">Sample emails <span className="font-normal text-ink/60">(one per line; use fictional examples)</span>
          <textarea name="sample_emails" rows={4} defaultValue={settings.sample_emails.join("\n")} className="mt-1 w-full rounded-lg border p-3" />
        </label>
        <label className="block font-semibold">Banned phrases <span className="font-normal text-ink/60">(one per line)</span>
          <textarea name="banned_phrases" rows={4} defaultValue={settings.banned_phrases.join("\n")} className="mt-1 w-full rounded-lg border p-3" />
        </label>
        <label className="block font-semibold">Sender postal address
          <textarea required name="sender_postal_address" maxLength={500} defaultValue={settings.sender_postal_address} className="mt-1 w-full rounded-lg border p-3" />
        </label>
        <label className="block font-semibold">Public booking link
          <input type="url" name="calendar_link" maxLength={2000} defaultValue={settings.calendar_link} placeholder="https://calendar.google.com/..." className="mt-1 w-full rounded-lg border p-3" />
        </label>
        <div className="grid gap-4 md:grid-cols-3">
          <label className="text-sm font-semibold">Daily token budget<input type="number" min={1} name="daily_token_budget" defaultValue={settings.daily_token_budget} className="mt-1 w-full rounded-lg border p-3" /></label>
          <label className="text-sm font-semibold">Tokens per lead<input type="number" min={1} name="per_lead_token_budget" defaultValue={settings.per_lead_token_budget} className="mt-1 w-full rounded-lg border p-3" /></label>
          <label className="text-sm font-semibold">Daily lead limit<input type="number" min={1} name="daily_lead_limit" defaultValue={settings.daily_lead_limit} className="mt-1 w-full rounded-lg border p-3" /></label>
        </div>
        {error && <p role="alert" className="text-red-700">{error}</p>}
        {message && <p role="status">{message}</p>}
        <button disabled={busy} className="rounded-full bg-moss px-6 py-3 font-semibold text-white">{busy ? "Saving…" : "Save settings"}</button>
      </form>
      <section className="space-y-4 rounded-2xl bg-white p-6">
        <h2 className="text-xl font-bold">Gmail and Calendar</h2>
        <p className="text-sm leading-6 text-ink/70">OAuth stays optional. Use a Google Cloud project in Testing mode and add only your own account as a test user. Tokens are encrypted at rest.</p>
        <button
          type="button"
          onClick={async () => {
            setError("");
            try {
              const response = await fetch("/api/integrations/google/start", { method: "POST" });
              const data = await response.json();
              if (!response.ok) throw new Error(data.detail ?? "Google authorization could not start.");
              window.location.assign(data.authorization_url);
            } catch (issue) {
              setError(issue instanceof Error ? issue.message : "Google authorization could not start.");
            }
          }}
          className="rounded-full border px-5 py-3 font-semibold"
        >Connect my Google account</button>
        <form onSubmit={(event) => { event.preventDefault(); void addDryRunInbox(); }} className="flex flex-wrap gap-2">
          <label className="sr-only" htmlFor="dry-run-inbox">Dry-run sender address</label>
          <input id="dry-run-inbox" required type="email" value={inboxEmail} onChange={(event) => setInboxEmail(event.target.value)} placeholder="owner@example.com" className="min-w-64 rounded-lg border p-3" />
          <button type="submit" className="rounded-full border px-5 py-3 font-semibold">Add dry-run inbox</button>
        </form>
        <ul className="space-y-1 text-sm">{inboxes.map((inbox) => <li key={inbox.id}>{inbox.email} · limit {inbox.daily_limit}/day · {inbox.connected ? "OAuth connected" : "dry-run only"}</li>)}</ul>
        <button
          type="button"
          onClick={async () => {
            try {
              const response = await fetch("/api/billing/checkout", { method: "POST" });
              const data = await response.json();
              if (!response.ok) throw new Error(data.detail ?? "Test checkout could not start.");
              window.location.assign(data.checkout_url);
            } catch (issue) {
              setError(issue instanceof Error ? issue.message : "Test checkout could not start.");
            }
          }}
          className="ml-2 rounded-full bg-moss px-5 py-3 font-semibold text-white"
        >Manage Stripe test plan</button>
        <p className="text-xs text-ink/60">Stripe checkout is test-mode only and requires a Stripe test product ID in the local environment.</p>
      </section>
      <section className="flex flex-wrap gap-3 rounded-2xl bg-white p-6">
        <button type="button" onClick={async () => {
          const response = await fetch("/api/data/export");
          const data = await response.json();
          if (!response.ok) { setError(data.detail ?? "Data export failed."); return; }
          const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
          const anchor = document.createElement("a");
          anchor.href = url;
          anchor.download = "outreachos-export.json";
          anchor.click();
          URL.revokeObjectURL(url);
        }} className="rounded-full border px-5 py-3 font-semibold">Export workspace data</button>
      </section>
      {identity?.role === "owner" && <section className="space-y-4 rounded-2xl border border-red-200 bg-white p-6">
        <h2 className="text-xl font-bold text-red-800">Delete workspace data</h2>
        <p className="text-sm leading-6">This permanently deletes the current workspace and its leads, drafts, outbox, and usage records. Type <strong>{identity.org_name}</strong> exactly to confirm.</p>
        <div className="flex flex-wrap gap-2">
          <input value={deleteConfirmation} onChange={(event) => setDeleteConfirmation(event.target.value)} aria-label="Workspace name confirmation" className="min-w-64 rounded-lg border p-3" />
          <button type="button" disabled={deleteConfirmation !== identity.org_name} onClick={async () => {
            const response = await fetch(`/api/data/account?confirmation=${encodeURIComponent(deleteConfirmation)}`, { method: "DELETE" });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) { setError(data.detail ?? "Workspace deletion failed."); return; }
            await fetch("/api/auth/logout", { method: "POST" });
            window.location.assign("/");
          }} className="rounded-full bg-red-700 px-5 py-3 font-semibold text-white disabled:opacity-50">Permanently delete workspace</button>
        </div>
      </section>}
    </section>
  );
}
