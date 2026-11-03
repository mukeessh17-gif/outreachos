# OutreachOS beta case-study draft

> **Synthetic demo only:** This draft uses fictional seed data and offline evaluations. It is not a customer story, and no email was sent. Replace it only with results measured with permission from a real beta user.

## Headline

An early OutreachOS prototype improved its offline outreach-generation score from 4.0/5 to 5.0/5 on a 30-lead fictional evaluation set.

## What was measured

- **Prompt evaluation:** Version 1 averaged 4.0/5 and version 2 averaged 5.0/5 across 30 fictional leads. The weakest version-1 case improved from 4/5 to 5/5 after one targeted prompt iteration.
- **Reply classification:** 96 of 100 fictional replies were classified correctly (96%). All four misses were expected “interested” replies classified as “other.”
- **Demo pipeline:** The deterministic seed creates 30 fictional leads, 6 labeled “Meeting,” and no sent messages or replies. These are sample labels only—not real meetings or outreach outcomes.
- **Local load test:** 20 simulated users made 1,768 authenticated API requests over 30 seconds with 0 failures (60.21 requests/second). Aggregate average response time was 9 ms, p95 was 22 ms, p99 was 46 ms, and maximum was 92 ms. This ran against a disposable local SQLite database and should not be extrapolated to hosted Postgres.
- **Cost:** No paid API was called for these measurements. The dashboard's current `$0` cost-per-lead value is a placeholder for this no-send/no-LLM demo, not a cost or margin claim.

## Draft narrative

OutreachOS is an early B2B sales-outreach prototype built around tenant-scoped lead management, evidence-grounded research, and human-approved drafts. On a small, synthetic evaluation set, a prompt revision raised the mean draft-quality score from 4.0/5 to 5.0/5. A separate fake-reply benchmark reached 96% accuracy. A short local API exercise completed 1,768 requests without failures.

These results show that the evaluation and demo workflows run end-to-end; they do not establish production performance, customer impact, deliverability, or revenue. The next beta phase should measure those outcomes using consented, non-sensitive data and owner-controlled inboxes.
