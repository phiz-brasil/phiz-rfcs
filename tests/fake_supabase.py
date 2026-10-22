"""A small in-memory stand-in for the Supabase REST API the site talks to, plugged into Playwright with page.route().

It implements what the page uses (comments, replies, hiding, status log and current status) with the same rules the SQL has:
hidden rows are never returned, replies inherit `para` from their parent, hiding a comment hides its replies.
"""
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

    def add_revision(self, rfc_id, bundle, meta, authors, collaborators=(), by="Ana", note=None):
        rev = len([r for r in self.revisions if r["rfc_id"] == rfc_id]) + 1
        row = {"id": str(uuid.uuid4()), "rfc_id": rfc_id, "rev": rev, "version": f"1.{rev - 1}", "meta": meta, "bundle": bundle,
               "authors": list(authors), "collaborators": list(collaborators), "edited_by": by, "note": note, "created_at": now()}
        self.revisions.append(row)
        return row

    def seed_rfc(self, bundle, meta, authors=("Ana",), collaborators=()):
        """An RFC created on the site, as if create_rfc had run."""
        rid = self.next_id()
        self.add_revision(rid, bundle, meta, authors, collaborators)
        return rid

    def current(self, rfc_id=None):
        out = []
        for rid in sorted({r["rfc_id"] for r in self.revisions}, reverse=True):
            if rfc_id and rid != rfc_id:
                continue
            revs = [r for r in self.revisions if r["rfc_id"] == rid]
            last = revs[-1]
            out.append({k: last[k] for k in ("rfc_id", "rev", "version", "meta", "authors", "collaborators", "edited_by", "created_at")}
                       | {"first_created_at": revs[0]["created_at"]})
        return out

    def visible(self, rfc_id=None):
        return [c for c in self.comments if not c["hidden"] and (rfc_id is None or c["rfc_id"] == rfc_id)]

    def current_status(self):
        out = {}
        for row in self.status_log:
            out[row["rfc_id"]] = row
        return list(out.values())

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
            rows = [r for r in self.revisions if r["rfc_id"] == eq("rfc_id") and (eq("version") is None or r["version"] == eq("version"))]
            rows = sorted(rows, key=lambda r: r["rev"], reverse=q.get("order", "").endswith("desc"))
            return ok(rows[:int(q["limit"])] if "limit" in q else rows)
        if "/rpc/" in path:
            fn = path.rsplit("/", 1)[1]
            self.calls.append((fn, body))
            if fn == "reserve_rfc_id":
                return ok(self.next_id("repo"))
            if fn in ("create_rfc", "add_rfc_revision"):
                if self.rate_limited:
                    return ok({"message": "rate limit"}, 429)
                for lang in ("pt", "en", "zh"):                                  # what rfc_check_input enforces
                    if lang not in body["p_meta"].get("title", {}) or f"lang:{lang}" not in body["p_bundle"].replace(" ", ""):
                        return ok({"message": f"invalid meta.title.{lang}"}, 400)
                if fn == "create_rfc":
                    rid = self.next_id("site")
                    self.add_revision(rid, body["p_bundle"], body["p_meta"], body["p_authors"], body["p_collaborators"], body["p_by"])
                    return ok({"rfc_id": rid, "version": "1.0"})
                if self.ids.get(body["p_rfc_id"]) != "site":
                    return ok({"message": "unknown RFC"}, 400)
                row = self.add_revision(body["p_rfc_id"], body["p_bundle"], body["p_meta"], body["p_authors"], body["p_collaborators"],
                                        body["p_by"], body.get("p_note"))
                return ok({"rfc_id": row["rfc_id"], "version": row["version"]})
        route.fulfill(status=404, headers=CORS, body="not found")
