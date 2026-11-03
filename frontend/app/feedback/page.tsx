"use client";

import { FormEvent, useState } from "react";

export default function FeedbackPage() {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ rating: Number(form.get("rating")), message: form.get("message") }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Feedback could not be saved.");
      setMessage("Thanks—your feedback was saved.");
      event.currentTarget.reset();
    } catch (issue) {
      setMessage(issue instanceof Error ? issue.message : "Feedback could not be saved.");
    } finally {
      setBusy(false);
    }
  }
  return <section className="mx-auto max-w-xl space-y-5">
    <h1 className="text-4xl font-bold">Beta feedback</h1>
    <form onSubmit={submit} className="space-y-4 rounded-2xl bg-white p-6">
      <label className="block font-semibold">Rating
        <select name="rating" required className="mt-1 w-full rounded border p-3">{[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n} / 5</option>)}</select>
      </label>
      <label className="block font-semibold">What worked? What should improve?
        <textarea required minLength={5} maxLength={2000} name="message" rows={6} className="mt-1 w-full rounded border p-3" />
      </label>
      <button disabled={busy} className="rounded-full bg-moss px-5 py-3 font-semibold text-white">{busy ? "Sending…" : "Send feedback"}</button>
      {message && <p role="status">{message}</p>}
    </form>
  </section>;
}
