"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function SignupPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          email: form.get("email"),
          password: form.get("password"),
          org_name: form.get("org_name"),
        }),
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail ?? "Signup failed.");
      }
      router.push("/onboarding");
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Signup failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-md rounded-3xl bg-white p-8 shadow-sm">
      <h1 className="text-3xl font-bold">Create your workspace</h1>
      <form className="mt-6 space-y-4" onSubmit={submit}>
        <label className="block text-sm font-semibold">Workspace name
          <input required minLength={2} maxLength={100} name="org_name" className="mt-1 w-full rounded-lg border p-3" />
        </label>
        <label className="block text-sm font-semibold">Email
          <input required type="email" name="email" autoComplete="email" className="mt-1 w-full rounded-lg border p-3" />
        </label>
        <label className="block text-sm font-semibold">Password (at least 12 characters)
          <input required minLength={12} maxLength={128} type="password" name="password" autoComplete="new-password" className="mt-1 w-full rounded-lg border p-3" />
        </label>
        {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
        <button disabled={loading} className="w-full rounded-full bg-moss px-5 py-3 font-semibold text-white">{loading ? "Creating…" : "Create workspace"}</button>
      </form>
      <p className="mt-5 text-sm text-ink/70">Already have an account? <Link href="/login" className="underline">Sign in</Link></p>
    </section>
  );
}
