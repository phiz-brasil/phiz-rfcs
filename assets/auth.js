/* Sign-in for every page (docs/spec/v2/login.md). A classic script, loaded first, configured by data- attributes of its own tag:
     data-url      the Supabase address          data-key       the publishable key
     data-required "1" when the switch is on (site.config.json auth.required): a page without a session goes to /login/
   It defines window.PHIZ_AUTH, keeps the session fresh and wraps window.fetch: any request to the Supabase address (REST, Storage, Edge Functions — never /auth/v1/)
   leaves with `Authorization: Bearer <access token>` when there is a session, so no request site of the old or the new pages needs to know about it.
   The session lives in localStorage ("phiz-auth": access_token, refresh_token, expires_at in seconds, user); the account name also goes to "phiz-rfc-author",
   where the old pages already look for the name they write with. */
(function () {
  "use strict";
  const tag = document.currentScript;
  const URL_ = ((tag && tag.dataset.url) || "").replace(/\/+$/, "");
  const KEY = (tag && tag.dataset.key) || "";
  const STORE = "phiz-auth", NAME_KEY = "phiz-rfc-author", STRICT_KEY = "phiz-auth-required";
  const DOMAIN = /@phiz\.com$/i;
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* blocked */ } },
    del(k) { try { localStorage.removeItem(k); } catch (e) { /* blocked */ } },
  };
  const required = () => (tag && tag.dataset.required === "1") || store.get(STRICT_KEY) === "1";
  const member = email => DOMAIN.test(String(email || "").trim());

  function session() {
    try { const s = JSON.parse(store.get(STORE) || "null"); return s && s.access_token && s.refresh_token ? s : null; } catch (e) { return null; }
  }
  /* "ana.souza@phiz.com" -> "Ana Souza"; a name in the account wins */
  function nameOf(s) {
    if (!s || !s.user) return null;
    const n = s.user.user_metadata && (s.user.user_metadata.name || s.user.user_metadata.full_name);
    if (n && String(n).trim()) return String(n).trim();
    return String(s.user.email || "").split("@")[0].split(/[._-]+/).filter(Boolean).map(w => w[0].toUpperCase() + w.slice(1)).join(" ") || null;
  }
  function remember(s) {
    store.set(STORE, JSON.stringify(s));
    const n = nameOf(s);
    if (n) store.set(NAME_KEY, n);
  }
  function fromResponse(j) {
    const exp = j.expires_at || Math.floor(Date.now() / 1000) + (Number(j.expires_in) || 3600);
    return { access_token: j.access_token, refresh_token: j.refresh_token, expires_at: exp, user: j.user || null };
  }
  function leave() {
    store.del(STORE);
    if (required() && !/^\/login\//.test(location.pathname)) goLogin();
  }
  function goLogin(extra) {
    const next = location.pathname + location.search + location.hash;
    location.replace("/login/?next=" + encodeURIComponent(next) + (extra || ""));
  }

  const realFetch = window.fetch.bind(window);
  const authFetch = (path, opts) => realFetch(URL_ + "/auth/v1/" + path, Object.assign({}, opts, { headers: Object.assign({ apikey: KEY, "Content-Type": "application/json" }, (opts && opts.headers) || {}) }));

  let refreshing = null;
  function refresh() {
    if (!refreshing) {
      refreshing = (async () => {
        const s = session();
        if (!s) return null;
        try {
          const r = await authFetch("token?grant_type=refresh_token", { method: "POST", body: JSON.stringify({ refresh_token: s.refresh_token }) });
          if (!r.ok) { leave(); return null; }
          const next = fromResponse(await r.json());
          if (!next.user) next.user = s.user;
          remember(next);
          return next;
        } catch (e) { return session(); }                       // offline: keep what there is, the request will fail on its own
      })().finally(() => { refreshing = null; });
    }
    return refreshing;
  }
  async function accessToken() {
    let s = session();
    if (!s) return null;
    if (s.expires_at * 1000 - Date.now() < 60000) s = await refresh();
    return s ? s.access_token : null;
  }

  if (URL_) {
    window.fetch = async function (input, init) {
      const url = typeof input === "string" ? input : (input && input.url) || String(input);
      if (url.startsWith(URL_ + "/") && !url.startsWith(URL_ + "/auth/v1/")) {
        const token = await accessToken();
        if (token) {
          const h = new Headers((init && init.headers) || (typeof input !== "string" && input.headers) || undefined);
          h.set("Authorization", "Bearer " + token);
          init = Object.assign({}, init, { headers: h });
        }
      }
      return realFetch(input, init);
    };
  }

  const api = {
    required, member, nameOf,
    session,
    account() { const s = session(); return s && s.user ? { email: s.user.email, name: nameOf(s) } : null; },
    name() { return nameOf(session()); },
    /* asks Supabase to send the link and the code */
    async sendLink(email) {
      const r = await authFetch("otp?redirect_to=" + encodeURIComponent(location.origin + "/login/"), { method: "POST", body: JSON.stringify({ email, create_user: true }) });
      if (!r.ok) throw new Error("otp " + r.status);
    },
    /* the 6-digit code of the same message */
    async verify(email, token) {
      const r = await authFetch("verify", { method: "POST", body: JSON.stringify({ type: "email", email, token }) });
      if (!r.ok) throw new Error("verify " + r.status);
      return finish(fromResponse(await r.json()));
    },
    /* the link: the tokens come back in the address (#access_token=…); returns the session, or null when the address has none */
    async fromAddress() {
      const h = new URLSearchParams(location.hash.replace(/^#/, ""));
      if (!h.get("access_token") || !h.get("refresh_token")) return null;
      const s = fromResponse({ access_token: h.get("access_token"), refresh_token: h.get("refresh_token"), expires_in: h.get("expires_in") });
      history.replaceState(null, "", location.pathname + location.search);
      const r = await authFetch("user", { headers: { Authorization: "Bearer " + s.access_token } });
      if (!r.ok) throw new Error("user " + r.status);
      s.user = await r.json();
      return finish(s);
    },
    async signOut() {
      const s = session();
      store.del(STORE);
      if (s) { try { await authFetch("logout", { method: "POST", headers: { Authorization: "Bearer " + s.access_token } }); } catch (e) { /* the session is gone here anyway */ } }
    },
    /* only paths of this site (never another address) */
    nextPath(raw) { return typeof raw === "string" && /^\/(?![/\\])/.test(raw) ? raw : "/overview/"; },
  };
  function finish(s) {
    if (!member(s.user && s.user.email)) { const e = new Error("not a member"); e.notMember = true; throw e; }
    remember(s);
    return s;
  }
  window.PHIZ_AUTH = api;

  // what happens when the page loads: keep the name the old pages use, guard, show the account
  const s0 = session();
  if (s0) {
    if (!member(s0.user && s0.user.email)) { store.del(STORE); } else { const n = nameOf(s0); if (n) store.set(NAME_KEY, n); }
  }
  if (required() && !session() && !/^\/login\//.test(location.pathname)) goLogin();

  const WORDS = { pt: "Sair", en: "Sign out", zh: "退出" };
  function slot() {
    const el = document.querySelector("[data-auth-slot]");
    const a = api.account();
    if (!el || !a) return;
    const lang = document.documentElement.dataset.lang || "pt";
    el.innerHTML = "";
    const who = document.createElement("span");
    who.className = "acct";
    who.textContent = a.email;
    const out = document.createElement("button");
    out.type = "button";
    out.className = "navc";
    out.textContent = WORDS[lang] || WORDS.pt;
    out.addEventListener("click", async () => { await api.signOut(); location.href = "/login/"; });
    el.append(who, out);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", slot); else slot();
})();
