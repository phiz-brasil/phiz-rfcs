"""A small in-memory stand-in for the Supabase REST API the site talks to, plugged into Playwright with page.route().

It implements what the page uses (comments, replies, hiding, status log and current status) with the same rules the SQL has:
hidden rows are never returned, replies inherit `para` from their parent, hiding a comment hides its replies.
"""
import base64
import binascii
import json
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization,apikey,content-type,x-upsert,prefer,x-client-info,range,accept-profile,content-profile",
        "Access-Control-Allow-Methods": "GET,POST,PATCH,DELETE,OPTIONS"}


def now():
    return datetime.now(timezone.utc).isoformat()


from fake_themes import ThemesMixin  # noqa: E402


class FakeSupabase(ThemesMixin):
    def __init__(self, has_para=True):
        self.has_para = has_para          # False behaves like a database without the `para` column (HTTP 400)
        self.comments = []                # every row, hidden ones included
        self.status_log = []
        self.posts = []                   # bodies received by POST, in order
        self.hides = []                   # ids sent to rpc/hide_rfc_comment
        self.ids = {"PHZ-0001": "repo", "PHZ-0002": "repo"}      # rfc_ids: the sequence shared with the repository
        self.revisions = []               # rfc_revisions of the RFCs created on the site
        self.calls = []                   # (function, body) of every rpc call, in order
        self.rate_limited = False         # make create_rfc / add_rfc_revision answer 429
        self.staging = {}                 # token -> {name: row}: images waiting for their RFC
        self.assets = []                  # rfc_assets rows
        self.auth_calls = []              # (endpoint, body) of every call to /auth/v1: otp, verify, token, user, logout
        self.rest_auth = []               # the Authorization header of every call to the REST API, Storage or Edge Functions (None when absent)
        self.lock = False                 # the member lock of docs/spec/v2/login.md: anon 401, another domain 403, members and /rpc/ping pass
        self.lock_refused = []            # (status, path) of every request the lock refused
        self.tokens = {}                  # access token prefix -> e-mail, for the lock (tests/support.py sign_in_as fills it)
        self.token_status = None          # when set (500, 429…), the refresh answers with that status instead of a session
        self.valid_codes = {"123456"}     # the 6-digit codes the fake Auth accepts
        self.refreshable = {}             # refresh_token -> email: what the fake Auth can refresh
        self.asset_reads = []             # (rfc, name, rev) of every read that carried the bytes (select includes `data`): what costs egress
        self._init_themes()               # fronts, themes, items, links, Jira links, events (fake_themes.py)

    # -- test helpers ---------------------------------------------------
    def add_comment(self, rfc_id, section, author, body, parent_id=None, para=None, **extra):
        row = {"id": str(uuid.uuid4()), "rfc_id": rfc_id, "section": section, "parent_id": parent_id, "author": author,
               "body": body, "quote": None, "lang": "pt", "created_at": now(), "para": para,
               "translations": None, "src_lang": None, "hidden": False}
        row.update(extra)
        self.comments.append(row)
        return row

    def next_id(self, source="site"):
        n = max(int(i[4:]) for i in self.ids) + 1
        new = f"PHZ-{n:04d}"
        self.ids[new] = source
        return new

    def add_revision(self, rfc_id, bundle, meta, authors, collaborators=(), by="Ana", note=None, rev=None, created_at=None):
        """`rev` is given for imported RFCs (version 1.7 is revision 8, with no earlier ones); otherwise the next number, as the SQL does."""
        rev = rev or max([r["rev"] for r in self.revisions if r["rfc_id"] == rfc_id], default=0) + 1
        row = {"id": str(uuid.uuid4()), "rfc_id": rfc_id, "rev": rev, "version": f"1.{rev - 1}", "meta": meta, "bundle": bundle,
               "authors": list(authors), "collaborators": list(collaborators), "edited_by": by, "note": note, "created_at": created_at or now()}
        self.revisions.append(row)
        return row

    def seed_rfc(self, bundle, meta, authors=("Ana",), collaborators=(), images=None):
        """An RFC created on the site, as if create_rfc had run. `images` is {name: PNG bytes} attached to revision 1."""
        rid = self.next_id()
        self.add_revision(rid, bundle, meta, authors, collaborators)
        for name, data in (images or {}).items():
            self.add_asset(rid, name, 1, data)
        return rid

    def add_asset(self, rfc_id, name, rev, data, mime="image/png"):
        self.assets.append({"rfc_id": rfc_id, "name": name, "rev": rev, "mime": mime, "size": len(data),
                            "data": base64.b64encode(data).decode(), "uploaded_by": "Ana", "created_at": now()})

    def current(self, rfc_id=None):
        out = []
        for rid in sorted({r["rfc_id"] for r in self.revisions}, reverse=True):
            if rfc_id and rid != rfc_id:
                continue
            revs = sorted((r for r in self.revisions if r["rfc_id"] == rid), key=lambda r: r["rev"])
            last = revs[-1]
            out.append({k: last[k] for k in ("rfc_id", "rev", "version", "meta", "authors", "collaborators", "edited_by", "created_at")}
                       | {"first_created_at": revs[0]["created_at"]})
        return out

    MAGIC = {"image/png": lambda b: b[:8] == b"\x89PNG\r\n\x1a\n", "image/jpeg": lambda b: b[:3] == b"\xff\xd8\xff",
             "image/webp": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP"}

    def stage_asset(self, body, ok):
        """stage_rfc_asset: the same checks as the SQL function."""
        name, mime = body["p_name"], body["p_mime"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,59}", name or ""):
            return ok({"message": "invalid image name"}, 400)
        if mime not in self.MAGIC:
            return ok({"message": "invalid image type"}, 400)
        try:
            raw = base64.b64decode(body["p_data"], validate=True)
        except (binascii.Error, ValueError):
            return ok({"message": "invalid image data"}, 400)
        if not 1 <= len(raw) <= 1048576:
            return ok({"message": "invalid image size"}, 400)
        if not self.MAGIC[mime](raw):
            return ok({"message": f"file is not a valid {mime}"}, 400)
        staged = self.staging.setdefault(body["p_token"], {})
        if len([n for n in staged if n != name]) >= 160:
            return ok({"message": "too many images"}, 400)
        staged[name] = {"name": name, "mime": mime, "size": len(raw), "data": body["p_data"], "uploaded_by": body["p_by"]}
        return ok(self._empty())

    def finalize_assets(self, rfc_id, rev, bundle, token):
        """rfc_asset_finalize: every image the text cites is staged or already stored for an earlier revision; None when fine."""
        names = sorted(set(re.findall(r"!\[[^\]]*\]\(asset:([a-z0-9][a-z0-9._-]{0,59})", bundle)))
        staged = self.staging.get(token, {}) if token else {}
        for name in names:
            if name not in staged and not any(a["rfc_id"] == rfc_id and a["name"] == name and a["rev"] < rev for a in self.assets):
                return f"missing image {name}"
        for name in names:
            if name in staged:
                s = staged[name]
                self.assets.append({"rfc_id": rfc_id, "name": name, "rev": rev, "mime": s["mime"], "size": s["size"], "data": s["data"],
                                    "uploaded_by": s["uploaded_by"], "created_at": now()})
        self.staging.pop(token, None)
        return None

    def visible(self, rfc_id=None):
        return [c for c in self.comments if not c["hidden"] and (rfc_id is None or c["rfc_id"] == rfc_id)]

    def current_status(self):
        out = {}
        for row in self.status_log:
            out[row["rfc_id"]] = row
        return list(out.values())

    def _empty(self):
        return {"__empty__": True}

    # -- the fake Auth (GoTrue): /auth/v1/otp, /verify, /token, /user, /logout --------------------------
    @staticmethod
    def session_for(email, name=None):
        tok = "tok-" + email.split("@")[0]
        return {"access_token": tok, "refresh_token": "ref-" + email.split("@")[0], "expires_in": 3600, "token_type": "bearer",
                "user": {"id": "u-" + email.split("@")[0], "email": email, "user_metadata": {"name": name} if name else {}}}

    def auth_handle(self, route, req, path, q):
        H = {**CORS, "Content-Type": "application/json"}
        body = json.loads(req.post_data) if req.post_data else {}
        endpoint = path.split("/auth/v1/", 1)[1].strip("/")
        self.auth_calls.append((endpoint, {**body, **({"_q": q} if q else {}), "_auth": req.headers.get("authorization")}))
        if endpoint == "otp":
            return route.fulfill(status=200, headers=H, body="{}")
        if endpoint == "verify":
            if body.get("token") in self.valid_codes and body.get("type") == "email" and body.get("email"):
                sess = self.session_for(body["email"])
                self.refreshable[sess["refresh_token"]] = body["email"]
                return route.fulfill(status=200, headers=H, body=json.dumps(sess))
            return route.fulfill(status=403, headers=H, body=json.dumps({"code": 403, "error_code": "otp_expired", "msg": "Token has expired or is invalid"}))
        if endpoint == "token" and q.get("grant_type") == "refresh_token":
            if self.token_status:
                return route.fulfill(status=self.token_status, headers=H, body=json.dumps({"msg": "unavailable"}))
            email = self.refreshable.get(body.get("refresh_token"))
            if not email:
                return route.fulfill(status=400, headers=H, body=json.dumps({"error": "invalid_grant", "error_description": "Invalid Refresh Token"}))
            sess = self.session_for(email)
            sess["access_token"] += "-r"                                     # a new access token
            return route.fulfill(status=200, headers=H, body=json.dumps(sess))
        if endpoint == "user":
            tok = (req.headers.get("authorization") or "").replace("Bearer ", "")
            email = next((e for r, e in self.refreshable.items() if tok.startswith("tok-" + e.split("@")[0])), None)
            if not email:
                return route.fulfill(status=401, headers=H, body=json.dumps({"msg": "invalid JWT"}))
            return route.fulfill(status=200, headers=H, body=json.dumps(self.session_for(email)["user"]))
        if endpoint == "logout":
            return route.fulfill(status=204, headers=CORS, body="")
        return route.fulfill(status=404, headers=H, body="{}")

    # -- Playwright route -----------------------------------------------
    def gate(self, token, path):
        """What check_request() answers for a request with this bearer token: 200, 401 (no session) or 403 (not a member)."""
        if path.endswith("/rpc/ping"):
            return 200
        who = (token or "").replace("Bearer ", "")
        email = next((e for t, e in self.tokens.items() if who and who.startswith(t)), None)
        if not who or email is None:
            return 401
        return 200 if re.fullmatch(r"[^@]+@phizchat\.com", email, re.I) else 403

    def handle(self, route):
        req = route.request
        url = urlparse(req.url)
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=CORS)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        path = url.path
        if any(x in path for x in ("/rest/v1/", "/storage/v1/", "/functions/v1/")):
            self.rest_auth.append(req.headers.get("authorization"))
            if path.endswith("/rest/v1/rpc/ping"):
                return route.fulfill(status=200, headers={**CORS, "Content-Type": "application/json"}, body="true")
            if self.lock:
                code = self.gate(req.headers.get("authorization"), path)
                if code != 200:
                    self.lock_refused.append((code, path))
                    return route.fulfill(status=code, headers={**CORS, "Content-Type": "application/json"},
                                         body=json.dumps({"code": f"PT{code}", "message": "sign in with a @phizchat.com account" if code == 401 else "only @phizchat.com accounts have access"}))
        if "/auth/v1/" in path:
            return self.auth_handle(route, req, path, q)
        if "/storage/v1/object/" in path:
            return self.storage_handle(route, req, url)
        if path.endswith("/functions/v1/suggest-summary"):
            return self.suggest_function(route, json.loads(req.post_data) if req.post_data else {}, CORS)
        if path.endswith("/functions/v1/plan-deck"):
            return self.plan_function(route, json.loads(req.post_data) if req.post_data else {}, CORS)
        body = json.loads(req.post_data) if req.post_data else None

        def ok(data, status=200):
            if isinstance(data, dict) and data.get("__empty__"):
                return route.fulfill(status=204, headers=CORS)
            route.fulfill(status=status, headers={**CORS, "Content-Type": "application/json"}, body=json.dumps(data))

        if self.themes_handle(path, q, body, ok):
            return
        if path.endswith("/rest/v1/rfc_comments") and req.method == "GET":
            if not self.has_para and "para" in q.get("select", ""):
                return ok({"message": "column rfc_comments.para does not exist"}, 400)
            rows = self.visible(q["rfc_id"].split("eq.")[1] if "rfc_id" in q else None)
            return ok([{k: v for k, v in r.items() if k != "hidden"} for r in rows])
        if path.endswith("/rest/v1/rfc_comments") and req.method == "POST":
            self.posts.append(body)
            parent = next((c for c in self.comments if c["id"] == body.get("parent_id")), None)
            row = self.add_comment(body["rfc_id"], body["section"], body["author"], body["body"], body.get("parent_id"),
                                   parent["para"] if parent else body.get("para"), quote=body.get("quote"), lang=body.get("lang", "pt"))
            return ok([{k: v for k, v in row.items() if k != "hidden"}], 201)
        if path.endswith("/rpc/hide_rfc_comment"):
            self.hides.append(body["p_id"])
            for c in self.comments:
                if c["id"] == body["p_id"] or c["parent_id"] == body["p_id"]:
                    c["hidden"] = True
            return route.fulfill(status=204, headers=CORS)
        if path.endswith("/rest/v1/rfc_status_current"):
            rows = self.current_status()
            if "rfc_id" in q:
                rows = [r for r in rows if r["rfc_id"] == q["rfc_id"].split("eq.")[1]]
            return ok(rows)
        if path.endswith("/rest/v1/rfc_status_log") and req.method == "POST":
            self.posts.append(body)
            self.status_log.append({**body, "created_at": now()})
            return route.fulfill(status=201, headers=CORS)
        eq = lambda key: q[key].split("eq.", 1)[1] if key in q and q[key].startswith("eq.") else None
        if path.endswith("/rest/v1/rfc_live_current"):
            return ok(self.current(eq("rfc_id")))
        if path.endswith("/rest/v1/rfc_live_revisions"):
            rows = [{k: r[k] for k in ("rfc_id", "rev", "version", "edited_by", "note", "created_at")} for r in self.revisions if r["rfc_id"] == eq("rfc_id")]
            return ok(sorted(rows, key=lambda r: r["rev"], reverse=True))
        if path.endswith("/rest/v1/rfc_revisions"):
            granted = {"id", "rfc_id", "rev", "version", "meta", "bundle", "authors", "collaborators", "edited_by", "note", "created_at"}
            wanted = set(q.get("select", "*").split(","))
            if not wanted <= granted:                                           # column grants: `*` includes ip_hash, which the public key cannot read
                return ok({"code": "42501", "message": "permission denied for table rfc_revisions"}, 401)
            rows = [r for r in self.revisions if r["rfc_id"] == eq("rfc_id") and (eq("version") is None or r["version"] == eq("version"))]
            rows = sorted(rows, key=lambda r: r["rev"], reverse=q.get("order", "").endswith("desc"))
            return ok(rows[:int(q["limit"])] if "limit" in q else rows)
        if "/rpc/" in path:
            fn = path.rsplit("/", 1)[1]
            self.calls.append((fn, body))
            if fn == "reserve_rfc_id":
                return ok(self.next_id("repo"))
            if fn == "stage_rfc_asset":
                return self.stage_asset(body, ok)
            if fn in ("create_rfc", "add_rfc_revision"):
                if self.rate_limited:
                    return ok({"message": "rate limit"}, 429)
                for lang in ("pt", "en", "zh"):                                  # what rfc_check_input enforces
                    if lang not in body["p_meta"].get("title", {}) or f"lang:{lang}" not in body["p_bundle"].replace(" ", ""):
                        return ok({"message": f"invalid meta.title.{lang}"}, 400)
                if fn == "create_rfc":
                    rid, rev = self.next_id("site"), 1
                else:
                    rid = body["p_rfc_id"]
                    if self.ids.get(rid) != "site":
                        return ok({"message": "unknown RFC"}, 400)
                    rev = max([r["rev"] for r in self.revisions if r["rfc_id"] == rid], default=0) + 1
                problem = self.finalize_assets(rid, rev, body["p_bundle"], body.get("p_token"))
                if problem:
                    if fn == "create_rfc":
                        del self.ids[rid]
                    return ok({"message": problem}, 400)
                if fn == "create_rfc":
                    self.add_revision(rid, body["p_bundle"], body["p_meta"], body["p_authors"], body["p_collaborators"], body["p_by"])
                    return ok({"rfc_id": rid, "version": "1.0"})
                row = self.add_revision(rid, body["p_bundle"], body["p_meta"], body["p_authors"], body["p_collaborators"], body["p_by"], body.get("p_note"))
                return ok({"rfc_id": row["rfc_id"], "version": row["version"]})
        if path.endswith("/rest/v1/rfc_assets"):
            rows = [a for a in self.assets if a["rfc_id"] == eq("rfc_id") and (eq("name") is None or a["name"] == eq("name"))]
            if q.get("rev", "").startswith("lte."):
                rows = [a for a in rows if a["rev"] <= int(q["rev"][4:])]
            if q.get("rev", "").startswith("eq."):
                rows = [a for a in rows if a["rev"] == int(q["rev"][3:])]
            rows = sorted(rows, key=lambda a: a["rev"], reverse=True)
            if "limit" in q:
                rows = rows[:int(q["limit"])]
            cols = q.get("select", "*").split(",")
            if "data" in cols or cols == ["*"]:
                self.asset_reads += [(a["rfc_id"], a["name"], a["rev"]) for a in rows]
            return ok([a if cols == ["*"] else {k: a[k] for k in cols} for a in rows])
        route.fulfill(status=404, headers=CORS, body="not found")
