import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "OutreachOS",
  description: "Evidence-based B2B outreach drafts with human approval.",
};

const links = [
  ["Leads", "/dashboard"],
  ["Approvals", "/approvals"],
  ["Replies", "/replies"],
  ["Outbox", "/outbox"],
  ["Pipeline", "/pipeline"],
  ["Analytics", "/analytics"],
  ["Jobs", "/jobs"],
  ["Settings", "/settings"],
];

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-ink/10 bg-white">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-4">
            <Link href="/" className="text-xl font-bold tracking-tight text-moss">OutreachOS</Link>
            <nav className="flex flex-wrap gap-4 text-sm text-ink/70">
              {links.map(([label, href]) => <Link key={href} href={href} className="hover:text-moss">{label}</Link>)}
              <Link href="/login" className="font-semibold text-moss">Sign in</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto min-h-[75vh] max-w-7xl px-6 py-10">{children}</main>
        <footer className="border-t border-ink/10 px-6 py-6 text-center text-sm text-ink/60">
          Use only fake or public business information. Free Gemini inputs may be used to improve Google products.
          <span className="mx-2">·</span><Link href="/privacy" className="underline">Privacy</Link>
        </footer>
      </body>
    </html>
  );
}
