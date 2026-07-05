# Comments & Feedback — provisioning

Two layers. Layer 1 makes submissions work and moderatable via the Supabase
Table Editor. Layer 2 adds instant email notifications with Approve/Reject links.

## Layer 1 — database + site wiring (do first)
1. Supabase -> SQL Editor -> paste and run `schema.sql`.
2. Supabase -> Project Settings -> API. Copy the **Project URL** and the
   **anon / public** key (both are safe to expose in the browser).
3. In `index_v2.html`, set:  `const SB_URL="...", SB_ANON="...";`
   (or send them to Claude to wire + redeploy).
4. Done: readers can submit; nothing shows until approved. Interim moderation:
   Supabase -> Table Editor -> `comments`, flip `status` pending -> approved.

## Layer 2 — instant email + one-click moderation
Edge Functions are in `functions/notify` and `functions/moderate`.
`SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are injected automatically.

1. Set function secrets (Supabase -> Edge Functions -> Secrets, or CLI):
   - `MOD_SECRET`         = any long random string (signs the approve/reject links)
   - `MODERATOR_EMAIL`    = edgar.ho@meritamerica.org
   - `FROM_EMAIL`         = a verified sender (e.g. onboarding@resend.dev to start)
   - `SITE_URL`           = https://klh-poetry.vercel.app/index_v2.html
   - `RESEND_API_KEY`     = (once you pick a provider; blank = logs instead of sends)
2. Deploy:  `supabase functions deploy notify`  and  `supabase functions deploy moderate`
3. Create Database Webhooks (Supabase -> Database -> Webhooks), one each for
   `comments` and `feedback`, event = INSERT, type = Supabase Edge Function -> `notify`.
4. Test: submit a comment on the live site -> you get an email -> click Approve ->
   comment appears on the page. Reject -> it never shows.

Notes
- No login/usernames anywhere; approval links are unguessable (HMAC-signed).
- Feedback is operator-only (no public read policy); Approve/Reject just marks it reviewed.
- Provider-agnostic: swap Resend for SMTP/another by editing `sendEmail()` in notify.
