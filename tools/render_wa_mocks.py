#!/usr/bin/env python3
"""Render the WhatsApp reference screens (EN source) to PNG in en/pt/zh.

usage: render_wa_mocks.py <whatsapp-design dir> <out mocks dir>
  e.g. python3 tools/render_wa_mocks.py sources/PHZ-0001/whatsapp-design rfcs/PHZ-0001/mocks

Writes <out>/<lang>/whatsapp/<name>.png. The design files are written in English;
i18n.json maps each text to [pt, zh]. Two kinds of keys:
  - the inner HTML of an element that mixes text with <b>/<em>/<code>/<strong>
    (translated as a whole, so word order can change),
  - a single text node, input value or placeholder.
Anything without a key (names, numbers, codes) is kept as is.
Needs playwright (chromium), beautifulsoup4 and a CJK font (Noto Sans CJK SC) for zh.
"""
import json, re, sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag
from playwright.sync_api import sync_playwright

SRC, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
I18N = json.loads((SRC / "i18n.json").read_text(encoding="utf-8"))
CSS = (SRC / "wa.css").read_text(encoding="utf-8")
NAMES = {
    "A02_Phone": "a02-phone-number", "A10_Chats": "a10-chats-home",
    "O00_Consent": "o00-consent-lifecycle", "O01_AppToggle": "o01-optin-app", "O02_Signup": "o02-optin-signup",
    "O03_UserStarts": "o03-user-starts", "O04_InChat": "o04-optin-in-chat", "O05_Record": "o05-consent-record",
    "O06_WhoVerifies": "o06-who-verifies", "B01_Architecture": "b01-architecture", "B02_Rules": "b02-sending-rules",
    "C01_Notification": "c01-notification", "C02_ChatList": "c02-chat-list", "C03_Utility": "c03-utility", "C04_Marketing": "c04-marketing",
    "C05_Auth": "c05-authentication", "C06_Bill": "c06-bill", "D00_Map": "d00-options-map",
    "D02_QuickReply": "d02-quick-reply", "D04_List": "d04-list", "D05_Flow": "d05-flow",
    "D07_Preferences": "d07-stop-offers", "D08_Block": "d08-block-report", "D10_OptOut": "d10-optout-keyword",
}
LANGS = {"en": (None, "en"), "pt": (0, "pt-BR"), "zh": (1, "zh-CN")}
INLINE = {"b", "em", "code", "strong"}
FONT = {"en": "'Noto Sans',sans-serif", "pt": "'Noto Sans',sans-serif",
        "zh": "'Noto Sans CJK SC','Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif"}


def is_rich(el):
    kids = [c for c in el.children if isinstance(c, Tag)]
    has_text = any(isinstance(c, NavigableString) and c.strip() for c in el.children)
    return has_text and kids and all(k.name in INLINE for k in kids)


def translate(html, idx):
    soup = BeautifulSoup(html, "html.parser")
    if idx is None:
        return str(soup)
    for el in list(soup.find_all(True)):
        if el.name in INLINE or el.name == "svg" or el.find_parent("svg") or not is_rich(el):
            continue
        key = el.decode_contents().strip()
        if key in I18N:
            el.clear()
            el.append(BeautifulSoup(I18N[key][idx], "html.parser"))
            el["data-done"] = "1"
    for ns in list(soup.find_all(string=True)):
        if ns.find_parent("svg") or ns.find_parent(attrs={"data-done": "1"}):
            continue
        core = ns.strip()
        if core in I18N:
            lead, trail = ns[:len(ns) - len(ns.lstrip())], ns[len(ns.rstrip()):]
            ns.replace_with(lead + I18N[core][idx] + trail)
    for el in soup.find_all("input"):
        for a in ("value", "placeholder"):
            if el.get(a) in I18N:
                el[a] = I18N[el[a]][idx]
    return str(soup)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(device_scale_factor=1.5)
    for lang, (idx, bcp) in LANGS.items():
        out = OUT / lang / "whatsapp"
        out.mkdir(parents=True, exist_ok=True)
        for src, name in NAMES.items():
            text = (SRC / f"{src}.dc.html").read_text(encoding="utf-8")
            width = int(re.search(r'"\$preview":\{"width":(\d+)', text).group(1))
            body = re.search(r"<x-dc>(.*?)</x-dc>", text, re.S).group(1)
            body = translate(re.sub(r"<helmet>.*?</helmet>", "", body, flags=re.S), idx)
            style = (f"body{{margin:0}}{CSS} .ab,.wide{{height:auto!important;padding-bottom:28px!important;"
                     f"font-family:{FONT[lang]}!important}}")
            html = f'<!doctype html><html lang="{bcp}"><head><meta charset="utf-8"><style>{style}</style></head><body>{body}</body></html>'
            tmp = out / f"{name}.html"
            tmp.write_text(html, encoding="utf-8")
            page.set_viewport_size({"width": width, "height": 400})
            page.goto(tmp.as_uri())
            page.wait_for_timeout(150)
            page.screenshot(path=str(out / f"{name}.png"), full_page=True)
            tmp.unlink()
            print(lang, name, flush=True)
    browser.close()
