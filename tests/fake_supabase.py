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

CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "GET,POST,OPTIONS"}


def now():
    return datetime.now(timezone.utc).isoformat()


class FakeSupabase:
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

    # -- Playwright route -----------------------------------------------
    def handle(self, route):
        req = route.request
        url = urlparse(req.url)
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=CORS)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        path = url.path
        body = json.loads(req.post_data) if req.post_data else None

        def ok(data, status=200):
            if isinstance(data, dict) and data.get("__empty__"):
                return route.fulfill(status=204, headers=CORS)
            route.fulfill(status=status, headers={**CORS, "Content-Type": "application/json"}, body=json.dumps(data))

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
            rows = sorted(rows, key=lambda a: a["rev"], reverse=True)
            if "limit" in q:
                rows = rows[:int(q["limit"])]
            cols = q.get("select", "*").split(",")
            return ok([a if cols == ["*"] else {k: a[k] for k in cols} for a in rows])
        route.fulfill(status=404, headers=CORS, body="not found")
