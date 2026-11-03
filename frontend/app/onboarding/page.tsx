import Link from "next/link";

export default function OnboardingPage() {
  return (
    <section className="mx-auto max-w-3xl space-y-6 rounded-3xl bg-white p-8">
      <p className="text-sm font-bold uppercase tracking-widest text-moss">Getting started</p>
      <h1 className="text-4xl font-bold">Your workspace is ready.</h1>
      <ol className="list-inside list-decimal space-y-3 leading-7 text-ink/75">
        <li>Use fake or public company information only.</li>
        <li>Add a public company website and review the CSV preview before importing.</li>
        <li>Set your sender postal address and brand voice in Settings.</li>
        <li>Queue research and writing, then review the drafts. Delivery is dry-run by default.</li>
      </ol>
      <div className="flex flex-wrap gap-3">
        <Link href="/dashboard" className="rounded-full bg-moss px-5 py-3 font-semibold text-white">Open leads</Link>
        <Link href="/settings" className="rounded-full border px-5 py-3 font-semibold">Configure settings</Link>
      </div>
    </section>
  );
}
