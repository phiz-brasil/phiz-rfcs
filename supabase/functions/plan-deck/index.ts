// "Describe the material" of the export (docs/spec/v2/redesign.md, What PR 3 delivers): reads the active themes, asks the model that writes the
// suggestions (Cloudflare Workers AI, CF_SUGGEST_MODEL) for a deck plan and answers it. It writes nothing; the page keeps only what it can trace to a theme.
//
// Called from the browser with the public key:  POST {"request": "...", "lang": "pt", "by": "Ana"}  (deploy with "Verify JWT" off: the key is not a JWT).
// Secrets: CF_ACCOUNT_ID, CF_API_TOKEN (permission "Workers AI"), optional CF_SUGGEST_MODEL. SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are provided.
// With the secret REQUIRE_MEMBER=1 it refuses anyone who is not signed in with a @phizchat.com account (401/403).
// Limits: a request of at most 600 characters; 20 plans an hour per running instance. Deployed only when the owner says.
import { createClient } from "jsr:@supabase/supabase-js@2";
import { buildPrompt, MAX_REQUEST, memberEmail, parseModelJson, type Context } from "./plan.ts";

const ACCOUNT = Deno.env.get("CF_ACCOUNT_ID") ?? "";
const TOKEN = Deno.env.get("CF_API_TOKEN") ?? "";
const MODEL = Deno.env.get("CF_SUGGEST_MODEL") ?? "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
const ENDPOINT = `https://api.cloudflare.com/client/v4/accounts/${ACCOUNT}/ai/run/${MODEL}`;
const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "POST, OPTIONS" };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json" } });
const runs: number[] = [];

async function gather(): Promise<Context> {
  const { data: themes } = await db.from("themes").select("id,front,title,what_it_is,progress,status,start_date,due_date,owner")
    .eq("hidden", false).not("status", "in", "(done,cancelled)").order("id").limit(150);
  const ids = (themes ?? []).map((t) => t.id);
  if (!ids.length) return { themes: [], blockers: [], decisions: [], milestones: [] };
  const [b, d, m] = await Promise.all([
    db.from("theme_blockers").select("theme_id,what,urgency,due_date,needs_leadership").eq("state", "open").in("theme_id", ids),
    db.from("theme_decisions").select("theme_id,what,urgency,due_date,needs_leadership").eq("state", "open").in("theme_id", ids),
    db.from("theme_items").select("theme_id,title,due_date").eq("milestone", true).neq("col", "done").in("theme_id", ids),
  ]);
  return { themes: themes ?? [], blockers: b.data ?? [], decisions: d.data ?? [], milestones: m.data ?? [] };
}

async function ask(system: string, user: string): Promise<unknown> {
  const r = await fetch(ENDPOINT, {
    method: "POST",
    headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify({ messages: [{ role: "system", content: system }, { role: "user", content: user }], max_tokens: 2000, temperature: 0.1 }),
  });
  const j = await r.json().catch(() => null);
  if (!r.ok || j?.success === false) throw new Error(`Workers AI ${r.status}: ${JSON.stringify(j?.errors ?? j)}`);
  return j?.result?.response ?? j?.response;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
  if (req.method !== "POST") return json({ error: "method not allowed" }, 405);
  if (!ACCOUNT || !TOKEN) return json({ error: "CF_ACCOUNT_ID / CF_API_TOKEN are not set" }, 500);
  if (Deno.env.get("REQUIRE_MEMBER") === "1") {
    const token = (req.headers.get("authorization") ?? "").replace(/^Bearer\s+/i, "");
    const { data } = token ? await db.auth.getUser(token) : { data: { user: null } };
    if (!data.user) return json({ error: "sign in" }, 401);
    if (!memberEmail(data.user.email)) return json({ error: "only @phizchat.com accounts" }, 403);
  }
  const body = await req.json().catch(() => ({}));
  const request = String(body.request ?? "").trim(), lang = ["pt", "en", "zh"].includes(body.lang) ? body.lang : "pt";
  if (!request || request.length > MAX_REQUEST) return json({ error: "invalid request" }, 400);
  const now = Date.now();
  while (runs.length && runs[0] < now - 3_600_000) runs.shift();
  if (runs.length >= 20) return json({ error: "rate limit" }, 429);
  runs.push(now);
  try {
    const context = await gather();
    if (!context.themes.length) return json({ plan: { title: "", slides: [] } });
    const { system, user } = buildPrompt(request, lang, context);
    return json({ plan: parseModelJson(await ask(system, user)) });
  } catch (e) {
    console.error(e);
    return json({ error: "model failed" }, 502);
  }
});
