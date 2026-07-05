// Supabase Edge Function: "moderate"
// Handles the one-click Approve/Reject links from the notification email.
// No login: the link carries an unguessable HMAC signature scoped to row+action.
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
const enc = new TextEncoder();
async function sign(msg: string): Promise<string> {
  const key = await crypto.subtle.importKey("raw", enc.encode(Deno.env.get("MOD_SECRET") || ""),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const s = await crypto.subtle.sign("HMAC", key, enc.encode(msg));
  return [...new Uint8Array(s)].map(b => b.toString(16).padStart(2, "0")).join("");
}
function page(msg: string) {
  const back = Deno.env.get("SITE_URL") || "/";
  return new Response(
    `<html><body style="font-family:system-ui,sans-serif;text-align:center;padding:3rem">
     <h2>${msg}</h2><p><a href="${back}">Back to site</a></p></body></html>`,
    { headers: { "Content-Type": "text/html" } });
}
Deno.serve(async (req) => {
  const u = new URL(req.url);
  const t = u.searchParams.get("t") || "", id = u.searchParams.get("id") || "",
        a = u.searchParams.get("a") || "", sig = u.searchParams.get("sig") || "";
  if (!["comments", "feedback"].includes(t) || !id || !["approve", "reject"].includes(a))
    return page("Invalid request.");
  if (sig !== await sign(`${t}:${id}:${a}`)) return page("Invalid or expired link.");
  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const status = t === "feedback" ? "reviewed" : (a === "approve" ? "approved" : "rejected");
  const patch: Record<string, unknown> = { status };
  if (t === "comments" && a === "approve") patch.approved_at = new Date().toISOString();
  const { error } = await sb.from(t).update(patch).eq("id", id);
  return page(error ? `Error: ${error.message}` : `Done — ${t} #${id} is now &ldquo;${status}&rdquo;.`);
});
