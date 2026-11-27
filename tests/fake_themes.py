"""The themes part of the fake Supabase: fronts, themes, execution items, dependencies, Jira links and the event log, with the same rules
as supabase/migrations/20261124000000_themes.sql (the functions are the only way to write; every change of a theme is an event)."""
import json
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qs

STATUSES = ("not_started", "on_track", "at_risk", "blocked", "paused", "done", "cancelled")
COLS = ("todo", "doing", "blocked", "done")
URGENCIES = ("urgent", "important", "info")
FRONTS = [("pop", "POP", 1, False), ("api-platform", "API Platform", 2, False), ("mini-apps", "Mini-Apps", 3, False),
          ("payments", "Payments", 4, False), ("product-center", "Product Center", 5, False), ("outros", "Outros", 99, True)]
TABLES = ("fronts", "themes", "theme_items", "theme_links", "theme_jira", "theme_events", "theme_updates", "theme_blockers", "theme_decisions",
          "stage_gates", "board_columns", "theme_gate_checks", "attachments", "fup_meetings")
ROUTE_STAGES = {"bug": [6, 7, 8, 9, 10], "p0": [7, 8, 9, 10]}
STAGE_NAMES = {1: "01 Solicitação", 2: "02 Pesquisa", 3: "03 Decisão", 4: "04 PRD e início", 5: "05 Revisão da solução", 6: "06 Planejamento",
               7: "07 Desenvolvimento", 8: "08 Testes", 9: "09 Publicação", 10: "10 Lançamento"}
# (key, stage, title, non_waivable): a short copy of the seed of supabase/migrations/20261127000000_board_columns.sql, enough to test with
GATES = [("01-triage", 1, "Informações completas", False), ("01-owner", 1, "Responsável definido", False), ("02-evidence", 2, "Evidências do problema", False),
         ("03-approved", 3, "Aprovado com escopo", False), ("04-prd", 4, "PRD no padrão", False), ("04-jira", 4, "Issue do Jira liga RFC e PRD", False),
         ("05-conclusions", 5, "Quatro conclusões", False), ("06-milestones", 6, "Quatro marcos", False), ("07-pipeline", 7, "Pipeline no padrão", False),
         ("08-acceptance", 8, "Aceite de negócio", True), ("09-rollback", 9, "Rollback ensaiado", True), ("10-reconcile", 10, "Conciliação fecha", True)]


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
        self.gates = [{"key": k, "stage": st, "position": i + 1, "title": {"pt": ti, "en": ti, "zh": ""}, "owner_role": None, "non_waivable": nw}
                      for i, (k, st, ti, nw) in enumerate(GATES)]
        self.columns = [{"id": str(uuid.uuid4()), "board": "b2b", "name": {"pt": STAGE_NAMES[n], "en": STAGE_NAMES[n], "zh": ""}, "position": n, "stage": n,
                         "wip_limit": None, "created_at": now()} for n in range(1, 11)]
        self.gate_checks = []
        self.suggest_calls, self.suggest_response, self.suggest_status = [], None, 200          # the Edge Function suggest-summary
        self.plan_calls, self.plan_response, self.plan_status = [], None, 200                   # the Edge Function plan-deck
        self.attachments = []
        self.storage_calls, self.downloads = [], []
        self.storage = {}                                 # path -> {"size", "mimetype", "data"}: the private bucket 'attachments'
        self.fups = []                                    # supabase/migrations/20261205000000_fup.sql

    # -- test helpers -----------------------------------------------------------
    def seed_theme(self, tid, front="payments", kind="project", title=None, **extra):
        self.ids.setdefault(tid, "site" if kind == "project" else "theme")
        row = {"id": tid, "kind": kind, "front": front, "title": title or {"pt": f"Tema {tid}"}, "owner": None, "status": "not_started",
               "stage": 1 if kind == "project" else None, "board_column": None, "answers": {}, "route": "full", "what_it_is": {}, "progress": {}, "problem": {}, "solution": {},
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
               "urgency": "important" if leadership else "info", "state": state, "how_resolved": {}, "resolved_at": None, "resolved_by": None, "created_at": now(), "created_by": "Ana", "text_meta": {}}
        row.update(extra)
        self.blockers.append(row)
        return row

    def seed_decision(self, tid, what, leadership=False, state="open", **extra):
        row = {"id": str(uuid.uuid4()), "theme_id": tid, "item_id": None, "what": what, "decider": None, "due_date": None, "needs_leadership": leadership,
               "urgency": "important" if leadership else "info", "state": state, "decision": {}, "decided_at": None, "decided_by": None, "created_at": now(), "created_by": "Ana", "text_meta": {}}
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
        for k in ("problem", "solution", "success"):                        # a person's text is a confirmed answer (the sources of a suggestion stay)
            if k in p and old[k] != t[k]:
                if any((v or "").strip() for v in (t[k] or {}).values()):
                    t["answers"][k] = {"state": "confirmed", "by": by.strip(), "at": now(), "sources": (t["answers"].get(k) or {}).get("sources", [])}
                else:
                    t["answers"].pop(k, None)
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
            start, due = p.get("start_date") or None, p.get("due_date") or None
            if start and due and start > due:
                raise Invalid("invalid period")
            row = {"id": str(uuid.uuid4()), "theme_id": theme, "title": p["title"].strip(), "owner": (p.get("owner") or "").strip() or None,
                   "col": col or "todo", "start_date": start, "due_date": due, "milestone": bool(p.get("milestone")), "created_at": now(), "created_by": by.strip(),
                   "updated_at": now()}
            self.items.append(row)
            self.event(theme, by.strip(), "item_created", None, row["title"], row["id"])
            return {"id": row["id"]}
        row = next((i for i in self.items if i["id"] == item and i["theme_id"] == theme), None)
        if not row:
            raise Invalid("unknown item")
        before = row["col"]
        period = (row.get("start_date"), row.get("due_date"))
        start = (p.get("start_date") or None) if "start_date" in p else period[0]
        due = (p.get("due_date") or None) if "due_date" in p else period[1]
        if start and due and start > due:
            raise Invalid("invalid period")
        for k in ("title", "owner", "col", "milestone"):
            if k in p and p[k] is not None:
                row[k] = p[k].strip() if isinstance(p[k], str) else p[k]
        row["start_date"], row["due_date"] = start, due
        if col and col != before:
            self.event(theme, by.strip(), "item_col", before, col, item)
        if (start, due) != period:
            self.event(theme, by.strip(), "item_period", {"start_date": period[0], "due_date": period[1]}, {"start_date": start, "due_date": due}, item)
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
        if "urgency" in p and p["urgency"] not in URGENCIES:
            raise Invalid("invalid urgency")
        if "what" in p:
            self._i18n(p["what"], 1200, True)
        if rid is None:
            self._i18n(p.get("what") or {}, 1200, True)
            lead = bool(p.get("needs_leadership"))
            row = (self.seed_blocker if kind == "blocker" else self.seed_decision)(theme, p["what"], lead, item_id=item, due_date=p.get("due_date") or None,
                                                                                 urgency=p.get("urgency") or ("important" if lead else "info"),
                                                                                 created_by=by.strip(), **{who: (p.get(who) or "").strip() or None})
            self.event(theme, by.strip(), f"{kind}_added", None, p["what"], item)
            return {"id": row["id"]}
        row = next((r for r in table if r["id"] == rid and r["theme_id"] == theme), None)
        if not row:
            raise Invalid(f"unknown {kind}")
        before = dict(row["what"])
        for k in ("what", who, "due_date", "needs_leadership", "urgency"):
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

    # -- the FUP (supabase/migrations/20261205000000_fup.sql) -------------------------------------------------------
    @staticmethod
    def _fup_agenda(a):
        if not isinstance(a, list) or len(a) > 300:
            raise Invalid("invalid agenda")
        for x in a:
            if (not isinstance(x, dict) or not re.fullmatch(r"PHZ-\d{4}", str(x.get("theme", ""))) or x.get("kind") not in ("inform", "discuss", "decide")
                    or not isinstance(x.get("on"), bool) or not isinstance(x.get("star"), bool)):
                raise Invalid("invalid agenda")

    @staticmethod
    def _fup_log(lg):
        if not isinstance(lg, list) or len(lg) > 500:
            raise Invalid("invalid log")
        for x in lg:
            if (not isinstance(x, dict) or not re.fullmatch(r"PHZ-\d{4}", str(x.get("theme", ""))) or x.get("type") not in ("note", "decision", "action")
                    or not 1 <= len(str(x.get("text") or "").strip()) <= 1200 or x.get("progress") not in ("todo", "doing", "done")
                    or (x.get("due") is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(x["due"])))
                    or (x.get("ref") is not None and not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", str(x["ref"])))):
                raise Invalid("invalid log")

    def save_fup(self, fid, p, by):
        self._name(by)
        if "title" in p and not 1 <= len(str(p.get("title") or "").strip()) <= 120:
            raise Invalid("invalid title")
        if "held_on" in p and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(p.get("held_on") or "")):
            raise Invalid("invalid date")
        if "agenda" in p:
            self._fup_agenda(p["agenda"])
        if "log" in p:
            self._fup_log(p["log"])
        if fid is None:
            if not str(p.get("title") or "").strip():
                raise Invalid("invalid title")
            row = {"id": str(uuid.uuid4()), "title": p["title"].strip(), "held_on": p.get("held_on") or now()[:10], "agenda": p.get("agenda") or [],
                   "log": p.get("log") or [], "closed_at": None, "snapshot": None, "created_by": by.strip(), "created_at": now(), "updated_at": now()}
            self.fups.append(row)
            return {"id": row["id"]}
        f = next((r for r in self.fups if r["id"] == fid), None)
        if not f:
            raise Invalid("unknown fup")
        if f["closed_at"]:
            raise Invalid("fup closed")
        for k in ("title", "held_on", "agenda", "log"):
            if k in p:
                f[k] = p[k].strip() if k == "title" else p[k]
        f["updated_at"] = now()
        return {"id": fid}

    def close_fup(self, fid, by):
        self._name(by)
        f = next((r for r in self.fups if r["id"] == fid), None)
        if not f:
            raise Invalid("unknown fup")
        if f["closed_at"]:
            raise Invalid("fup closed")
        y, m, d = f["held_on"].split("-")
        n = 0
        for tid in dict.fromkeys(x["theme"] for x in f["log"]):
            t = self.themes.get(tid)
            if not t or t["hidden"]:
                continue
            notes = [("Decidido: " + x["text"]) if x["type"] == "decision" else x["text"] for x in f["log"] if x["theme"] == tid and x["type"] in ("note", "decision")]
            nexts = [x["text"] + (f" (até {x['due'][8:10]}/{x['due'][5:7]})" if x.get("due") else "") for x in f["log"] if x["theme"] == tid and x["type"] == "action"]
            day = f"{d}/{m}/{y}"
            p = {"progress": {"pt": f"Tratado no FUP de {day}.", "en": f"Discussed in the FUP of {day}.", "zh": f"已在 {day} 的 FUP 会议上讨论。"}}
            if notes:
                p["advanced"] = {"pt": "\n".join(notes)[:2000]}
            if nexts:
                p["next_step"] = {"pt": "\n".join(nexts)[:2000]}
            self.post_theme_update(tid, p, by)
            n += 1
        on = [x["theme"] for x in f["agenda"] if x["on"]]
        f["snapshot"] = {"agenda": f["agenda"], "log": f["log"], "statuses": {k: self.themes[k]["status"] for k in on if k in self.themes}, "closed_by": by.strip()}
        f["closed_at"] = f["updated_at"] = now()
        return {"id": fid, "updates": n}

    # -- the B2B board ------------------------------------------------------------
    def column_of_stage(self, stage):
        return next(c for c in sorted(self.columns, key=lambda c: (c["position"], c["created_at"])) if c["stage"] == stage)

    def current_column(self, t):
        cur = next((c for c in self.columns if c["id"] == t.get("board_column") and c["stage"] == t["stage"]), None)
        return cur or (self.column_of_stage(t["stage"]) if t["stage"] else None)

    def move_theme_card(self, theme, column, by, reason=None):
        self._name(by)
        t = self.themes.get(theme)
        if not t or t["hidden"] or t["kind"] != "project":
            raise Invalid("unknown theme")
        dest = next((c for c in self.columns if c["id"] == column), None)
        if not dest:
            raise Invalid("unknown column")
        if len(reason or "") > 300:
            raise Invalid("invalid reason")
        cur = self.current_column(t)
        if cur and cur["id"] == dest["id"]:
            return {"moved": False}
        frm = t["stage"]
        route = ROUTE_STAGES.get(t["route"], list(range(1, 11)))
        skipped = dest["stage"] > (frm or 0) and any((frm or 0) < s < dest["stage"] for s in route)
        if (skipped or dest["stage"] not in route) and not (reason or "").strip():
            raise Invalid("reason required")
        open_gates = []
        if frm is not None and dest["stage"] > frm:
            open_gates = [g["key"] for g in self.gates if g["stage"] == frm and not any(k["theme_id"] == theme and k["gate_key"] == g["key"] for k in self.gate_checks)]
        t.update(stage=dest["stage"], board_column=dest["id"], updated_at=now())
        self.event(theme, by.strip(), "move", None, {"from_column": cur["id"] if cur else None, "to_column": dest["id"], "from_stage": frm,
                                                      "to_stage": dest["stage"], "open_gates": open_gates, "reason": (reason or "").strip() or None})
        return {"moved": True, "open_gates": open_gates}

    def set_theme_gate(self, theme, gate, evidence, by):
        self._name(by)
        t = self.themes.get(theme)
        if not t or t["hidden"] or t["kind"] != "project":
            raise Invalid("unknown theme")
        if not any(g["key"] == gate for g in self.gates):
            raise Invalid("unknown gate")
        self.gate_checks = [k for k in self.gate_checks if not (k["theme_id"] == theme and k["gate_key"] == gate)]
        if not (evidence or "").strip():
            self.event(theme, by.strip(), "gate_unchecked", None, gate)
            return
        if len(evidence.strip()) > 500:
            raise Invalid("invalid evidence")
        self.gate_checks.append({"theme_id": theme, "gate_key": gate, "evidence": evidence.strip(), "checked_by": by.strip(), "checked_at": now()})
        self.event(theme, by.strip(), "gate_checked", None, gate)

    def _stage_in_use(self, col):
        others = any(c["stage"] == col["stage"] and c["id"] != col["id"] for c in self.columns)
        return not others and any(t["stage"] == col["stage"] and t["kind"] == "project" and not t["hidden"] and not t["resolution"] for t in self.themes.values())

    def save_board_column(self, cid, p, by):
        self._name(by)
        if "name" in p:
            self._i18n(p["name"], 60, True)
        if "stage" in p and not 1 <= int(p["stage"]) <= 10:
            raise Invalid("invalid stage")
        if "position" in p and not 1 <= int(p["position"]) <= 100:
            raise Invalid("invalid position")
        wip = p.get("wip_limit")
        if wip not in (None, "") and int(wip) < 1:
            raise Invalid("invalid limit")
        wip = int(wip) if wip not in (None, "") else None
        if cid is None:
            if "name" not in p or "stage" not in p:
                raise Invalid("name and stage required")
            row = {"id": str(uuid.uuid4()), "board": "b2b", "name": p["name"], "position": int(p.get("position") or max([c["position"] for c in self.columns] + [0]) + 1),
                   "stage": int(p["stage"]), "wip_limit": wip, "created_at": now()}
            self.columns.append(row)
            return {"id": row["id"]}
        c = next((x for x in self.columns if x["id"] == cid), None)
        if not c:
            raise Invalid("unknown column")
        if "stage" in p and int(p["stage"]) != c["stage"] and self._stage_in_use(c):
            raise Invalid("stage in use")
        for k in ("name", "position", "stage"):
            if k in p:
                c[k] = int(p[k]) if k in ("position", "stage") else p[k]
        if "wip_limit" in p:
            c["wip_limit"] = wip
        return {"id": cid}

    def delete_board_column(self, cid, by):
        self._name(by)
        c = next((x for x in self.columns if x["id"] == cid), None)
        if not c:
            raise Invalid("unknown column")
        if self._stage_in_use(c):
            raise Invalid("stage in use")
        self.columns.remove(c)
        for t in self.themes.values():
            if t.get("board_column") == cid:
                t["board_column"] = None

    # -- attachments (supabase/migrations/20261128000000_attachments.sql) --------------------------------------------
    PATH_RE = re.compile(r"^(PHZ-\d{4})/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[^/]{1,150}$")

    def put_object(self, path, data=b"x", mimetype="application/octet-stream"):
        self.storage[path] = {"size": len(data), "mimetype": mimetype, "data": data}

    def seed_attachment(self, tid, name, kind="file", **extra):
        row = {"id": str(uuid.uuid4()), "theme_id": tid, "item_id": None, "kind": kind, "name": name, "description": "", "storage_path": None, "content_type": None,
               "size": None, "checksum": None, "body": None, "url": None, "stage": None, "replaces": None, "archive_version": None, "archive_date": None,
               "archive_note": None, "hidden": False, "created_at": now(), "created_by": "Ana"}
        if kind == "file":
            path = f"{tid}/{uuid.uuid4()}/{name}"
            self.put_object(path, extra.pop("data", b"conteudo"), extra.get("content_type") or "application/octet-stream")
            row.update(storage_path=path, content_type=extra.pop("content_type", "application/octet-stream"), size=self.storage[path]["size"])
        row.update(extra)
        self.attachments.append(row)
        return row

    def add_attachment(self, theme, p, by):
        self._name(by)
        t = self.themes.get(theme)
        if not t or t["hidden"]:
            raise Invalid("unknown theme")
        kind = p.get("kind")
        nm = (p.get("name") or "").strip()
        if kind not in ("file", "note", "link"):
            raise Invalid("invalid kind")
        if not 1 <= len(nm) <= 200:
            raise Invalid("invalid name")
        if len(p.get("description") or "") > 1000:
            raise Invalid("invalid description")
        st = p.get("stage")
        if st is not None and not 1 <= int(st) <= 10:
            raise Invalid("invalid stage")
        if p.get("item_id") and not any(i["id"] == p["item_id"] and i["theme_id"] == theme for i in self.items):
            raise Invalid("unknown item")
        rep = p.get("replaces")
        if rep and not any(a["id"] == rep and a["theme_id"] == theme and not a["hidden"] for a in self.attachments):
            raise Invalid("unknown attachment")
        if p.get("checksum") is not None and not re.fullmatch(r"[0-9a-f]{64}", p["checksum"]):
            raise Invalid("invalid checksum")
        row = {"id": str(uuid.uuid4()), "theme_id": theme, "item_id": p.get("item_id"), "kind": kind, "name": nm, "description": p.get("description") or "",
               "storage_path": None, "content_type": None, "size": None, "checksum": p.get("checksum"), "body": None, "url": None, "stage": st, "replaces": rep,
               "archive_version": None, "archive_date": None, "archive_note": None, "hidden": False, "created_at": now(), "created_by": by.strip()}
        if kind == "file":
            path = p.get("path") or ""
            m = self.PATH_RE.match(path)
            if not m or m.group(1) != theme:
                raise Invalid("invalid path")
            obj = self.storage.get(path)
            if not obj:
                raise Invalid("file not uploaded")
            row.update(storage_path=path, content_type=obj["mimetype"], size=obj["size"])
        elif kind == "note":
            if not 1 <= len(p.get("body") or "") <= 50000:
                raise Invalid("invalid note")
            row["body"] = p["body"]
        else:
            if not re.fullmatch(r"https://[^ ]{4,500}", p.get("url") or ""):
                raise Invalid("invalid url")
            row["url"] = p["url"]
        self.attachments.append(row)
        self.event(theme, by.strip(), "attachment_added", None, nm, p.get("item_id"))
        return {"id": row["id"]}

    def hide_attachment(self, aid, by):
        self._name(by)
        a = next((x for x in self.attachments if x["id"] == aid and not x["hidden"]), None)
        if not a:
            raise Invalid("unknown attachment")
        a["hidden"] = True
        self.event(a["theme_id"], by.strip(), "attachment_removed", a["name"], None, a["item_id"])

    def storage_handle(self, route, req, url):
        """The private bucket: upload (the policy checks the path), signed addresses and the signed download."""
        from urllib.parse import unquote
        from fake_supabase import CORS as H
        path = unquote(url.path.split("/storage/v1/object/", 1)[1])
        self.storage_calls.append((req.method, path))
        if path.startswith("sign/attachments/"):
            obj_path = path[len("sign/attachments/"):]
            if req.method == "POST":
                if obj_path not in self.storage:
                    return route.fulfill(status=400, headers={**H, "Content-Type": "application/json"}, body=json.dumps({"message": "Object not found"}))
                from urllib.parse import quote
                return route.fulfill(status=200, headers={**H, "Content-Type": "application/json"},
                                     body=json.dumps({"signedURL": f"/object/sign/attachments/{quote(obj_path)}?token=t0k3n"}))
            obj = self.storage.get(obj_path)
            if not obj:
                return route.fulfill(status=404, headers=H, body="")
            query = dict(parse_qs(url.query))
            self.downloads.append((obj_path, query))
            extra = {"Content-Disposition": f'attachment; filename="{query["download"][0]}"'} if "download" in query else {}     # what Storage does for ?download=
            return route.fulfill(status=200, headers={**H, **extra, "Content-Type": obj["mimetype"]}, body=obj["data"])
        if path.startswith("attachments/") and req.method == "POST":
            obj_path = path[len("attachments/"):]
            data = req.post_data_buffer or b""
            if not self.PATH_RE.match(obj_path):
                return route.fulfill(status=403, headers={**H, "Content-Type": "application/json"}, body=json.dumps({"message": "new row violates row-level security policy"}))
            if len(data) > 50 * 1024 * 1024:
                return route.fulfill(status=413, headers={**H, "Content-Type": "application/json"}, body=json.dumps({"message": "The object exceeded the maximum allowed size"}))
            if obj_path in self.storage:
                return route.fulfill(status=409, headers={**H, "Content-Type": "application/json"}, body=json.dumps({"message": "The resource already exists"}))
            self.put_object(obj_path, data, (req.headers.get("content-type") or "application/octet-stream").split(";")[0])
            return route.fulfill(status=200, headers={**H, "Content-Type": "application/json"}, body=json.dumps({"Key": "attachments/" + obj_path}))
        return route.fulfill(status=404, headers=H, body="")

    # -- slide answers (supabase/migrations/20261130000000_theme_answers.sql) -----------------------------------------
    @staticmethod
    def _has_text(v):
        return any((x or "").strip() for x in (v or {}).values())

    def suggest_theme_answers(self, theme, p, by):
        self._name(by)
        t = self.themes.get(theme)
        if not t or t["hidden"]:
            raise Invalid("unknown theme")
        applied = []
        for f in ("problem", "solution", "success"):
            if f not in p:
                continue
            s = p[f]
            if not isinstance(s, dict):
                raise Invalid("invalid answer")
            cur = t["answers"].get(f)
            if (cur or {}).get("state") == "confirmed" or (self._has_text(t[f]) and cur is None):
                continue                                                      # a person's text is never replaced
            srcs = s.get("sources") or []
            if not isinstance(srcs, list) or len(srcs) > 6 or any(not 1 <= len(x.get("label", "")) <= 200 or not 1 <= len(x.get("quote", "")) <= 400 for x in srcs):
                raise Invalid("invalid sources")
            if len(s.get("missing") or "") > 300:
                raise Invalid("invalid missing")
            txt = (s.get("text") or "").strip()
            t["text_meta"].pop(f, None)
            if txt:
                if len(txt) > 1200 or not srcs:
                    raise Invalid("invalid answer")
                t[f] = {"pt": txt}
                t["answers"][f] = {"state": "suggested", "by": by.strip(), "at": now(), "sources": srcs}
            else:
                t[f] = {}
                t["answers"][f] = {"state": "missing", "by": by.strip(), "at": now(), "missing": s.get("missing") or ""}
            applied.append(f)
        if applied:
            self.event(theme, by.strip(), "answers_suggested", None, applied)
        return {"applied": applied}

    def confirm_theme_answers(self, theme, fields, by):
        self._name(by)
        t = self.themes.get(theme)
        if not t or t["hidden"]:
            raise Invalid("unknown theme")
        for f in fields:
            if f not in ("problem", "solution", "success"):
                raise Invalid("invalid field")
            if not self._has_text(t[f]):
                raise Invalid("nothing to confirm")
            t["answers"][f] = {"state": "confirmed", "by": by.strip(), "at": now(), "sources": (t["answers"].get(f) or {}).get("sources", [])}
            self.event(theme, by.strip(), "answer_confirmed", None, f)

    def suggest_function(self, route, body, H):
        """The Edge Function suggest-summary: answers with `suggest_response` (set by the test) or an error status."""
        self.suggest_calls.append(body)
        if self.suggest_status != 200:
            return route.fulfill(status=self.suggest_status, headers={**H, "Content-Type": "application/json"}, body=json.dumps({"error": "failed"}))
        return route.fulfill(status=200, headers={**H, "Content-Type": "application/json"}, body=json.dumps(self.suggest_response or {"suggestions": {}, "sources": []}))

    def plan_function(self, route, body, H):
        """The Edge Function plan-deck: answers {"plan": plan_response} (set by the test) or an error status."""
        self.plan_calls.append(body)
        if self.plan_status != 200:
            return route.fulfill(status=self.plan_status, headers={**H, "Content-Type": "application/json"}, body=json.dumps({"error": "failed"}))
        return route.fulfill(status=200, headers={**H, "Content-Type": "application/json"}, body=json.dumps({"plan": self.plan_response}))

    # -- the HTTP side ----------------------------------------------------------
    def themes_handle(self, path, q, body, ok):
        """True when the request was about themes (and has been answered)."""
        fn = path.rsplit("/", 1)[1]
        if "/rpc/" in path and fn in ("create_theme", "update_theme", "update_front", "save_theme_item", "add_theme_jira", "remove_theme_jira", "set_theme_link",
                                      "post_theme_update", "save_theme_blocker", "resolve_theme_blocker", "save_theme_decision", "decide_theme_decision",
                                      "move_theme_card", "set_theme_gate", "save_board_column", "delete_board_column", "add_attachment", "hide_attachment", "suggest_theme_answers", "confirm_theme_answers", "save_fup", "close_fup"):
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
                    "move_theme_card": lambda: self.move_theme_card(body["p_theme"], body["p_column"], body["p_by"], body.get("p_reason")),
                    "set_theme_gate": lambda: self.set_theme_gate(body["p_theme"], body["p_gate"], body["p_evidence"], body["p_by"]),
                    "save_board_column": lambda: self.save_board_column(body["p_id"], body["p"], body["p_by"]),
                    "delete_board_column": lambda: self.delete_board_column(body["p_id"], body["p_by"]),
                    "add_attachment": lambda: self.add_attachment(body["p_theme"], body["p"], body["p_by"]),
                    "hide_attachment": lambda: self.hide_attachment(body["p_id"], body["p_by"]),
                    "suggest_theme_answers": lambda: self.suggest_theme_answers(body["p_theme"], body["p"], body["p_by"]),
                    "confirm_theme_answers": lambda: self.confirm_theme_answers(body["p_theme"], body["p_fields"], body["p_by"]),
                    "save_fup": lambda: self.save_fup(body["p_id"], body["p"], body["p_by"]),
                    "close_fup": lambda: self.close_fup(body["p_id"], body["p_by"]),
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
                "theme_blockers": self.blockers, "theme_decisions": self.decisions, "stage_gates": self.gates, "board_columns": self.columns,
                "theme_gate_checks": self.gate_checks,
                "attachments": [a for a in self.attachments if not a["hidden"]], "fup_meetings": self.fups}[table]
        for col, val in q.items():
            if col in ("select", "order", "limit", "offset"):
                continue
            if val.startswith("eq."):
                rows = [r for r in rows if str(r.get(col)).lower() == val[3:].lower()]
            elif val == "not.is.null":
                rows = [r for r in rows if r.get(col) is not None]
            elif val.startswith("in.("):
                wanted = val[4:-1].split(",")
                rows = [r for r in rows if str(r.get(col)) in wanted]
        order = q.get("order")
        if order:
            key, _, direction = order.split(",")[0].partition(".")
            rows = sorted(rows, key=lambda r: r.get(key) if isinstance(r.get(key), (int, float)) else str(r.get(key)), reverse=direction == "desc")
        rows = rows[int(q.get("offset", 0)):]
        if "limit" in q:
            rows = rows[:int(q["limit"])]
        sel = q.get("select", "*")
        ok(rows if sel == "*" else [{k: r[k] for k in sel.split(",")} for r in rows])
        return True
