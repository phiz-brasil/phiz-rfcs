"""The themes part of the fake Supabase: fronts, themes, execution items, dependencies, Jira links and the event log, with the same rules
as supabase/migrations/20261124000000_themes.sql (the functions are the only way to write; every change of a theme is an event)."""
import re
import uuid
from datetime import datetime, timezone

STATUSES = ("not_started", "on_track", "at_risk", "blocked", "paused", "done", "cancelled")
COLS = ("todo", "doing", "blocked", "done")
FRONTS = [("pop", "POP", 1, False), ("api-platform", "API Platform", 2, False), ("mini-apps", "Mini-Apps", 3, False),
          ("payments", "Payments", 4, False), ("product-center", "Product Center", 5, False), ("outros", "Outros", 99, True)]
TABLES = ("fronts", "themes", "theme_items", "theme_links", "theme_jira", "theme_events", "theme_updates", "theme_blockers", "theme_decisions")


def now():
    return datetime.now(timezone.utc).isoformat()


class Invalid(Exception):
    pass


class ThemesMixin:
    def _init_themes(self):
        self.fronts = [{"key": k, "name": {"pt": n, "en": n, "zh": n}, "scope": {"pt": f"Escopo de {n}", "en": f"Scope of {n}", "zh": ""}, "ord": o, "is_other": other}
                       for k, n, o, other in FRONTS]
        self.themes, self.items, self.links, self.jira, self.events = {}, [], [], [], []
        self.updates, self.blockers, self.decisions = [], [], []
        self.week = "2026-W48"                            # the ISO week the "server" is in

    # -- test helpers -----------------------------------------------------------
    def seed_theme(self, tid, front="payments", kind="project", title=None, **extra):
        self.ids.setdefault(tid, "site" if kind == "project" else "theme")
        row = {"id": tid, "kind": kind, "front": front, "title": title or {"pt": f"Tema {tid}"}, "owner": None, "status": "not_started",
               "stage": 1 if kind == "project" else None, "route": "full", "what_it_is": {}, "progress": {}, "problem": {}, "solution": {},
               "success": {}, "text_meta": {}, "start_date": None, "due_date": None, "tags": [], "resolution": None, "hidden": False, "created_at": now(),
               "created_by": "importação", "updated_at": now()}
        row.update(extra)
        self.themes[tid] = row
        return row

    def machine_translate(self, tid, field, lang, text):
        """What the translation webhook leaves: the text in `lang`, marked as a machine translation."""
        t = self.themes[tid]
        t[field] = {**t[field], lang: text}
        t["text_meta"][field] = sorted({*t["text_meta"].get(field, []), lang})

    def event(self, theme_id, by, field, old=None, new=None, item_id=None):
        self.events.append({"id": str(uuid.uuid4()), "theme_id": theme_id, "item_id": item_id, "at": now(), "edited_by": by, "field": field,
                            "old_value": old, "new_value": new})

    def seed_update(self, tid, week=None, progress=None, by="Ana", **extra):
        row = {"id": str(uuid.uuid4()), "theme_id": tid, "week": week or self.week, "edited_by": by, "created_at": now(),
               "progress": progress or {"pt": "Tudo certo"}, "advanced": {}, "next_step": {}, "status_from": None, "status_to": None,
               "due_from": None, "due_to": None, "due_reason": None, "text_meta": {}}
        row.update(extra)
        self.updates.append(row)
        return row

    def seed_blocker(self, tid, what, leadership=False, state="open", **extra):
        row = {"id": str(uuid.uuid4()), "theme_id": tid, "item_id": None, "what": what, "owner": None, "due_date": None, "needs_leadership": leadership,
               "state": state, "how_resolved": {}, "resolved_at": None, "resolved_by": None, "created_at": now(), "created_by": "Ana", "text_meta": {}}
        row.update(extra)
        self.blockers.append(row)
        return row

    def seed_decision(self, tid, what, leadership=False, state="open", **extra):
        row = {"id": str(uuid.uuid4()), "theme_id": tid, "item_id": None, "what": what, "decider": None, "due_date": None, "needs_leadership": leadership,
               "state": state, "decision": {}, "decided_at": None, "decided_by": None, "created_at": now(), "created_by": "Ana", "text_meta": {}}
        row.update(extra)
        self.decisions.append(row)
        return row

    # -- the functions ----------------------------------------------------------
    @staticmethod
    def _i18n(v, maximum, required):
        if not isinstance(v, dict) or any(k not in ("pt", "en", "zh") or not isinstance(x, str) or len(x) > maximum for k, x in v.items()):
            raise Invalid("invalid text")
        if required and not any(x.strip() for x in v.values()):
            raise Invalid("text required")

    @staticmethod
    def _name(by):
        if not by or not 1 <= len(by.strip()) <= 60:
            raise Invalid("invalid name")

    def create_theme(self, p, by):
        self._name(by)
        kind = p.get("kind", "task")
        if kind not in ("project", "task"):
            raise Invalid("invalid kind")
        if not any(f["key"] == p.get("front") for f in self.fronts):
            raise Invalid("invalid front")
        self._i18n(p.get("title") or {}, 200, True)
        if p.get("id"):
            if p["id"] not in self.ids or p["id"] in self.themes:
                raise Invalid("unknown RFC" if p["id"] not in self.ids else "theme exists")
            tid = p["id"]
        else:
            tid = self.next_id("theme")
        self.seed_theme(tid, p["front"], kind, p["title"], owner=(p.get("owner") or "").strip()[:80] or None, created_by=by.strip())
        self.event(tid, by.strip(), "created", None, kind)
        return {"id": tid}

    def update_theme(self, tid, p, by):
        self._name(by)
        t = self.themes.get(tid)
        if not t or t["hidden"]:
            raise Invalid("unknown theme")
        if "front" in p and not any(f["key"] == p["front"] for f in self.fronts):
            raise Invalid("invalid front")
        if "title" in p:
            self._i18n(p["title"], 200, True)
        for k in ("what_it_is", "progress", "problem", "solution", "success"):
            if k in p:
                self._i18n(p[k], 1200, False)
        if "status" in p and p["status"] not in STATUSES:
            raise Invalid("invalid status")
        if p.get("stage") is not None and "stage" in p and (t["kind"] != "project" or not 1 <= int(p["stage"]) <= 10):
            raise Invalid("invalid stage")
        if "tags" in p and (not isinstance(p["tags"], list) or len(p["tags"]) > 20 or any(not isinstance(x, str) or not 1 <= len(x) <= 40 for x in p["tags"])):
            raise Invalid("invalid tags")
        old = dict(t)
        for k, v in p.items():
            if k in ("owner",):
                v = (v or "").strip() or None
            t[k] = v
        t["updated_at"] = now()
        for k in ("title", "what_it_is", "progress", "problem", "solution", "success"):      # a person who edits a language takes it off the machine list
            if k in p:
                for lg in ("pt", "en", "zh"):
                    if (old[k] or {}).get(lg) != (t[k] or {}).get(lg):
                        t["text_meta"][k] = [x for x in t["text_meta"].get(k, []) if x != lg]
        for k in ("front", "title", "owner", "status", "stage", "route", "what_it_is", "progress", "problem", "solution", "success",
                  "start_date", "due_date", "tags", "resolution"):
            if old[k] != t[k]:
                self.event(tid, by.strip(), k, old[k], t[k])

    def update_front(self, key, p, by):
        self._name(by)
        f = next((x for x in self.fronts if x["key"] == key), None)
        if not f:
            raise Invalid("unknown front")
        if "name" in p:
            self._i18n(p["name"], 60, True)
        if "scope" in p:
            self._i18n(p["scope"], 1200, False)
        if "ord" in p and (f["is_other"] or not 1 <= int(p["ord"]) <= 50):
            raise Invalid("invalid order")
        f.update({k: v for k, v in p.items() if k in ("name", "scope", "ord")})

    def save_theme_item(self, theme, item, p, by):
        self._name(by)
        t = self.themes.get(theme)
        if not t or t["hidden"] or t["kind"] != "project":
            raise Invalid("unknown project")
        col = p.get("col")
        if col is not None and col not in COLS:
            raise Invalid("invalid column")
        if "title" in p and not 1 <= len((p.get("title") or "").strip()) <= 200:
            raise Invalid("invalid title")
        if item is None:
            row = {"id": str(uuid.uuid4()), "theme_id": theme, "title": p["title"].strip(), "owner": (p.get("owner") or "").strip() or None,
                   "col": col or "todo", "due_date": p.get("due_date"), "milestone": bool(p.get("milestone")), "created_at": now(), "created_by": by.strip(), "updated_at": now()}
            self.items.append(row)
            self.event(theme, by.strip(), "item_created", None, row["title"], row["id"])
            return {"id": row["id"]}
        row = next((i for i in self.items if i["id"] == item and i["theme_id"] == theme), None)
        if not row:
            raise Invalid("unknown item")
        before = row["col"]
        for k in ("title", "owner", "col", "due_date", "milestone"):
            if k in p and p[k] is not None:
                row[k] = p[k].strip() if isinstance(p[k], str) else p[k]
        if col and col != before:
            self.event(theme, by.strip(), "item_col", before, col, item)
        return {"id": item}

    def add_theme_jira(self, theme, item, url, label, by):
        self._name(by)
        if theme not in self.themes:
            raise Invalid("unknown theme")
        if not url or not re.fullmatch(r"https://[^ ]{4,500}", url.strip()):
            raise Invalid("invalid url")
        m = re.search(r"([A-Z][A-Z0-9]+-[0-9]+)", url)
        row = {"id": str(uuid.uuid4()), "theme_id": theme, "item_id": item, "url": url.strip(), "label": (label or "").strip() or None,
               "issue_key": m.group(1) if m else None, "created_at": now(), "created_by": by.strip()}
        self.jira.append(row)
        self.event(theme, by.strip(), "jira_added", None, row["url"], item)
        return {"id": row["id"], "issue_key": row["issue_key"]}

    def remove_theme_jira(self, jid, by):
        self._name(by)
        row = next((j for j in self.jira if j["id"] == jid), None)
        if row:
            self.jira.remove(row)
            self.event(row["theme_id"], by.strip(), "jira_removed", row["url"], None, row["item_id"])

    def set_theme_link(self, theme, to, kind, on, by):
        self._name(by)
        if kind not in ("depends_on", "blocks", "related") or theme == to:
            raise Invalid("invalid link")
        if theme not in self.themes or to not in self.themes:
            raise Invalid("unknown theme")
        row = {"theme_id": theme, "to_theme": to, "kind": kind}
        if on:
            if row not in self.links:
                self.links.append(row)
            self.event(theme, by.strip(), "link_added", None, {"to": to, "kind": kind})
        else:
            self.links = [x for x in self.links if x != row]
            self.event(theme, by.strip(), "link_removed", {"to": to, "kind": kind}, None)

    def post_theme_update(self, theme, p, by):
        self._name(by)
        t = self.themes.get(theme)
        if not t or t["hidden"]:
            raise Invalid("unknown theme")
        self._i18n(p.get("progress") or {}, 1200, True)
        self._i18n(p.get("advanced") or {}, 2000, False)
        self._i18n(p.get("next_step") or {}, 2000, False)
        st = p.get("status")
        if st is not None and st not in STATUSES:
            raise Invalid("invalid status")
        if len(p.get("due_reason") or "") > 300:
            raise Invalid("invalid reason")
        due_set = "due_date" in p
        due = (p.get("due_date") or None) if due_set else None
        status_changed = st is not None and st != t["status"]
        due_changed = due_set and due != t["due_date"]
        row = {"id": str(uuid.uuid4()), "theme_id": theme, "week": self.week, "edited_by": by.strip(), "created_at": now(), "progress": p["progress"],
               "advanced": p.get("advanced") or {}, "next_step": p.get("next_step") or {},
               "status_from": t["status"] if status_changed else None, "status_to": st if status_changed else None,
               "due_from": t["due_date"] if due_changed else None, "due_to": due if due_changed else None,
               "due_reason": (p.get("due_reason") or "").strip() or None, "text_meta": {}}
        self.updates.append(row)
        old_status, old_due = t["status"], t["due_date"]
        t["progress"] = p["progress"]
        t["text_meta"].pop("progress", None)
        t["status"] = st or t["status"]
        if due_set:
            t["due_date"] = due
        t["updated_at"] = now()
        self.event(theme, by.strip(), "update_posted", None, self.week)
        if status_changed:
            self.event(theme, by.strip(), "status", old_status, st)
        if due_changed:
            self.event(theme, by.strip(), "due_date", old_due, due)
        return {"id": row["id"], "week": self.week}

    def _record(self, table, theme, rid, p, by, kind):
        self._name(by)
        t = self.themes.get(theme)
        if not t or t["hidden"]:
            raise Invalid("unknown theme")
        item = p.get("item_id") or None
        if item and not any(i["id"] == item and i["theme_id"] == theme for i in self.items):
            raise Invalid("unknown item")
        who = "owner" if kind == "blocker" else "decider"
        if "what" in p:
            self._i18n(p["what"], 1200, True)
        if rid is None:
            self._i18n(p.get("what") or {}, 1200, True)
            row = (self.seed_blocker if kind == "blocker" else self.seed_decision)(theme, p["what"], bool(p.get("needs_leadership")),
                                                                                 item_id=item, due_date=p.get("due_date") or None, created_by=by.strip(), **{who: (p.get(who) or "").strip() or None})
            self.event(theme, by.strip(), f"{kind}_added", None, p["what"], item)
            return {"id": row["id"]}
        row = next((r for r in table if r["id"] == rid and r["theme_id"] == theme), None)
        if not row:
            raise Invalid(f"unknown {kind}")
        before = dict(row["what"])
        for k in ("what", who, "due_date", "needs_leadership"):
            if k in p:
                row[k] = (p[k] or None) if k in (who, "due_date") else p[k]
        for lg in ("pt", "en", "zh"):
            if before.get(lg) != row["what"].get(lg):
                row["text_meta"]["what"] = [x for x in row["text_meta"].get("what", []) if x != lg]
        return {"id": rid}

    def save_theme_blocker(self, theme, rid, p, by):
        return self._record(self.blockers, theme, rid, p, by, "blocker")

    def save_theme_decision(self, theme, rid, p, by):
        return self._record(self.decisions, theme, rid, p, by, "decision")

    def resolve_theme_blocker(self, rid, how, by):
        self._name(by)
        b = next((r for r in self.blockers if r["id"] == rid and r["state"] == "open"), None)
        if not b:
            raise Invalid("unknown blocker")
        self._i18n(how or {}, 1200, False)
        b.update(state="resolved", how_resolved=how or {}, resolved_at=now(), resolved_by=by.strip())
        self.event(b["theme_id"], by.strip(), "blocker_resolved", b["what"], None, b["item_id"])

    def decide_theme_decision(self, rid, state, decision, by):
        self._name(by)
        if state not in ("decided", "dropped"):
            raise Invalid("invalid state")
        d = next((r for r in self.decisions if r["id"] == rid and r["state"] == "open"), None)
        if not d:
            raise Invalid("unknown decision")
        self._i18n(decision or {}, 1200, state == "decided")
        d.update(state=state, decision=decision or {}, decided_at=now(), decided_by=by.strip())
        self.event(d["theme_id"], by.strip(), f"decision_{state}", d["what"], decision, d["item_id"])

    # -- the HTTP side ----------------------------------------------------------
    def themes_handle(self, path, q, body, ok):
        """True when the request was about themes (and has been answered)."""
        fn = path.rsplit("/", 1)[1]
        if "/rpc/" in path and fn in ("create_theme", "update_theme", "update_front", "save_theme_item", "add_theme_jira", "remove_theme_jira", "set_theme_link",
                                      "post_theme_update", "save_theme_blocker", "resolve_theme_blocker", "save_theme_decision", "decide_theme_decision"):
            self.calls.append((fn, body))
            if self.rate_limited:
                ok({"message": "rate limit"}, 429)
                return True
            try:
                res = {
                    "create_theme": lambda: self.create_theme(body["p"], body["p_by"]),
                    "update_theme": lambda: self.update_theme(body["p_id"], body["p"], body["p_by"]),
                    "update_front": lambda: self.update_front(body["p_key"], body["p"], body["p_by"]),
                    "save_theme_item": lambda: self.save_theme_item(body["p_theme"], body["p_item"], body["p"], body["p_by"]),
                    "add_theme_jira": lambda: self.add_theme_jira(body["p_theme"], body["p_item"], body["p_url"], body["p_label"], body["p_by"]),
                    "remove_theme_jira": lambda: self.remove_theme_jira(body["p_id"], body["p_by"]),
                    "set_theme_link": lambda: self.set_theme_link(body["p_theme"], body["p_to"], body["p_kind"], body["p_on"], body["p_by"]),
                    "post_theme_update": lambda: self.post_theme_update(body["p_theme"], body["p"], body["p_by"]),
                    "save_theme_blocker": lambda: self.save_theme_blocker(body["p_theme"], body["p_id"], body["p"], body["p_by"]),
                    "resolve_theme_blocker": lambda: self.resolve_theme_blocker(body["p_id"], body["p_how"], body["p_by"]),
                    "save_theme_decision": lambda: self.save_theme_decision(body["p_theme"], body["p_id"], body["p"], body["p_by"]),
                    "decide_theme_decision": lambda: self.decide_theme_decision(body["p_id"], body["p_state"], body["p_decision"], body["p_by"]),
                }[fn]()
            except Invalid as e:
                ok({"message": str(e)}, 400)
                return True
            ok(res if res is not None else self._empty())
            return True
        table = path.rsplit("/rest/v1/", 1)[-1] if "/rest/v1/" in path else ""
        if table not in TABLES:
            return False
        rows = {"fronts": self.fronts, "themes": [t for t in self.themes.values() if not t["hidden"]], "theme_items": self.items,
                "theme_links": self.links, "theme_jira": self.jira, "theme_events": self.events, "theme_updates": self.updates,
                "theme_blockers": self.blockers, "theme_decisions": self.decisions}[table]
        for col, val in q.items():
            if col in ("select", "order", "limit"):
                continue
            if val.startswith("eq."):
                rows = [r for r in rows if str(r.get(col)).lower() == val[3:].lower()]
            elif val.startswith("in.("):
                wanted = val[4:-1].split(",")
                rows = [r for r in rows if str(r.get(col)) in wanted]
        order = q.get("order")
        if order:
            key, _, direction = order.partition(".")
            rows = sorted(rows, key=lambda r: str(r.get(key)), reverse=direction == "desc")
        if "limit" in q:
            rows = rows[:int(q["limit"])]
        sel = q.get("select", "*")
        ok(rows if sel == "*" else [{k: r[k] for k in sel.split(",")} for r in rows])
        return True
