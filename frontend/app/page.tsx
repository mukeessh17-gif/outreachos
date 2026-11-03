import Link from "next/link";

const highlights = [
  ["Research with sources", "Summarize only public company-site text and keep citations attached."],
  ["Review before sending", "Every sequence starts as a draft. Sending is dry-run by default."],
  ["Tenant-aware", "Organization-scoped data and explicit approval are built into the workflow."],
];

export default function HomePage() {
  return (
    <div className="space-y-16">
      <section className="grid gap-10 py-12 md:grid-cols-[1.4fr_0.8fr] md:items-center">
        <div>
          <p className="mb-4 text-sm font-bold uppercase tracking-[0.2em] text-moss">Outreach that stays grounded</p>
          <h1 className="max-w-3xl text-5xl font-bold leading-tight tracking-tight md:text-6xl">
            Thoughtful B2B outreach, with a human in control.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-ink/70">
            Research public business information, draft evidence-backed email sequences, and approve every message before it leaves your outbox.
          </p>
          <div className="mt-8 flex gap-3">
            <Link href="/signup" className="rounded-full bg-moss px-6 py-3 font-semibold text-white">Create a free workspace</Link>
            <Link href="/login" className="rounded-full border border-ink/20 px-6 py-3 font-semibold">Sign in</Link>
          </div>
        </div>
        <aside className="rounded-3xl bg-ink p-8 text-white shadow-xl">
          <p className="text-sm uppercase tracking-widest text-lime">Safe by default</p>
          <p className="mt-5 text-2xl font-semibold">Draft → Review → Dry-run</p>
          <p className="mt-4 leading-7 text-white/70">No cold email is sent automatically. Live email is limited to your own allowlisted inboxes.</p>
        </aside>
      </section>
      <section className="grid gap-5 md:grid-cols-3">
        {highlights.map(([title, detail]) => (
          <article key={title} className="rounded-2xl border border-ink/10 bg-white p-6">
            <h2 className="text-xl font-bold">{title}</h2>
            <p className="mt-3 leading-7 text-ink/70">{detail}</p>
          </article>
        ))}
      </section>
      <p className="rounded-xl bg-lime/40 p-5 text-sm leading-6">
        Privacy warning: Google states that free-tier Gemini content may be used to improve its products. Never submit real customer data.
      </p>
    </div>
  );
}
