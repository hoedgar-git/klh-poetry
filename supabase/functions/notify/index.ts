// Supabase Edge Function: "notify"
// Fires on INSERT into comments/feedback (via a Database Webhook) and emails the
// operator immediately with signed Approve/Reject links. Provider-agnostic:
// set RESEND_API_KEY to send via Resend; otherwise it logs the email (safe no-op).
const enc = new TextEncoder();
async function sign(msg: string): Promise<string> {
  const key = await crypto.subtle.importKey("raw", enc.encode(Deno.env.get("MOD_SECRET") || ""),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(msg));
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, "0")).join("");
}
async function sendEmail(subject: string, html: string) {
  const to = Deno.env.get("MODERATOR_EMAIL");
  const from = Deno.env.get("FROM_EMAIL") || "onboarding@resend.dev";
  const rk = Deno.env.get("RESEND_API_KEY");
  if (!rk || !to) { console.log("EMAIL (no provider/recipient set):", subject, html); return; }
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { "Authorization": `Bearer ${rk}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from, to, subject, html }),
  });
  if (!r.ok) console.error("email send failed", await r.text());
}
Deno.serve(async (req) => {
  const payload = await req.json().catch(() => ({}));
  const rec = payload.record, table = payload.table;
  if (!rec || !["comments", "feedback"].includes(table)) return new Response("ignored");
  const base = `${Deno.env.get("SUPABASE_URL")}/functions/v1/moderate`;
  const link = async (a: string) =>
    `${base}?t=${table}&id=${rec.id}&a=${a}&sig=${await sign(`${table}:${rec.id}:${a}`)}`;
  const approve = await link("approve"), reject = await link("reject");
  const ctx = table === "comments"
    ? (rec.scope === "guestbook" ? "Guestbook comment" : `Comment on ${rec.page_id}`)
    : `Feedback (page: ${rec.page_id || "—"})`;
  const html = `<p><b>New ${table}</b> — ${ctx}</p>
    <blockquote style="border-left:3px solid #ccc;padding:4px 12px;color:#333">${(rec.body || "").replace(/</g, "&lt;")}</blockquote>
    <p><a href="${approve}">&#10003; Approve &amp; publish</a> &nbsp;|&nbsp; <a href="${reject}">&#10007; Reject</a></p>`;
  await sendEmail(`KLH Poetry — new ${table}`, html);
  return new Response("ok");
});
