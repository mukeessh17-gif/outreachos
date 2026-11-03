# OutreachOS demo script

Use only a workspace seeded with fictional data. Keep `SEND_MODE=dry-run`; do not connect a real prospect address.

1. Start the API, worker, and frontend using the README commands. Sign up to create a workspace.
2. Seed 30 fictional leads: `python -m week4.seed_demo --org-id <your-org-id>`.
3. Open **Leads** and show search/filter, pipeline, and lead research. The seeded sources use the reserved `.example` domain and are not fetched.
4. Queue a writing job only if `GEMINI_API_KEY` is a valid no-billing key. Use fake data only; the free Gemini service may use submitted content to improve Google products.
5. Review and edit drafts in **Approval queue**. Approving a draft does not send it.
6. Add a dry-run inbox in **Settings**, then schedule an approved sequence in **Outbox**. Show that each message is stored and that no email is sent.
7. Show the **Replies**, **Jobs**, **Pipeline**, and **Analytics** pages. Synthetic reply evaluation is available through `python -m week4.evals.reply_eval`.
8. End by showing **Privacy**, data export, and the owner-only workspace deletion control. Do not actually delete a workspace during the demo.

Live Gmail and Stripe flows are optional integrations. Gmail requires a Google Cloud OAuth app in Testing mode and a test-user account; live email also requires an explicit allowlist containing only the owner's own addresses. Stripe stays in TEST mode.
