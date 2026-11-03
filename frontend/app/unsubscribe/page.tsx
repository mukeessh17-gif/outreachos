"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

function UnsubscribeForm() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function unsubscribe() {
    setBusy(true);
    try {
      const response = await fetch(`/api/unsubscribe?token=${encodeURIComponent(token)}`, { method: "POST" });
      const data = await response.json();
      setMessage(response.ok ? data.message : (data.detail ?? "This unsubscribe link is invalid or expired."));
    } catch {
      setMessage("The unsubscribe service is unavailable. Please try again later.");
    } finally {
      setBusy(false);
    }
  }

  return <section className="mx-auto max-w-xl rounded-2xl bg-white p-8">
    <h1 className="text-3xl font-bold">Email preferences</h1>
    <p className="mt-4 leading-7">Confirm to permanently suppress this address from future messages for this workspace.</p>
    <button disabled={busy || !token} onClick={unsubscribe} className="mt-6 rounded-full bg-moss px-6 py-3 font-semibold text-white">{busy ? "Updating…" : "Unsubscribe"}</button>
    {message && <p role="status" className="mt-4">{message}</p>}
  </section>;
}

export default function UnsubscribePage() {
  return <Suspense fallback={<p>Loading unsubscribe form…</p>}><UnsubscribeForm /></Suspense>;
}
