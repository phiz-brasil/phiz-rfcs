"""Builds rfc.html: trilingual RFC page with shared code samples, Mermaid diagrams and embedded Swagger UI."""
import json, re, html, yaml
from openapi_gen import build, EXAMPLES, MEDIA_EXAMPLE

LANGS = [("pt", "pt-BR", "PT-BR"), ("en", "en-US", "EN-US"), ("zh", "zh-CN", "中文")]

# ---------- code samples (shared by all languages) ----------
J = lambda o: json.dumps(o, ensure_ascii=False, indent=2)

CODE = {
"legacy_auth": ("http", """POST /gateway/openapi/auth
Content-Type: application/json

{
  "app_id": "69c37cb1821121af34201f48",
  "app_secret": "94B18B920D19463C7264BD0BDE30C31…",
  "description": "push news",
  "grant_type": "user_credentials",
  "device_fingerprint": ""
}

200 OK
{
  "code": 200,
  "msg": "success",
  "data": {
    "scope": "channel",
    "status": "active",
    "access_token": "at_1770343926041_1Y3iz6XN…",
    "token_type": "Bearer",
    "expires_in": 7199,
    "refresh_token": "rt_1770343926041_mxc7RV9…",
    "access_token_expires_at": "2026-02-06T04:…",
    "refresh_token_expires_at": "2026-05-07T02:…",
    "created_at": "2026-02-05T10:15:23.672+00:00"
  },
  "success": true
}"""),
"token_curl": ("bash", """# Base URL of this API: current PHIZ gateway + /gateway/business prefix (illustrative host)
PHIZ_API_BASE="https://gateway.phiz.chat/gateway/business"

curl -X POST "$PHIZ_API_BASE/oauth/token" \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d grant_type=client_credentials \\
  -d client_id=app_2Fk81PzQ \\
  -d client_secret="$PHIZ_CLIENT_SECRET" \\
  -d "scope=messages:send messages:read\""""),
"token_resp": ("json", J({"access_token": "eyJhbGciOiJFUzI1NiIsImtpZCI6InBoei0yMDI2LTEwIn0…", "token_type": "Bearer",
                           "expires_in": 3600, "scope": "messages:send messages:read",
                           "merchant_id": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57"})),
"token_err": ("json", J({"error": "invalid_client", "error_description": "Client authentication failed."})),
"jwt_claims": ("json", J({"iss": "https://gateway.phiz.chat/gateway/business", "sub": "app_2Fk81PzQ", "aud": "phiz-business-api",
                           "mid": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57", "scope": "messages:send messages:read",
                           "snd": ["7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57", "1231"], "env": "live", "iat": 1760527800, "exp": 1760531400, "jti": "tok_01JA9VQ4N2"})),
"me_resp": ("json", J({"active": True, "app_id": "app_2Fk81PzQ", "merchant_id": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57",
                        "scope": "messages:send messages:read", "senders": ["7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57", "1231"], "expires_at": "2026-10-15T12:30:00Z"})),
"send_curl": ("bash", """# sender_id = merchant_id: direct message from the merchant, no channel needed
curl -X POST "$PHIZ_API_BASE/v1/7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57/messages" \\
  -H "Authorization: Bearer $PHIZ_TOKEN" \\
  -H "Content-Type: application/json" \\
  -H "Idempotency-Key: pedido-48213-envio" \\
  -d '{
    "messaging_product": "phiz",
    "to": "+5511987654321",
    "to_type": "phone",
    "type": "text",
    "text": { "body": "Olá, Maria! Seu pedido #48213 foi enviado." },
    "biz_opaque_callback_data": "pedido=48213"
  }'"""),
"send_curl_channel": ("bash", """# sender_id = 1231: same request, sent through the merchant's channel
curl -X POST "$PHIZ_API_BASE/v1/1231/messages" \\
  -H "Authorization: Bearer $PHIZ_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{ "to": "+5511987654321", "type": "text", "text": { "body": "Novidades da semana na Loja Exemplo - Ofertas" } }'"""),
"send_resp": ("json", J({"messaging_product": "phiz", "contacts": [{"input": "+5511987654321", "phiz_id": None}],
                          "messages": [{"id": "pmid.01JA9VZ6T8R3", "message_status": "accepted"}]})),
"send_phiz_id": ("json", J({"to": "839201447", "to_type": "phiz_id", "type": "text", "text": {"body": "Seu cupom chegou: PHIZ10"}})),
"send_buttons": ("json", J({"to": "+5511987654321", "type": "interactive", "interactive": {"type": "button",
                    "body": {"text": "Confirma a entrega amanhã entre 9h e 12h?"},
                    "action": {"buttons": [{"type": "reply", "reply": {"id": "confirmar", "title": "Confirmar"}},
                                            {"type": "reply", "reply": {"id": "reagendar", "title": "Reagendar"}}]}}})),
"media_upload": ("bash", """# 1. Upload the file to PHIZ (multipart/form-data). Third-party URLs are not accepted when sending.
curl -X POST "$PHIZ_API_BASE/v1/7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57/media" \\
  -H "Authorization: Bearer $PHIZ_TOKEN" \\
  -F messaging_product=phiz \\
  -F type=application/pdf \\
  -F file=@nota-fiscal-48213.pdf"""),
"media_upload_resp": ("json", J(MEDIA_EXAMPLE)),
"send_audio": ("json", J({"to": "+5511987654321", "type": "audio", "audio": {"id": "pmed.01JB2K4M7A"}})),
"send_video": ("json", J({"to": "839201447", "to_type": "phiz_id", "type": "video",
                           "video": {"link": "https://media.phiz.chat/biz/pmed.01JB2K5V1C", "caption": "Como montar seu produto"}})),
"send_document": ("json", J({"to": "+5511987654321", "type": "document",
                              "document": {"id": "pmed.01JB2K7Q9X", "filename": "nota-fiscal-48213.pdf", "caption": "Nota fiscal do pedido #48213"}})),
"wh_inbound_media": ("json", J({"from": "839201447", "id": "pmid.IN_01JA9W7R", "timestamp": "1760528731", "type": "audio",
                                 "audio": {"url": "https://media.phiz.chat/in/9xT2…?expires=1760615131&sig=…", "mime_type": "audio/ogg; codecs=opus", "sha256": "3f9a…", "voice": True}})),
"mark_read": ("json", J({"messaging_product": "phiz", "status": "read", "message_id": "pmid.IN_01JA9W2C"})),
"error_env": ("json", J({"error": {"code": 1003, "type": "invalid_parameter",
                                    "message": "Field 'to' must be E.164 when to_type is 'phone'.",
                                    "details": [{"field": "to", "issue": "format"}], "trace_id": "trc_9f2c41ab"}})),
"wh_verify_node": ("javascript", """// Express: verification handshake + signed events
import express from "express";
import crypto from "node:crypto";

const app = express();
app.use(express.raw({ type: "application/json" })); // keep the raw body for the HMAC

app.get("/phiz/webhook", (req, res) => {
  const ok = req.query["hub.mode"] === "subscribe" &&
             req.query["hub.verify_token"] === process.env.PHIZ_VERIFY_TOKEN;
  return ok ? res.status(200).send(req.query["hub.challenge"]) : res.sendStatus(403);
});

app.post("/phiz/webhook", (req, res) => {
  const ts = Number(req.get("X-Phiz-Timestamp"));
  if (Math.abs(Date.now() / 1000 - ts) > 300) return res.sendStatus(400);

  const expected = "sha256=" + crypto
    .createHmac("sha256", process.env.PHIZ_WEBHOOK_SECRET)
    .update(`${ts}.${req.body}`)
    .digest("hex");
  const received = (req.get("X-Phiz-Signature-256") || "").split(",");
  const valid = received.some(sig => sig.length === expected.length &&
    crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected)));
  if (!valid) return res.sendStatus(401);

  queue.push({ deliveryId: req.get("X-Phiz-Delivery-Id"), event: JSON.parse(req.body) });
  res.sendStatus(200); // answer fast, process asynchronously
});"""),
"wh_verify_py": ("python", """# Flask: signature check
import hmac, hashlib, time, os
from flask import request, abort

def verify_phiz_signature() -> None:
    ts = int(request.headers["X-Phiz-Timestamp"])
    if abs(time.time() - ts) > 300:
        abort(400)
    msg = f"{ts}.".encode() + request.get_data()  # raw bytes, before JSON parsing
    expected = "sha256=" + hmac.new(os.environ["PHIZ_WEBHOOK_SECRET"].encode(), msg, hashlib.sha256).hexdigest()
    received = request.headers.get("X-Phiz-Signature-256", "").split(",")
    if not any(hmac.compare_digest(sig, expected) for sig in received):
        abort(401)"""),
"wh_headers": ("http", """POST /phiz/webhook HTTP/1.1
Host: integracao.lojaexemplo.com.br
Content-Type: application/json
User-Agent: PHIZ-Webhooks/1.0
X-Phiz-Delivery-Id: dlv_01JA9W2D7K
X-Phiz-Timestamp: 1760528527
X-Phiz-Signature-256: sha256=6f1c0e…"""),
"wh_inbound": ("json", J(EXAMPLES["inbound"])),
"wh_status": ("json", J(EXAMPLES["status"])),
"wh_failed": ("json", J(EXAMPLES["failed"])),
"webhook_put": ("bash", """curl -X PUT "$PHIZ_API_BASE/v1/apps/app_2Fk81PzQ/webhook" \\
  -H "Authorization: Bearer $PHIZ_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://integracao.lojaexemplo.com.br/phiz/webhook",
    "verify_token": "um-texto-que-so-voce-conhece",
    "fields": ["messages", "message_status"]
  }'"""),
"ratelimit": ("http", """HTTP/1.1 429 Too Many Requests
Retry-After: 2
X-RateLimit-Limit: 80
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1760528529"""),
}


def hl_json(src):
    out = []
    tok = re.compile(r'("(?:[^"\\]|\\.)*")(\s*:)?|(-?\b\d+(?:\.\d+)?\b)|\b(true|false|null)\b|([{}\[\],:])|(\s+)|(.)', re.S)
    for m in tok.finditer(src):
        s, colon, num, kw, punct, ws, other = m.groups()
        if s is not None:
            cls = "k" if colon else "s"
            out.append(f'<span class="t-{cls}">{html.escape(s)}</span>' + (html.escape(colon) if colon else ""))
        elif num is not None:
            out.append(f'<span class="t-n">{num}</span>')
        elif kw is not None:
            out.append(f'<span class="t-b">{kw}</span>')
        else:
            out.append(html.escape(punct or ws or other))
    return "".join(out)


def hl_generic(src, lang):
    esc = html.escape(src)
    if lang in ("javascript", "python", "bash"):
        cm = r"(//[^\n]*|#[^\n!]*$)" if lang != "bash" else r"(^\s*#[^\n]*)"
        esc = re.sub(r'(&quot;[^&\n]*?&quot;|`[^`\n]*`|&#x27;[^\n]*?&#x27;)', r'<span class="t-s">\1</span>', esc)
        esc = re.sub(r'(?m)' + cm, r'<span class="t-c">\1</span>', esc)
    if lang == "http":
        esc = re.sub(r'(?m)^(GET|POST|PUT|DELETE|HTTP/1\.1)( [^\n]*)?$', r'<span class="t-k">\1</span>\2', esc)
        esc = re.sub(r'(?m)^([A-Za-z-]+)(:) ', r'<span class="t-h">\1</span>\2 ', esc)
    return esc


def code_block(name):
    lang, src = CODE[name]
    body = hl_json(src) if lang == "json" else hl_generic(src, lang)
    return (f'<figure class="code"><figcaption><span>{lang.upper() if lang != "javascript" else "JAVASCRIPT"}</span>'
            f'<button type="button" class="copy" data-copy>COPY</button></figcaption>'
            f'<pre><code>{body}</code></pre></figure>')


# ---------- endpoint rows ----------
def endpoints(rows):
    out = ['<div class="eps">']
    for m, path, desc in rows:
        out.append(f'<div class="ep"><span class="m m-{m.lower()}">{m}</span><code class="p">{html.escape(path)}</code><span class="d">{desc}</span></div>')
    out.append("</div>")
    return "".join(out)


def table(head, rows, cls=""):
    th = "".join(f"<th>{h}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tbl {cls}"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


# ---------- assemble ----------
def render_lang(lang):
    src = open(f"content_{lang}.html", encoding="utf-8").read()
    src = src.replace('id="§', f'id="{lang}-')
    src = re.sub(r"\{CODE:(\w+)\}", lambda m: code_block(m.group(1)), src)
    # TOC from h2
    toc = []
    for m in re.finditer(r'<h2 id="([^"]+)"[^>]*>(.*?)</h2>', src):
        toc.append(f'<li><a href="#{m.group(1)}">{re.sub("<[^>]+>", "", re.sub(r'<span class="n">.*?</span>', "", m.group(2)))}</a></li>')
    return src, "".join(toc)


def main():
    css = open("page.css", encoding="utf-8").read()
    swagger_css = open("package/swagger-ui.css", encoding="utf-8").read()
    specs = {l: build(l) for l, _, _ in LANGS}
    yamls = {l: yaml.safe_dump(specs[l], allow_unicode=True, sort_keys=False, width=110) for l in specs}
    shell = open("shell.html", encoding="utf-8").read()
    blocks, tocs = [], []
    for l, bcp, _ in LANGS:
        body, toc = render_lang(l)
        blocks.append(f'<div class="lang" data-lang="{l}" lang="{bcp}">{body}</div>')
        tocs.append(f'<ol class="toc-list" data-lang="{l}" lang="{bcp}">{toc}</ol>')
    page = (shell.replace("/*CSS*/", css)
                 .replace("/*SWAGGERCSS*/", swagger_css)
                 .replace("<!--CONTENT-->", "\n".join(blocks))
                 .replace("<!--TOC-->", "\n".join(tocs))
                 .replace("/*SPECS*/", "window.PHIZ_SPECS=" + json.dumps(specs, ensure_ascii=False).replace("</", "<\\/") + ";"
                          + "window.PHIZ_YAML=" + json.dumps(yamls, ensure_ascii=False).replace("</", "<\\/") + ";"))
    open("out/rfc-phiz-business-messaging-api.html", "w", encoding="utf-8").write(page)
    print("bytes", len(page.encode()))


if __name__ == "__main__":
    main()
