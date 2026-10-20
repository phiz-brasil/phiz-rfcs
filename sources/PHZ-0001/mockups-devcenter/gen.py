"""Mockups da seção 12 (v1.5) no visual da Central do Desenvolvedor PHIZ."""
import os, sys, asyncio
HERE = os.path.dirname(os.path.abspath(__file__))
FS = HERE + '/node_modules/@fontsource'
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE + '/out'
LANGS = ['pt', 'en', 'zh']
L = 'pt'
def T(pt, en, zh):
    return {'pt': pt, 'en': en, 'zh': zh}[L]

def css():
    f = lambda fam, w: f"@font-face{{font-family:'{fam}';font-weight:{w};src:url('file://{FS}/{fam.lower().replace(' ','-')}/files/{fam.lower().replace(' ','-')}-latin-{w}-normal.woff2')}}"
    return ''.join(f('IBM Plex Sans', w) for w in (400, 500, 600, 700)) + ''.join(f('IBM Plex Mono', w) for w in (400, 500)) + """
*{box-sizing:border-box}
body{margin:0;width:1440px;font-family:'IBM Plex Sans','Noto Sans CJK SC','Noto Sans CJK TC',sans-serif;color:#1f2328;background:#fff;font-size:14px;line-height:1.45}
.mono{font-family:'IBM Plex Mono','Noto Sans CJK SC',monospace;font-size:13px}
.app{display:flex;min-height:960px;position:relative}
.rail{flex:0 0 80px;border-right:1px solid #e8e8e8;display:flex;flex-direction:column;align-items:center;background:#fff}
.rail .logo{height:64px;display:flex;align-items:center;justify-content:center;border-bottom:1px solid #e8e8e8;width:100%}
.rail .ic{width:54px;height:38px;border-radius:9px;display:flex;align-items:center;justify-content:center;margin-top:6px;color:#3b4148;position:relative}
.rail .ic.on{background:#efefef}
.rail .ic .dot{position:absolute;top:6px;right:9px;width:8px;height:8px;border-radius:50%;background:#16a34a;border:2px solid #fff}
.main{flex:1;min-width:0}
.top{height:64px;border-bottom:1px solid #e8e8e8;display:flex;align-items:center;padding:0 28px;gap:16px}
.crumb{color:#59636e;font-size:14px}.crumb b{color:#1f2328;font-weight:500}
.top .sp{flex:1}
.ibtn{border:1px solid #d9dce0;border-radius:7px;height:32px;padding:0 10px;display:flex;align-items:center;gap:6px;font-size:13px;color:#1f2328;background:#fff}
.ava{width:26px;height:26px;border-radius:50%;background:#f0f0f0;display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:13px}
.page{padding:28px 36px 40px}
h1{font-size:26px;font-weight:600;margin:0 0 6px;letter-spacing:-.01em}
.sub{color:#59636e;margin:0}
.row{display:flex;gap:16px}
.card{border:1px solid #e3e5e8;border-radius:10px;padding:18px 20px;background:#fff}
.stat .n{font-size:24px;font-weight:600}.stat .l{margin-top:4px}.stat .d{color:#6e7781;margin-top:8px;font-size:13px}
.btn{background:#111;color:#fff;border-radius:7px;padding:8px 16px;font-weight:500;font-size:14px;display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.btn2{background:#fff;color:#1f2328;border:1px solid #d9dce0;border-radius:7px;padding:7px 14px;font-weight:500;font-size:14px;display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.red{color:#d93025}.green{color:#15803d}.muted{color:#6e7781}
.tag{display:inline-flex;align-items:center;gap:5px;border-radius:6px;padding:1px 8px;font-size:12px;font-weight:500;border:1px solid;white-space:nowrap}
.t-ok{color:#15803d;border-color:#b7e3c4;background:#f0faf3}.t-warn{color:#b45309;border-color:#f5d39b;background:#fff8eb}
.t-off{color:#59636e;border-color:#d9dce0;background:#f6f7f8}.t-err{color:#c5221f;border-color:#f3b8b4;background:#fff4f3}
.t-new{color:#1d4ed8;border-color:#bfd2fb;background:#f0f5ff}.t-dark{color:#fff;border-color:#111;background:#111}
table.tb{width:100%;border-collapse:collapse}
.tb th{font-family:'IBM Plex Mono','Noto Sans CJK SC',monospace;font-weight:500;font-size:12px;color:#59636e;text-align:left;padding:12px;background:#fafafa;border-bottom:1px solid #e3e5e8}
.tb td{padding:14px 12px;border-bottom:1px solid #eef0f2;vertical-align:middle}
.aname{display:flex;align-items:center;gap:10px}.aname .sq{width:36px;height:36px;border-radius:6px;background:#9aa1a9;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:600}
.aname .id{color:#6e7781;font-size:12.5px}
.sec{font-family:'IBM Plex Mono','Noto Sans CJK SC',monospace;font-size:13px;font-weight:500;letter-spacing:.02em;color:#3b4148;margin:26px 0 12px}
.hr{border-top:1px solid #e8e8e8;margin:22px 0}
.kv{display:grid;grid-template-columns:repeat(3,1fr);gap:16px 20px}.kv .k{font-size:12px;color:#59636e}.kv .v{margin-top:3px}
.chip{display:inline-flex;align-items:center;gap:8px;border:1px solid #e3e5e8;border-radius:7px;padding:6px 10px;background:#fafafa;margin:0 8px 8px 0}
.code{background:#16191d;color:#e6e6e6;border-radius:8px;padding:14px 16px;font-family:'IBM Plex Mono',monospace;font-size:12.5px;line-height:1.7;white-space:pre}
.field{margin-bottom:16px}.field .fl{font-weight:500;margin-bottom:6px}.field .hint{color:#6e7781;font-size:12.5px;margin-top:5px}
.inp{border:1px solid #d9dce0;border-radius:7px;padding:8px 12px;background:#fff;min-height:36px;display:flex;align-items:center;justify-content:space-between}
.seg{display:inline-flex;border:1px solid #d9dce0;border-radius:8px;padding:3px;gap:2px}.seg span{padding:5px 14px;border-radius:6px;color:#59636e}.seg .a{background:#111;color:#fff}
.cb{display:flex;align-items:flex-start;gap:10px;padding:9px 0}.cb .box{flex:0 0 16px;height:16px;border:1.5px solid #9aa1a9;border-radius:4px;margin-top:2px;display:flex;align-items:center;justify-content:center}
.cb .box.on{background:#111;border-color:#111}.cb .box.on:after{content:'';width:8px;height:4px;border:2px solid #fff;border-top:0;border-right:0;transform:rotate(-45deg) translate(1px,-1px)}
.cb.dis{opacity:.5}
.overlay{position:absolute;inset:0;background:rgba(17,17,17,.42)}
.drawer{position:absolute;top:0;right:0;bottom:0;background:#fff;box-shadow:-8px 0 24px rgba(0,0,0,.12);padding:0 32px 32px;overflow:hidden}
.drawer .dh{height:64px;display:flex;align-items:center;gap:14px;font-size:17px;font-weight:600;border-bottom:1px solid #eee;margin:0 -32px 22px;padding:0 32px}
.foot{display:flex;justify-content:flex-end;gap:10px;margin-top:20px}
.note{border:1px solid #f5d39b;background:#fff8eb;border-radius:8px;padding:10px 14px;color:#7c4a03}
.info{border:1px solid #bfd2fb;background:#f0f5ff;border-radius:8px;padding:10px 14px;color:#1e3a8a}
.bar{display:flex;align-items:flex-end;gap:10px;height:110px;border-bottom:1px solid #e3e5e8;padding:0 4px}
.bar div{flex:1;background:#1f2328;border-radius:2px 2px 0 0}
"""

ICONS = ['<path d="M4 15a8 8 0 1 1 16 0"/><path d="M12 15l4-4"/>',
         '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6"/><path d="M15 14l2 2 4-4"/>',
         '<rect x="4" y="4" width="6" height="6"/><rect x="14" y="4" width="6" height="6"/><rect x="4" y="14" width="6" height="6"/><rect x="14" y="14" width="6" height="6"/>',
         '<circle cx="15" cy="9" r="4"/><path d="M12 12l-7 7"/><path d="M7 17l2 2"/>',
         '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
         '<rect x="5" y="3" width="12" height="18" rx="1"/><path d="M8 8h6M8 12h6M8 16h3"/>',
         '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/>',
         '<path d="M4 20V4M4 20h16M8 16v-5M12 16V8M16 16v-7"/>',
         '<path d="M13 3L5 13h6l-1 8 8-10h-6z"/>',
         '<path d="M6 16V11a6 6 0 1 1 12 0v5l2 2H4z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
         '<path d="M3 11l14-6v14L3 13z"/><path d="M7 13v5h3"/>',
         '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"/>',
         ]
SENDER_IC = '<path d="M4 5h16v10H8l-4 4z"/><path d="M8 9h8M8 12h5"/>'
LOGO = '<svg width="30" height="30" viewBox="0 0 30 30"><path d="M5 3h20a3 3 0 0 1 3 3v15a3 3 0 0 1-3 3H11l-6 4v-4a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3z" fill="#21c063"/><circle cx="11" cy="11" r="1.6" fill="#fff"/><circle cx="19" cy="11" r="1.6" fill="#fff"/><path d="M10 16c3 3 7 3 10 0" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round"/></svg>'

def svg(p, s=18):
    return f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{p}</svg>'

# menu order: painel, membros, aplicacoes, chaves, permissao, auditoria, scope, uso, assinaturas, webhook, notificacoes, perfil  (+ remetentes, novo, after aplicacoes)
def shell(active, crumb, body, extra='', minh=960):
    items = []
    keys = ['painel', 'membros', 'apps', 'remet', 'chaves', 'perm', 'audit', 'scope', 'uso', 'assin', 'webhook', 'notif', 'perfil']
    icons = ICONS[:3] + [SENDER_IC] + ICONS[3:]
    for k, ic in zip(keys, icons):
        dot = '<span class="dot"></span>' if k == 'remet' else ''
        items.append(f'<div class="ic{" on" if k == active else ""}">{svg(ic)}{dot}</div>')
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>{css()}</style></head><body>
<div class="app" style="min-height:{minh}px"><aside class="rail"><div class="logo">{LOGO}</div><div style="height:6px"></div>{''.join(items)}</aside>
<div class="main"><div class="top">{svg('<path d="M4 6h16M4 12h10M4 18h16"/>')}<div class="crumb">{T('Central do Desenvolvedor PHIZ','PHIZ Developer Center','PHIZ开发者中心')} &nbsp;/&nbsp; <b>{crumb}</b></div><div class="sp"></div>
<div class="ibtn">{svg('<path d="M6 16V11a6 6 0 1 1 12 0v5l2 2H4z"/>',15)}</div><div class="ibtn">{svg('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',15)} {T('Português (BR)','English (US)','简体中文')}</div>
<span class="ava">G</span><b style="font-weight:600">gleison</b></div>
<div class="page">{body}</div></div>{extra}</div></body></html>'''

def stats(items):
    return '<div class="row" style="margin:22px 0">' + ''.join(f'<div class="card stat" style="flex:1"><div class="n">{n}</div><div class="l">{l}</div><div class="d">{d}</div></div>' for n, l, d in items) + '</div>'

def app_cell(letter, name=None, aid=None, color='#9aa1a9'):
    if callable(letter): letter, name, aid, color = letter()
    return f'<div class="aname"><div class="sq" style="background:{color}">{letter}</div><div><b style="font-weight:600">{name}</b><div class="id mono">{aid}</div></div></div>'

BLIP = ('B', 'Blip · Atendimento', 'app_9d31c0a7f2b4e1c8a6d0', '#2f6fde')
SF = ('S', 'Salesforce · Marketing', 'app_51ab07e3c9d24f1a8b77', '#0b8bd6')
BO = lambda: ('B', T('Backoffice interno', 'Internal back office', '内部后台'), 'app_c03e4fa1b8d9726e5a14', '#6b7280')
STORE = lambda: T('Loja Exemplo', 'Example Store', '示例商店')
OFFERS = lambda: T('Loja Exemplo · Ofertas', 'Example Store · Offers', '示例商店 · 优惠')
NEWS = lambda: T('Loja Exemplo · Novidades', 'Example Store · News', '示例商店 · 新品')

# ------------------------------------------------------------------ 01 Painel
def s01():
    ck = lambda done, txt, extra='': f'<div class="cb" style="padding:10px 0;border-bottom:1px solid #f0f1f3"><span class="box{" on" if done else ""}"></span><div style="flex:1">{txt}</div>{extra}</div>'
    hero = f'''<div style="background:#0d0d0d;color:#fff;border-radius:10px;padding:24px 26px;margin-top:22px">
<div style="display:flex;align-items:center;gap:12px"><span style="font-size:21px;font-weight:600">{STORE()}</span><span class="tag" style="color:#4ade80;border-color:#14532d;background:#0d1f13">● {T('Em operação','Operating','运营中')}</span><span class="tag" style="color:#e5e7eb;border-color:#374151;background:#111">{T('Organização verificada','Verified organization','已认证组织')}</span></div>
<div style="display:flex;gap:28px;margin-top:16px;font-size:13px;color:#a3a3a3">
<span>{T('ID da organização','Organization ID','组织 ID')} <b style="color:#fff;font-weight:500" class="mono">org_7b1e4c5291d04a6e</b></span>
<span>{T('ID do comerciante','Merchant ID','商户 ID')} <b style="color:#fff;font-weight:500" class="mono">7b1e4c52-91d0-4a6e-b3f8-2c5d9a0e7f14</b></span>
<span>{T('Responsável','Owner','负责人')} <b style="color:#fff;font-weight:500">gleison</b></span></div>
<div style="display:flex;gap:28px;margin-top:10px;font-size:13px;color:#a3a3a3"><span>{T('Membros','Members','成员')} <b style="color:#fff">4</b></span><span>{T('Aplicações','Applications','应用')} <b style="color:#fff">4</b></span><span>{T('Remetentes','Senders','发送方')} <b style="color:#fff">3</b></span></div>
<div style="margin-top:18px;display:flex;gap:10px"><span class="btn2" style="background:#0d0d0d;color:#fff;border-color:#4b5563">{T('Gerenciar aplicações','Manage applications','管理应用')} ›</span><span class="btn2" style="background:#0d0d0d;color:#fff;border-color:#4b5563">{T('Remetentes','Senders','发送方')} ›</span></div></div>'''
    st = stats([('12.480', T('Mensagens enviadas','Messages sent','已发送消息'), T('Últimas 24 h · Business Messaging','Last 24 h · Business Messaging','最近 24 小时 · Business Messaging')),
                ('98,6%', T('Entregues','Delivered','已送达'), T('12.311 de 12.480','12,311 of 12,480','12,311 / 12,480')),
                ('37', T('Com falha','Failed','失败'), T('Principal causa: 2201 usuário bloqueou','Top cause: 2201 user blocked','主要原因：2201 用户已屏蔽')),
                ('99,2%', T('Webhooks entregues','Webhooks delivered','Webhook 投递成功'), T('9 falhas em Salesforce · Marketing','9 failures in Salesforce · Marketing','Salesforce · Marketing 有 9 次失败'))])
    left = f'''<div class="card" style="flex:1.25"><div style="display:flex;justify-content:space-between;align-items:center"><b style="font-size:16px;font-weight:600">{T('Business Messaging API · primeiros passos','Business Messaging API · getting started','Business Messaging API · 快速开始')}</b><span class="tag t-new">{T('Novo','New','新')}</span></div>
<p class="muted" style="margin:6px 0 10px">{T('Para enviar mensagens a usuários PhizChat pelo seu sistema ou por um parceiro (Blip, Salesforce).','To send messages to PhizChat users from your own system or through a partner (Blip, Salesforce).','通过自有系统或合作伙伴（Blip、Salesforce）向 PhizChat 用户发送消息。')}</p>
{ck(True, T('Criar uma aplicação do tipo <b>Business Messaging</b>','Create a <b>Business Messaging</b> application','创建 <b>Business Messaging</b> 类型的应用'))}
{ck(True, T('Solicitar os scopes <span class="mono">messages:send</span> e <span class="mono">messages:read</span>','Request the <span class="mono">messages:send</span> and <span class="mono">messages:read</span> scopes','申请 <span class="mono">messages:send</span> 和 <span class="mono">messages:read</span> 范围'), f'<span class="tag t-ok">{T("Aprovado","Approved","已批准")}</span>')}
{ck(True, T('Escolher os remetentes que a aplicação pode usar','Choose which senders the application can use','选择应用可使用的发送方'))}
{ck(False, T('Assinar os eventos <span class="mono">messages</span> e <span class="mono">message_status</span>','Subscribe to the <span class="mono">messages</span> and <span class="mono">message_status</span> events','订阅 <span class="mono">messages</span> 和 <span class="mono">message_status</span> 事件'), f'<span class="btn2" style="padding:3px 10px;font-size:13px">{T("Assinar","Subscribe","订阅")}</span>')}
{ck(False, T('Enviar a primeira mensagem','Send the first message','发送第一条消息'))}
<div style="margin-top:16px" class="muted">{T('URL base','Base URL','基础 URL')}</div>
<div class="inp mono" style="margin-top:6px">https://gateway.phiz.chat/gateway/business<span class="muted" style="font-family:'IBM Plex Sans'">{T('Copiar','Copy','复制')}</span></div></div>'''
    bars = ''.join(f'<div style="height:{h}%"></div>' for h in (40, 52, 48, 61, 70, 66, 74, 69, 82, 78, 88, 85, 92, 96))
    right = f'''<div style="flex:1;display:flex;flex-direction:column;gap:16px"><div class="card"><b style="font-weight:600">{T('Alertas','Alerts','提醒')}</b>
<div class="note" style="margin-top:12px">{T('O segredo anterior de <b>Blip · Atendimento</b> ainda está em uso e expira em 6 dias.','The previous secret of <b>Blip · Atendimento</b> is still in use and expires in 6 days.','<b>Blip · Atendimento</b> 的旧密钥仍在使用，将于 6 天后过期。')}</div>
<div class="note" style="margin-top:8px;border-color:#f3b8b4;background:#fff4f3;color:#9b1c1c">{T('<b>Salesforce · Marketing</b>: 9 entregas de webhook com falha desde 10:02.','<b>Salesforce · Marketing</b>: 9 failed webhook deliveries since 10:02.','<b>Salesforce · Marketing</b>：自 10:02 起 9 次 Webhook 投递失败。')} <u>{T('Ver entregas','View deliveries','查看投递')}</u></div></div>
<div class="card"><div style="display:flex;justify-content:space-between"><b style="font-weight:600">{T('Mensagens enviadas','Messages sent','已发送消息')}</b><span class="mono muted">14 {T('dias','days','天')}</span></div><div class="bar" style="margin-top:14px">{bars}</div>
<div style="display:flex;justify-content:space-between;margin-top:6px" class="mono muted"><span>10-07</span><span>10-20</span></div></div></div>'''
    body = f'''<h1>{T('Boa tarde, gleison','Good afternoon, gleison','下午好，gleison')}</h1><p class="sub">{T('terça-feira, 20 de outubro · 1 pendência hoje','Tuesday, October 20 · 1 pending item today','10 月 20 日 星期二 · 今日 1 项待办')}</p>{hero}{st}<div class="row">{left}{right}</div>'''
    return shell('painel', T('Painel', 'Dashboard', '仪表盘'), body)

# ------------------------------------------------------------------ Aplicações (fundo)
def apps_page():
    rows = ''
    for a, sc, cb, rem, stt in [(BLIP, 3, 1, 2, ('t-ok', T('Em execução', 'Running', '运行中'))),
                                 (SF, 2, 1, 1, ('t-ok', T('Em execução', 'Running', '运行中'))),
                                 (BO, 1, 0, 1, ('t-warn', T('Em análise', 'In review', '审核中')))]:
        rows += f'<tr><td>{app_cell(*(a if isinstance(a, tuple) else (a,)))}</td><td><span class="tag t-new">Business Messaging</span></td><td class="muted" style="font-size:12.5px">Scopes {sc}<br>{T("Remetentes","Senders","发送方")} {rem}<br>Callbacks {cb}</td><td><span class="tag {stt[0]}">{stt[1]}</span></td><td class="mono muted">2026-10-20 09:12</td><td>{T("Detalhes","Details","详情")} &nbsp; {T("Editar","Edit","编辑")}</td></tr>'
    return f'''<div style="display:flex;justify-content:space-between;align-items:flex-start"><div><h1>{T('Aplicações','Applications','应用')}</h1><p class="sub">{T('Gerencie ciclo de vida, callbacks, listas de permissão, scopes e rotação de chaves.','Manage lifecycle, callbacks, allowlists, scopes and key rotation.','管理生命周期、回调、白名单、范围和密钥轮换。')}</p></div><span class="btn">＋ {T('Nova aplicação','New application','新建应用')}</span></div>
{stats([('4', T('Total de aplicações','Total applications','应用总数'), ''), ('3', T('Em execução','Running','运行中'), ''), ('1', T('Em análise','In review','审核中'), ''), ('0', T('Desativadas','Disabled','已停用'), '')])}
<div class="card" style="padding:0;overflow:hidden"><table class="tb"><tr><th>{T('Nome da aplicação','Application name','应用名称')}</th><th>{T('Tipo','Type','类型')}</th><th>{T('Acesso','Access','访问')}</th><th>Status</th><th>{T('Atualizado em','Updated at','更新时间')}</th><th>{T('Ações','Actions','操作')}</th></tr>{rows}</table></div>'''

# ------------------------------------------------------------------ 02 Nova aplicação
def s02():
    cb = lambda on, t, h='', dis=False: f'<div class="cb{" dis" if dis else ""}"><span class="box{" on" if on else ""}"></span><div><div>{t}</div>{f"<div class=muted style=font-size:12.5px>{h}</div>" if h else ""}</div></div>'
    drawer = f'''<div class="overlay"></div><div class="drawer" style="width:700px"><div class="dh">✕ &nbsp;{T('Nova aplicação','New application','新建应用')}</div>
<div class="field"><div class="fl">{T('Nome da aplicação','Application name','应用名称')}</div><div class="inp">Blip · Atendimento</div></div>
<div class="field"><div class="fl">{T('Tipo de aplicação','Application type','应用类型')}</div><div class="seg"><span>{T('Padrão','Standard','标准')}</span><span class="a">Business Messaging</span></div><div class="hint">{T('Business Messaging libera a API de mensagens (envio para telefone ou PHIZ ID, mídia e webhooks).','Business Messaging enables the messaging API (send to phone or PHIZ ID, media and webhooks).','Business Messaging 开通消息 API（向手机号或 PHIZ ID 发送、媒体和 Webhook）。')}</div></div>
<div class="row"><div class="field" style="flex:1"><div class="fl">{T('Tipo de integração','Integration type','集成类型')}</div><div class="inp">Blip <span class="muted">▾</span></div><div class="hint">{T('Própria, Blip, Salesforce ou outra','Own, Blip, Salesforce or other','自有、Blip、Salesforce 或其他')}</div></div>
<div class="field" style="flex:1"><div class="fl">{T('Ambiente','Environment','环境')}</div><div class="seg"><span>TEST</span><span>SANDBOX</span><span class="a">PRODUCTION</span></div><div class="hint">{T('PRODUCTION exige organização verificada','PRODUCTION requires a verified organization','PRODUCTION 需要已认证组织')}</div></div></div>
<div class="sec">SCOPES</div>
{cb(True, '<span class="mono">messages:send</span>', T('Enviar mensagens e mídias, marcar como lidas','Send messages and media, mark as read','发送消息和媒体，标记已读'))}
{cb(True, '<span class="mono">messages:read</span>', T('Consultar status de mensagens','Look up message status','查询消息状态'))}
{cb(True, '<span class="mono">account:read</span>', T('Ler dados da conta e dos remetentes','Read account and sender data','读取账户和发送方信息'))}
{cb(False, '<span class="mono">webhooks:manage</span> <span class="tag t-off">' + T('Fase 2','Phase 2','第 2 阶段') + '</span>', T('Configurar webhook pela API','Configure the webhook through the API','通过 API 配置 Webhook'), True)}
<div class="info" style="margin-top:6px">{T('Os scopes são solicitados agora e aprovados pela plataforma. Enquanto pendentes, o token não os inclui.','Scopes are requested now and approved by the platform. While pending, the token does not include them.','范围在此申请，由平台审批。审批前令牌不包含这些范围。')}</div>
<div class="sec">{T('REMETENTES PERMITIDOS','ALLOWED SENDERS','可用发送方')}</div>
{cb(True, f'<b style="font-weight:600">{STORE()}</b> · ' + T('Mensagem direta','Direct message','直接消息') + f' <span class="tag t-off">{T("Padrão","Default","默认")}</span>', T('Conversa direta com a loja, sem canal','Direct conversation with the store, no channel','与商户的直接对话，无需频道'))}
{cb(True, f'<b style="font-weight:600">{OFFERS()}</b>', T('Canal 1231 · 2 inscritos','Channel 1231 · 2 subscribers','频道 1231 · 2 位订阅者'))}
{cb(False, f'<b style="font-weight:600">{NEWS()}</b>', T('Canal 1288 · 540 inscritos','Channel 1288 · 540 subscribers','频道 1288 · 540 位订阅者'))}
<div class="sec">{T('LISTA DE IPS (OPCIONAL)','IP ALLOWLIST (OPTIONAL)','IP 白名单（可选）')}</div>
<div class="inp mono" style="min-height:58px;align-items:flex-start">52.67.10.0/24<br>18.231.4.12</div>
<div class="foot"><span class="btn2">{T('Cancelar','Cancel','取消')}</span><span class="btn">{T('Criar aplicação','Create application','创建应用')}</span></div></div>'''
    return shell('apps', T('Aplicações', 'Applications', '应用'), apps_page(), drawer, 1270)

# ------------------------------------------------------------------ 03 Detalhes
def detail_body():
    sk = lambda key, ver, since, used, tag: f'<div class="card" style="padding:12px 16px;margin-bottom:8px;display:flex;align-items:center;gap:16px"><div style="flex:1"><b class="mono" style="font-weight:500">{key}</b><div class="muted" style="font-size:12.5px">{ver} · {since} · {used}</div></div>{tag}</div>'
    return f'''<div style="display:flex;align-items:center;gap:14px"><div class="aname"><div class="sq" style="background:#2f6fde;width:46px;height:46px;font-size:18px">B</div></div><span style="font-size:21px;font-weight:600">Blip · Atendimento</span><span class="mono muted">(app_9d31c0a7f2b4e1c8a6d0 ⧉)</span><span class="green" style="font-size:13px">● {T('Em execução','Running','运行中')}</span><span class="tag t-new">Business Messaging</span><span class="tag t-dark">PRODUCTION</span></div>
<p class="muted" style="margin:8px 0 18px">{T('Atendimento ao cliente pela Blip','Customer service through Blip','通过 Blip 提供客服')}</p>
<div class="card"><div class="kv"><div><div class="k">{T('Organização','Organization','组织')}</div><div class="v">{STORE()}</div></div><div><div class="k">{T('Responsável','Owner','负责人')}</div><div class="v">gleison</div></div><div><div class="k">{T('Tipo de integração','Integration type','集成类型')}</div><div class="v">Blip</div></div>
<div><div class="k">App ID (client_id)</div><div class="v mono">app_9d31c0a7f2b4e1c8a6d0</div></div><div><div class="k">{T('URL do token','Token URL','令牌 URL')}</div><div class="v mono">…/gateway/business/oauth/token</div></div><div><div class="k">Grant</div><div class="v mono">client_credentials</div></div></div></div>
<div class="sec">{T('Configuração de acesso','Access configuration','访问配置')}</div>
<div class="row"><div style="flex:1"><div class="muted" style="margin-bottom:8px">{T('Permissões de scope','Scope permissions','范围权限')}</div>
<span class="chip"><span class="mono">messages:send</span><span class="tag t-ok">{T('Aprovado','Approved','已批准')}</span></span><span class="chip"><span class="mono">messages:read</span><span class="tag t-ok">{T('Aprovado','Approved','已批准')}</span></span><span class="chip"><span class="mono">account:read</span><span class="tag t-warn">{T('Pendente de aprovação','Pending approval','待审批')}</span></span></div>
<div style="flex:1"><div class="muted" style="margin-bottom:8px">{T('Remetentes permitidos','Allowed senders','可用发送方')} <span class="tag t-new">{T('Novo','New','新')}</span></div>
<div class="card" style="padding:10px 14px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center"><div><b style="font-weight:600">{STORE()}</b> · {T('Mensagem direta','Direct message','直接消息')}<div class="mono muted" style="font-size:12px">sender_id 7b1e4c52-91d0-4a6e…</div></div><span class="tag t-ok">{T('Responsável pelas conversas','Owns conversations','负责会话')}</span></div>
<div class="card" style="padding:10px 14px;display:flex;justify-content:space-between;align-items:center"><div><b style="font-weight:600">{OFFERS()}</b><div class="mono muted" style="font-size:12px">sender_id 1231</div></div><span class="tag t-off">{T('Só envio','Send only','仅发送')}</span></div></div></div>
<div class="sec">{T('Segredo da aplicação','Application secret','应用密钥')}</div>
{sk('phzsk_live_••••••••3f9a', 'v2', T('Vigente desde 2026-10-20 14:30','Active since 2026-10-20 14:30','2026-10-20 14:30 起生效'), T('último uso há 2 min','last used 2 min ago','2 分钟前使用'), f'<span class="tag t-ok">{T("Em vigor","Active","生效中")}</span>')}
{sk('phzsk_live_••••••••b27c', 'v1', T('Expira em 2026-10-27 14:30','Expires 2026-10-27 14:30','2026-10-27 14:30 过期'), T('último uso há 1 h','last used 1 h ago','1 小时前使用'), f'<span class="tag t-warn">{T("Em tolerância · 6 dias","Grace period · 6 days","宽限期 · 6 天")}</span> <span class="red">{T("Revogar agora","Revoke now","立即撤销")}</span>')}
<div style="display:flex;gap:18px;margin:10px 0 4px"><span>⟳ {T('Rotacionar','Rotate','轮换')}</span><span class="red">{T('Revogar','Revoke','撤销')}</span></div>
<p class="muted" style="font-size:12.5px;margin:0">{T('Só o segredo mascarado é exibido. Ao rotacionar, o anterior continua válido durante a tolerância (até 7 dias), para trocar sem interromper o envio.','Only the masked secret is shown. When rotating, the previous one stays valid during the grace period (up to 7 days), so you can switch without stopping sends.','仅显示掩码密钥。轮换后旧密钥在宽限期内（最长 7 天）仍有效，切换不中断发送。')}</p>
<div class="sec">{T('Testar o token','Test the token','测试令牌')}</div>
<div class="code">curl -X POST "https://gateway.phiz.chat/gateway/business/oauth/token" \\
  -d "grant_type=client_credentials" \\
  -d "client_id=app_9d31c0a7f2b4e1c8a6d0" \\
  -d "client_secret=$PHIZ_CLIENT_SECRET" \\
  -d "scope=messages:send messages:read"</div>'''

def s03():
    drawer = f'<div class="overlay"></div><div class="drawer" style="left:84px"><div class="dh">✕ &nbsp;{T("Detalhes da aplicação","Application details","应用详情")}</div>{detail_body()}</div>'
    return shell('apps', T('Aplicações', 'Applications', '应用'), apps_page(), drawer, 1010)

# ------------------------------------------------------------------ 04 Segredo criado
def s04():
    modal = f'''<div class="overlay" style="background:rgba(17,17,17,.55)"></div><div style="position:absolute;left:50%;top:150px;transform:translateX(-50%);width:600px;background:#fff;border-radius:12px;box-shadow:0 20px 50px rgba(0,0,0,.25);padding:26px 28px">
<div style="font-size:18px;font-weight:600">{T('Novo segredo gerado','New secret generated','已生成新密钥')}</div><p class="muted" style="margin:6px 0 16px">Blip · Atendimento · v2</p>
<div class="note">{T('<b>Copie agora.</b> Este segredo é exibido uma única vez e guardado apenas como hash.','<b>Copy it now.</b> This secret is shown only once and stored only as a hash.','<b>请立即复制。</b>该密钥仅显示一次，系统只保存其哈希。')}</div>
<div class="inp mono" style="margin-top:14px;padding:12px 14px;font-size:14px">phzsk_live_7Qm2xV9pL4rT8wZ1nB6cK3sH5yJ0dF2a<span class="btn" style="padding:5px 12px;font-family:'IBM Plex Sans'">{T('Copiar','Copy','复制')}</span></div>
<div class="info" style="margin-top:14px">{T('O segredo anterior <span class="mono">••••b27c</span> continua válido até <b>27/10/2026 14:30</b> (tolerância de 7 dias). Atualize a Blip e revogue o anterior quando terminar.','The previous secret <span class="mono">••••b27c</span> stays valid until <b>2026-10-27 14:30</b> (7-day grace). Update Blip and revoke the old one when you are done.','旧密钥 <span class="mono">••••b27c</span> 在 <b>2026-10-27 14:30</b> 前仍有效（7 天宽限期）。更新 Blip 后即可撤销旧密钥。')}</div>
<div class="cb" style="margin-top:12px"><span class="box on"></span><div>{T('Copiei e guardei o segredo em um local seguro','I copied the secret and stored it somewhere safe','我已复制并妥善保存该密钥')}</div></div>
<div class="foot"><span class="btn">{T('Concluir','Done','完成')}</span></div></div>'''
    drawer = f'<div class="drawer" style="left:84px">{"<div class=dh>✕ &nbsp;" + T("Detalhes da aplicação","Application details","应用详情") + "</div>"}{detail_body()}</div>'
    return shell('apps', T('Aplicações', 'Applications', '应用'), apps_page(), '<div class="overlay"></div>' + drawer + modal, 1010)

# ------------------------------------------------------------------ 05 Assinaturas de eventos
def s05():
    on = lambda: f'<span class="tag t-ok">{T("Ativada","Active","已启用")}</span>'
    off = lambda: f'<span class="tag t-off">{T("Desativada","Disabled","已停用")}</span>'
    rows = ''.join(f'<tr><td>{app_cell(*(a if isinstance(a, tuple) else (a,)))}</td><td><b style="font-weight:500">{ev}</b> <span class="muted">v1</span><div class="mono muted" style="font-size:12px">{sid}</div></td><td class="mono" style="font-size:12.5px">{url}</td><td>{s}</td><td class="mono muted">2026-10-20 09:40</td><td>{T("Editar","Edit","编辑")}</td></tr>'
                   for a, ev, sid, url, s in [(BLIP, 'messages', 'sub_3f1c8e20a9d4', 'https://api.blip.ai/phiz/webhook', on()),
                                              (BLIP, 'message_status', 'sub_77ab02c4e5f1', 'https://api.blip.ai/phiz/webhook', on()),
                                              (SF, 'message_status', 'sub_c91d4b7e0a32', 'https://lojaexemplo.my.salesforce.com/phiz', on()),
                                              (BO, 'sender_update', 'sub_0be5a6f9d118', 'https://backoffice.lojaexemplo.com/hooks', off())])
    page = f'''<div style="display:flex;justify-content:space-between"><div><h1>{T('Assinaturas de eventos','Event subscriptions','事件订阅')}</h1><p class="sub">{T('Assine eventos publicados para seus apps e configure URLs de retorno Webhook.','Subscribe to events published for your apps and configure webhook callback URLs.','为应用订阅已发布的事件，并配置 Webhook 回调 URL。')}</p></div><div><span class="btn2">{T('Atualizar','Refresh','刷新')}</span> <span class="btn">＋ {T('Nova assinatura','New subscription','新建订阅')}</span></div></div>
{stats([('4', T('Total de assinaturas','Total subscriptions','订阅总数'), ''), ('3', T('Ativas','Active','启用'), ''), ('1', T('Desativadas','Disabled','停用'), ''), ('3', T('Apps envolvidos','Apps involved','涉及应用'), '')])}
<div class="card" style="padding:0;overflow:hidden"><table class="tb"><tr><th>App</th><th>{T('Evento','Event','事件')}</th><th>{T('URL de retorno','Callback URL','回调 URL')}</th><th>Status</th><th>{T('Atualizado em','Updated at','更新时间')}</th><th>{T('Ações','Actions','操作')}</th></tr>{rows}</table></div>'''
    ev = lambda on, name, d: f'<div class="cb"><span class="box{" on" if on else ""}"></span><div><span class="mono">{name}</span> <span class="muted">v1</span><div class="muted" style="font-size:12.5px">{d}</div></div></div>'
    drawer = f'''<div class="overlay"></div><div class="drawer" style="width:620px"><div class="dh">✕ &nbsp;{T('Nova assinatura','New subscription','新建订阅')}</div>
<div class="field"><div class="fl">{T('Aplicação','Application','应用')}</div><div class="inp">Blip · Atendimento <span class="muted">▾</span></div></div>
<div class="fl" style="font-weight:500;margin-bottom:2px">{T('Eventos','Events','事件')} <span class="muted" style="font-weight:400">· Business Messaging</span></div>
{ev(True, 'messages', T('Usuário enviou mensagem, clicou num botão ou reagiu','User sent a message, tapped a button or reacted','用户发送消息、点击按钮或回应'))}
{ev(True, 'message_status', T('Mensagem enviada mudou para sent, delivered, read ou failed','A sent message changed to sent, delivered, read or failed','已发送消息变为 sent、delivered、read 或 failed'))}
{ev(False, 'sender_update', T('Mudou status, qualidade ou limite de um remetente','A sender’s status, quality or limit changed','发送方状态、质量或限额变化'))}
{ev(False, 'account_update', T('Mudança na conta (verificação, restrição)','Account change (verification, restriction)','账户变化（认证、限制）'))}
<div class="field" style="margin-top:12px"><div class="fl">{T('URL de retorno','Callback URL','回调 URL')}</div><div class="inp mono">https://api.blip.ai/phiz/webhook<span class="tag t-ok" style="font-family:'IBM Plex Sans'">✓ {T('Verificada','Verified','已验证')}</span></div><div class="hint">{T('A PHIZ faz um GET com hub.challenge antes de ativar. A URL precisa estar na lista de callbacks da aplicação.','PHIZ sends a GET with hub.challenge before activating. The URL must be in the application’s callback list.','启用前 PHIZ 会发送带 hub.challenge 的 GET 请求。URL 必须在应用的回调白名单中。')}</div></div>
<div class="field"><div class="fl">Verify token</div><div class="inp mono">blip-phiz-2026</div></div>
<div class="field"><div class="fl">Webhook secret</div><div class="inp mono">whsec_••••••••a41e<span class="muted" style="font-family:'IBM Plex Sans'">{T('Rotacionar','Rotate','轮换')}</span></div><div class="hint">{T('Assina cada entrega (X-Phiz-Signature). É diferente do segredo da aplicação.','Signs every delivery (X-Phiz-Signature). It is different from the application secret.','用于对每次投递签名（X-Phiz-Signature），与应用密钥不同。')}</div></div>
<div class="foot"><span class="btn2">{T('Enviar evento de teste','Send test event','发送测试事件')}</span><span class="btn">{T('Salvar assinatura','Save subscription','保存订阅')}</span></div></div>'''
    return shell('assin', T('Assinaturas de eventos', 'Event subscriptions', '事件订阅'), page, drawer)

# ------------------------------------------------------------------ 06 Webhook (entregas)
def s06():
    st = {'ok': ('t-ok', T('Entregue', 'Delivered', '已送达')), 'rt': ('t-warn', T('Repetindo', 'Retrying', '重试中')), 'f': ('t-err', T('Falha na entrega', 'Delivery failed', '投递失败'))}
    data = [(BLIP, 'messages', 'https://api.blip.ai/phiz/webhook', 'ok', '1 / 5', '200', '14:31:08'),
            (BLIP, 'message_status', 'https://api.blip.ai/phiz/webhook', 'ok', '1 / 5', '200', '14:31:07'),
            (SF, 'message_status', 'https://lojaexemplo.my.salesforce.com/phiz', 'rt', '3 / 5', '503', '14:30:55'),
            (SF, 'message_status', 'https://lojaexemplo.my.salesforce.com/phiz', 'f', '5 / 5', '500', '14:12:40'),
            (BLIP, 'messages', 'https://api.blip.ai/phiz/webhook', 'ok', '2 / 5', '200', '14:10:02'),
            (SF, 'message_status', 'https://lojaexemplo.my.salesforce.com/phiz', 'f', '5 / 5', '500', '13:58:21')]
    rows = ''.join(f'<tr><td>{app_cell(*(a if isinstance(a, tuple) else (a,)))}</td><td class="mono">{e}</td><td class="mono" style="font-size:12.5px">{u}</td><td><span class="tag {st[s][0]}">{st[s][1]}</span></td><td class="mono">{t}</td><td class="mono{" red" if r[0] == "5" else ""}">{r}</td><td class="mono muted">2026-10-20 {h}</td><td>{T("Detalhes","Details","详情")}{"<br><b style=font-weight:500>" + T("Retentar","Retry","重试") + "</b>" if s == "f" else ""}</td></tr>' for a, e, u, s, t, r, h in data)
    detail = f'''<div class="card" style="margin-top:16px"><div style="display:flex;justify-content:space-between"><b style="font-weight:600">{T('Detalhes da entrega','Delivery details','投递详情')} · <span class="mono">dlv_8c2e41f0b7a9</span></b><span class="tag t-err">{T('Falha na entrega','Delivery failed','投递失败')}</span></div>
<div class="row" style="margin-top:14px"><div style="flex:1"><div class="kv" style="grid-template-columns:repeat(2,1fr)"><div><div class="k">{T('Evento','Event','事件')}</div><div class="v mono">message_status · failed</div></div><div><div class="k">X-Phiz-Delivery-Id</div><div class="v mono">dlv_8c2e41f0b7a9</div></div><div><div class="k">{T('Tentativas','Attempts','尝试')}</div><div class="v mono">10s · 30s · 1min · 5min · 15min</div></div><div><div class="k">{T('Próxima ação','Next action','下一步')}</div><div class="v">{T('Dead letter · reenvio manual por 72 h','Dead letter · manual replay for 72 h','死信 · 72 小时内可手动重放')}</div></div><div><div class="k">trace_id</div><div class="v mono">7f3a9c10e2b84d55</div></div><div><div class="k">{T('Última resposta','Last response','最后响应')}</div><div class="v mono red">500 Internal Server Error</div></div></div></div>
<div style="flex:1"><div class="code" style="font-size:12px">{{"object": "phiz_business_account",
 "entry": [{{"id": "7b1e4c52-…",
  "changes": [{{"field": "message_status",
   "value": {{"statuses": [{{"id": "wamid.HBg…",
     "status": "failed", "errors": [{{"code": 2201}}]
   }}]}}}}]}}]}}</div></div></div></div>'''
    page = f'''<div style="display:flex;justify-content:space-between"><div><h1>Webhook</h1><p class="sub">{T('Inspecione entregas de eventos, retentativas, códigos de resposta e detalhes de rastreio.','Inspect event deliveries, retries, response codes and trace details.','查看事件投递、重试、响应码和追踪详情。')}</p></div><div><span class="btn2">{T('Atualizar','Refresh','刷新')}</span> <span class="btn">{T('Retentar falhas','Retry failures','重试失败项')}</span></div></div>
{stats([('1.284', T('Entregas','Deliveries','投递'), T('Últimas 72 h','Last 72 h','最近 72 小时')), ('1.270', T('Entregue','Delivered','已送达'), '98,9%'), ('5', T('Repetindo','Retrying','重试中'), T('Aguardando reenvio','Waiting for retry','等待重发')), ('9', T('Falha na entrega','Delivery failed','投递失败'), T('Exige atenção manual','Needs manual attention','需人工处理'))])}
<div class="row" style="margin-bottom:14px"><div class="inp" style="flex:1;color:#8b949e">⌕ {T('Buscar por app, evento, URL de destino ou ID do evento','Search by app, event, target URL or event ID','按应用、事件、目标 URL 或事件 ID 搜索')}</div><div class="inp" style="width:220px">{T('Todos os eventos','All events','全部事件')} ▾</div><div class="inp" style="width:220px">{T('Todos os status','All statuses','全部状态')} ▾</div></div>
<div class="card" style="padding:0;overflow:hidden"><table class="tb"><tr><th>App</th><th>{T('Evento','Event','事件')}</th><th>{T('URL de destino','Target URL','目标 URL')}</th><th>Status</th><th>{T('Tentativas','Attempts','尝试')}</th><th>{T('Última resposta','Last response','最后响应')}</th><th>{T('Última entrega','Last delivery','最后投递')}</th><th>{T('Ações','Actions','操作')}</th></tr>{rows}</table></div>{detail}'''
    return shell('webhook', 'Webhook', page)

# ------------------------------------------------------------------ 07 Remetentes
def s07():
    sel = lambda v: f'<div class="inp" style="min-height:30px;padding:4px 10px;width:220px">{v} <span class="muted">▾</span></div>'
    apps = lambda *n: ''.join(f'<span class="chip" style="padding:3px 8px;margin:0 6px 6px 0;font-size:12.5px">{x}</span>' for x in n)
    av = lambda t, c='#111': f'<div class="sq" style="background:{c};border-radius:50%">{t}</div>'
    rows = f'''<tr><td><div class="aname">{av(T("LE","ES","示"))}<div><b style="font-weight:600">{STORE()}</b><div class="id">{T('Nome e foto do comerciante','Merchant name and photo','商户名称和头像')}</div></div></div></td><td><span class="tag t-new">{T('Mensagem direta','Direct message','直接消息')}</span> <span class="tag t-off">{T('Padrão','Default','默认')}</span></td><td class="mono" style="font-size:12.5px">7b1e4c52-91d0-4a6e-<br>b3f8-2c5d9a0e7f14</td><td>{apps('Blip · Atendimento', 'Salesforce · Marketing')}</td><td>{sel('Blip · Atendimento')}</td><td><span class="tag t-ok">{T('Ativo','Active','启用')}</span><div class="muted mono" style="font-size:12px;margin-top:4px">{T('Limite','Limit','限额')} 10k/24h</div></td></tr>
<tr><td><div class="aname">{av(T("LO","EO","优"), "#b45309")}<div><b style="font-weight:600">{OFFERS()}</b><div class="id">{T('Canal · 2 inscritos','Channel · 2 subscribers','频道 · 2 位订阅者')}</div></div></div></td><td><span class="tag t-off">{T('Canal','Channel','频道')}</span><div style="margin-top:6px;font-size:12.5px">● <span class="green">{T('Modo Phiz Business API ligado','Phiz Business API mode on','Phiz Business API 模式已开启')}</span></div></td><td class="mono">1231</td><td>{apps('Blip · Atendimento', T('Backoffice interno','Internal back office','内部后台'))}</td><td>{sel(T('Backoffice interno','Internal back office','内部后台'))}</td><td><span class="tag t-ok">{T('Ativo','Active','启用')}</span><div class="muted mono" style="font-size:12px;margin-top:4px">{T('Limite','Limit','限额')} 1k/24h</div></td></tr>
<tr><td><div class="aname">{av(T("LN","EN","新"), "#6b7280")}<div><b style="font-weight:600">{NEWS()}</b><div class="id">{T('Canal · 540 inscritos','Channel · 540 subscribers','频道 · 540 位订阅者')}</div></div></div></td><td><span class="tag t-off">{T('Canal','Channel','频道')}</span><div style="margin-top:6px;font-size:12.5px" class="muted">○ {T('Modo Phiz Business API desligado','Phiz Business API mode off','Phiz Business API 模式未开启')}</div></td><td class="mono">1288</td><td class="muted">—</td><td class="muted">—</td><td><span class="tag t-off">{T('Sem integração','No integration','无集成')}</span></td></tr>'''
    page = f'''<div style="display:flex;justify-content:space-between;align-items:flex-start"><div><h1>{T('Remetentes','Senders','发送方')} <span class="tag t-new" style="vertical-align:middle">{T('Novo','New','新')}</span></h1><p class="sub" style="max-width:760px">{T('O remetente é quem aparece para o usuário no PhizChat. A organização envia como ela mesma (mensagem direta) e, se tiver canais, também por eles.','The sender is who the user sees in PhizChat. The organization sends as itself (direct message) and, if it has channels, through them too.','发送方是用户在 PhizChat 中看到的身份。组织可以以自身名义发送（直接消息），有频道时也可通过频道发送。')}</p></div><span class="btn2">{T('Atualizar','Refresh','刷新')}</span></div>
<div class="card" style="padding:0;overflow:hidden;margin-top:22px"><table class="tb"><tr><th>{T('Remetente','Sender','发送方')}</th><th>{T('Tipo','Type','类型')}</th><th>sender_id</th><th>{T('Aplicações com acesso','Applications with access','有权限的应用')}</th><th>{T('Responsável pelas conversas','Owns conversations','负责会话的应用')}</th><th>Status</th></tr>{rows}</table></div>
<div class="row" style="margin-top:16px"><div class="card" style="flex:1"><b style="font-weight:600">{T('Como o usuário vê','How the user sees it','用户看到的效果')}</b><div style="background:#f6f7f8;border-radius:8px;padding:12px 14px;margin-top:12px"><b style="font-weight:600">{STORE()}</b><div>{T('Olá! Seu pedido saiu para entrega.','Hi! Your order is out for delivery.','您好！您的订单已发货。')}</div></div><p class="muted" style="margin:10px 0 0;font-size:13px">{T('Mensagem direta: aparece como conversa com a loja, sem canal.','Direct message: shows up as a conversation with the store, no channel.','直接消息：显示为与商户的对话，无需频道。')}</p></div>
<div class="card" style="flex:1"><b style="font-weight:600">{T('Regras','Rules','规则')}</b><ul style="margin:10px 0 0;padding-left:18px;line-height:1.8">
<li>{T('Só a aplicação responsável recebe o evento <span class="mono">messages</span> daquele remetente.','Only the responsible application receives the <span class="mono">messages</span> event for that sender.','只有负责的应用会收到该发送方的 <span class="mono">messages</span> 事件。')}</li>
<li>{T('Qualquer aplicação com acesso pode enviar e recebe o <span class="mono">message_status</span> do que enviou.','Any application with access can send and receives <span class="mono">message_status</span> for what it sent.','任何有权限的应用都可发送，并收到所发消息的 <span class="mono">message_status</span>。')}</li>
<li>{T('Os canais continuam sendo criados no Open Platform, em <b>Canal › Meus Canais</b>.','Channels are still created in the Open Platform, under <b>Channel › My Channels</b>.','频道仍在开放平台的<b>频道 › 我的频道</b>中创建。')}</li></ul></div></div>'''
    return shell('remet', T('Remetentes', 'Senders', '发送方'), page)

# ------------------------------------------------------------------ 08 Canal (Open Platform)
def s08():
    c = css() + """
.op{background:#f2f2f2;min-height:820px;font-family:-apple-system,'Inter','Noto Sans CJK SC',sans-serif}
.opbar{height:64px;background:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 28px;border-bottom:1px solid #ececec}
.oplogo{font-weight:800;font-size:26px;color:#ef6a1f}.oppill{background:#c4500d;color:#fff;font-weight:600;font-size:13px;padding:5px 14px;border-radius:999px;margin-left:10px}
.opside{flex:0 0 256px;background:#f8f8f8;border-right:1px solid #ececec;padding:16px 12px}
.opside div{padding:11px 14px;border-radius:10px;color:#2a2a2a;font-size:15px}.opside .on{background:#fff;color:#b8470b;font-weight:600}
.opcard{background:#fff;border-radius:14px;padding:24px}
.opbtn{display:inline-flex;background:#c4500d;color:#fff;border-radius:8px;padding:10px 18px;font-weight:600}
"""
    body = f'''<!doctype html><html><head><meta charset="utf-8"><style>{c}</style></head><body><div class="op">
<div class="opbar"><div style="display:flex;align-items:center"><span class="oplogo">PHIZ</span><span class="oppill">Open Platform</span></div><div style="display:flex;gap:26px;font-size:14px"><span style="color:#1f5fc4">{T('Português ▾','English ▾','简体中文 ▾')}</span><b>{STORE()} ▾</b></div></div>
<div style="display:flex;min-height:756px"><div class="opside"><div style="color:#1f5fc4">‹ &nbsp;{T('Todos os canais','All channels','全部频道')}</div><div style="display:flex;gap:10px;align-items:center"><span style="width:34px;height:34px;border-radius:50%;background:#111;color:#f2c14e;display:inline-flex;align-items:center;justify-content:center;font-weight:700;padding:0">{T('LO','EO','优')}</span><span><b>{OFFERS()}</b><br><span style="font-size:13px;color:#666">{T('2 inscritos','2 subscribers','2 位订阅者')}</span></span></div>
<div>{T('Informações do canal','Channel information','频道信息')}</div><div>{T('Postar conteúdo','Post content','发布内容')}</div><div>{T('Configuração de Negócio','Business settings','业务设置')}</div><div>{T('Mini programa','Mini program','小程序')}</div><div>{T('Robô de IA','AI bot','AI 机器人')}</div><div class="on">{T('Configuração de Desenvolvimento','Development settings','开发配置')}</div></div>
<div style="flex:1;padding:28px 36px"><h1 style="font-family:inherit">{T('Configuração de Desenvolvimento','Development settings','开发配置')}</h1>
<div class="opcard" style="border-left:4px solid #c4500d;margin-top:18px"><b style="font-size:17px">{T('As credenciais da API agora ficam na Central do Desenvolvedor PHIZ','API credentials now live in the PHIZ Developer Center','API 凭证现已迁移至 PHIZ开发者中心')}</b>
<p style="color:#444;margin:8px 0 16px;max-width:820px">{T('Criamos a aplicação <b>Legado – Loja Exemplo · Ofertas</b> com o mesmo AppID e segredo, então nada parou. Lá você rotaciona segredos sem interromper o envio, escolhe os remetentes de cada aplicação e assina os eventos de webhook. As chaves abaixo seguem funcionando até <b>20/01/2027</b>; depois disso esta página fica somente leitura.','We created the <b>Legacy – Example Store · Offers</b> application with the same AppID and secret, so nothing stopped. There you rotate secrets without stopping sends, choose the senders of each application and subscribe to webhook events. The keys below keep working until <b>2027-01-20</b>; after that this page becomes read-only.','我们已用相同的 AppID 和密钥创建了 <b>Legacy – 示例商店 · 优惠</b> 应用，现有集成不受影响。在开发者中心可以不中断地轮换密钥、为每个应用选择发送方并订阅 Webhook 事件。下方密钥在 <b>2027-01-20</b> 前继续有效，之后本页面变为只读。')}</p>
<span class="opbtn">{T('Abrir a Central do Desenvolvedor ↗','Open the Developer Center ↗','打开开发者中心 ↗')}</span></div>
<div class="opcard" style="margin-top:18px"><div style="display:grid;grid-template-columns:200px 1fr 160px;row-gap:18px;align-items:center">
<span style="color:#666">AppID</span><span class="mono">1231</span><span></span>
<span style="color:#666">AppSecret</span><span class="mono">••••••••••••••••••••c81e</span><span style="color:#999">{T('Redefinir','Reset','重置')} <span class="tag t-off" style="margin-left:6px">{T('até 20/01','until 01-20','至 01-20')}</span></span>
<span style="color:#666">{T('Aplicação na Central','App in the Developer Center','开发者中心应用')}</span><span><span class="tag t-new">{T('Legado – Loja Exemplo · Ofertas','Legacy – Example Store · Offers','Legacy – 示例商店 · 优惠')}</span> <span class="mono" style="color:#666">app_1231</span></span><span style="color:#1f5fc4">{T('Ver aplicação','View app','查看应用')}</span>
<span style="color:#666">Endpoint</span><span class="mono">/gateway/openapi/auth · /token/refresh</span><span class="tag t-warn" style="justify-self:start">{T('Em descontinuação','Deprecated','即将停用')}</span></div></div></div></div></div></body></html>'''
    return body

SCREENS = [('01-painel', s01), ('02-nova-aplicacao', s02), ('03-detalhe-aplicacao', s03), ('04-segredo-gerado', s04),
           ('05-assinaturas-eventos', s05), ('06-webhook-entregas', s06), ('07-remetentes', s07), ('08-canal-migracao', s08)]

async def main():
    from playwright.async_api import async_playwright
    global L
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1440, 'height': 900}, device_scale_factor=1)
        for L in LANGS:
            os.makedirs(f'{OUT}/{L}', exist_ok=True)
            for name, fn in SCREENS:
                html = fn()
                fp = f'{HERE}/tmp_{L}_{name}.html'
                open(fp, 'w', encoding='utf-8').write(html)
                await pg.set_viewport_size({'width': 1440, 'height': 820 if name.startswith('08') else 900})
                await pg.goto('file://' + fp)
                await pg.wait_for_timeout(150)
                await pg.screenshot(path=f'{OUT}/{L}/{name}.png', full_page=True)
                os.remove(fp)
        await b.close()

if __name__ == '__main__':
    asyncio.run(main())
