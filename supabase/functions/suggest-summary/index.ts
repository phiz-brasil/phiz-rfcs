// "Suggest with AI" for a theme: reads the theme's RFC, notes, text attachments and recent weekly updates, asks a model (Cloudflare Workers AI, the same
// account the translation uses) for the three slide answers and returns only what the documents support, each with the quotations that prove it.
// It writes nothing about the answers: the page shows the suggestion and a person confirms or edits it (the RPC suggest_theme_answers stores it).
//
// Called from the browser with the public key:  POST {"theme": "PHZ-0001", "by": "Ana"}  (deploy with "Verify JWT" off: the key is not a JWT).
// Secrets: CF_ACCOUNT_ID, CF_API_TOKEN (permission "Workers AI"), optional CF_SUGGEST_MODEL. SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are provided.
// Limits: 3 runs an hour per theme and 40 an hour in all (counted in theme_events as 'ai_suggest').
import { createClient } from "jsr:@supabase/supabase-js@2";
import { buildPrompt, buildSources, parseModelJson, type Raw, validate } from "./suggest.ts";

const ACCOUNT = Deno.env.get("CF_ACCOUNT_ID") ?? "";
const TOKEN = Deno.env.get("CF_API_TOKEN") ?? "";
const MODEL = Deno.env.get("CF_SUGGEST_MODEL") ?? "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
const ENDPOINT = `https://api.cloudflare.com/client/v4/accounts/${ACCOUNT}/ai/run/${MODEL}`;
const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "POST, OPTIONS" };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json" } });
const TEXT_NAME = /\.(md|markdown|txt|csv|json|yaml|yml)$/i;

async function gather(theme: string): Promise<Raw | null> {
  const { data: t } = await db.from("themes").select("id,title,what_it_is,progress,hidden").eq("id", theme).maybeSingle();
  if (!t || t.hidden) return null;
  const [rev, atts, ups] = await Promise.all([
    db.from("rfc_revisions").select("bundle").eq("rfc_id", theme).order("rev", { ascending: false }).limit(1),
    db.from("attachments").select("kind,name,body,storage_path,content_type,size").eq("theme_id", theme).eq("hidden", false).order("created_at", { ascending: false }).limit(60),
    db.from("theme_updates").select("week,progress,advanced,next_step").eq("theme_id", theme).order("created_at", { ascending: false }).limit(6),
  ]);
  const rows = atts.data ?? [];
  const files: { name: string; text: string }[] = [];
  for (const a of rows.filter((x) => x.kind === "file" && x.storage_path && (x.size ?? 0) <= 300_000 && !/html/i.test(x.content_type ?? "")
                                       && (/^text\//.test(x.content_type ?? "") || TEXT_NAME.test(x.name))).slice(0, 8)) {
    const { data } = await db.storage.from("attachments").download(a.storage_path!);
    if (data) files.push({ name: a.name, text: await data.text() });
  }
  return {
    rfcBundle: rev.data?.[0]?.bundle ?? null,
    notes: rows.filter((x) => x.kind === "note" && x.body).map((x) => ({ name: x.name, body: x.body! })),
    files,
    updates: ups.data ?? [],
    theme: { title: t.title, what_it_is: t.what_it_is, progress: t.progress },
  };
}

async function ask(system: string, user: string): Promise<unknown> {
  const r = await fetch(ENDPOINT, {
    method: "POST",
    headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify({ messages: [{ role: "system", content: system }, { role: "user", content: user }], max_tokens: 1800, temperature: 0.1 }),
  });
  const j = await r.json().catch(() => null);
  if (!r.ok || j?.success === false) throw new Error(`Workers AI ${r.status}: ${JSON.stringify(j?.errors ?? j)}`);
  return j?.result?.response ?? j?.response;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
  if (req.method !== "POST") return json({ error: "method not allowed" }, 405);
  if (!ACCOUNT || !TOKEN) return json({ error: "CF_ACCOUNT_ID / CF_API_TOKEN are not set" }, 500);
  const body = await req.json().catch(() => ({}));
  const theme = String(body.theme ?? ""), by = String(body.by ?? "").trim();
  if (!/^PHZ-\d{4}$/.test(theme)) return json({ error: "invalid theme" }, 400);
  if (by.length < 1 || by.length > 60) return json({ error: "invalid name" }, 400);
  try {
    const since = new Date(Date.now() - 3_600_000).toISOString();
    const [mine, all] = await Promise.all([
      db.from("theme_events").select("id", { count: "exact", head: true }).eq("field", "ai_suggest").eq("theme_id", theme).gte("at", since),
      db.from("theme_events").select("id", { count: "exact", head: true }).eq("field", "ai_suggest").gte("at", since),
    ]);
    if ((mine.count ?? 0) >= 3 || (all.count ?? 0) >= 40) return json({ error: "rate limit" }, 429);
    const raw = await gather(theme);
    if (!raw) return json({ error: "unknown theme" }, 404);
    const sources = buildSources(raw);
    await db.from("theme_events").insert({ theme_id: theme, edited_by: by, field: "ai_suggest", new_value: { sources: sources.length } });
    if (!sources.length) return json({ suggestions: validate(null, []), sources: [] });          // nothing to read: every answer stays missing
    const { system, user } = buildPrompt(String(raw.theme.title?.pt ?? raw.theme.title?.en ?? raw.theme.title?.zh ?? theme), sources);
    const parsed = parseModelJson(await ask(system, user));
    return json({ suggestions: validate(parsed, sources), sources: sources.map(({ id, label }) => ({ id, label })) });
  } catch (e) {
    console.error(e);
    return json({ error: "model failed" }, 502);
  }
});
