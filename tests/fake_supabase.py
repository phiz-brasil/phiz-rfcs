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

    # -- test helpers ---------------------------------------------------
    def add_comment(self, rfc_id, section, author, body, parent_id=None, para=None, **extra):
        row = {"id": str(uuid.uuid4()), "rfc_id": rfc_id, "section": section, "parent_id": parent_id, "author": author,
               "body": body, "quote": None, "lang": "pt", "created_at": now(), "para": para,
               "translations": None, "src_lang": None, "hidden": False}
        row.update(extra)
        self.comments.append(row)
        return row

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
        route.fulfill(status=404, headers=CORS, body="not found")
