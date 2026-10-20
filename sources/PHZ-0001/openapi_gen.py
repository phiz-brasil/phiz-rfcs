"""Generates the Phiz Business Messaging API OpenAPI 3.1 spec in pt-BR, en-US and zh-CN.

Every human-readable string is written as T(pt, en, zh); resolve(obj, lang) picks one.
"""
import json, copy, yaml


class T:
    def __init__(self, pt, en, zh):
        self.v = {"pt": pt, "en": en, "zh": zh}


def resolve(o, lang):
    if isinstance(o, T):
        return o.v[lang]
    if isinstance(o, dict):
        return {k: resolve(v, lang) for k, v in o.items()}
    if isinstance(o, list):
        return [resolve(v, lang) for v in o]
    return o


def ref(name):
    return {"$ref": f"#/components/schemas/{name}"}


def err(code_ref):
    return {"$ref": f"#/components/responses/{code_ref}"}


STD_ERRORS = {
    "400": err("BadRequest"),
    "401": err("Unauthorized"),
    "403": err("Forbidden"),
    "429": err("TooManyRequests"),
    "500": err("ServerError"),
}

IDEMPOTENCY = {
    "name": "Idempotency-Key",
    "in": "header",
    "required": False,
    "schema": {"type": "string", "maxLength": 128},
    "example": "pedido-48213-confirmacao",
    "description": T(
        "Chave única por requisição lógica. Repetir a mesma chave em até 24 h devolve a resposta original sem reenviar a mensagem.",
        "Unique key per logical request. Reusing the same key within 24 h returns the original response without sending the message again.",
        "每个逻辑请求的唯一键。24 小时内重复使用同一键将返回原始响应，不会重复发送消息。",
    ),
}

SENDER_ID = {
    "name": "sender_id",
    "in": "path",
    "required": True,
    "schema": {"type": "string"},
    "example": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57",
    "description": T(
        "ID do remetente. Use o merchant_id para enviar diretamente em nome do comerciante (padrão, não exige canal) ou, opcionalmente, o ID de um canal do comerciante. Equivale ao phone_number_id da Cloud API da Meta.",
        "Sender ID. Use the merchant_id to send directly on behalf of the merchant (default, no channel required) or, optionally, the ID of one of the merchant's channels. Equivalent to Meta Cloud API's phone_number_id.",
        "发送方 ID。使用 merchant_id 直接以商户名义发送（默认，无需频道），或可选地使用商户某个频道的 ID。相当于 Meta Cloud API 的 phone_number_id。",
    ),
}

APP_ID = {
    "name": "app_id",
    "in": "path",
    "required": True,
    "schema": {"type": "string"},
    "example": "app_2Fk81PzQ",
    "description": T("ID do app de desenvolvedor.", "Developer app ID.", "开发者应用 ID。"),
}

MERCHANT_ID = {
    "name": "merchant_id",
    "in": "path",
    "required": True,
    "schema": {"type": "string"},
    "example": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57",
    "description": T("ID da conta de comerciante.", "Merchant account ID.", "商户账号 ID。"),
}

TAGS = [
    {"name": "Auth", "description": T(
        "Emissão e revogação de tokens OAuth 2.0 (client credentials).",
        "OAuth 2.0 token issuance and revocation (client credentials).",
        "OAuth 2.0 令牌签发与撤销（客户端凭证模式）。")},
    {"name": "Account", "description": T(
        "Conta de comerciante, remetentes e apps de desenvolvedor.",
        "Merchant account, senders and developer apps.",
        "商户账号、发送方与开发者应用。")},
    {"name": "Messages", "description": T(
        "Envio de mensagens para um número de telefone ou PHIZ ID e consulta de status.",
        "Send messages to a phone number or PHIZ ID and query their status.",
        "向手机号或 PHIZ ID 发送消息并查询状态。")},
    {"name": "Media", "description": T(
        "Upload de mídia para o armazenamento temporário da PHIZ. Toda mídia enviada em mensagens precisa passar por aqui; links de terceiros não são aceitos.",
        "Media upload to PHIZ temporary storage. All media sent in messages must go through here; third-party links are not accepted.",
        "将媒体上传到 PHIZ 临时存储。消息中发送的所有媒体都必须经由此处上传；不接受第三方链接。")},
    {"name": "Webhooks", "description": T(
        "Configuração da assinatura de webhook do app e eventos enviados ao seu servidor.",
        "App webhook subscription setup and events delivered to your server.",
        "应用的 Webhook 订阅配置以及推送到您服务器的事件。")},
]

INFO_DESC = T(
    """API de mensageria empresarial da PHIZ. Permite que sistemas de terceiros (CRMs, plataformas de atendimento como Blip e Salesforce, ou sistemas próprios do comerciante) enviem mensagens a usuários PHIZ identificados por **número de telefone** ou **PHIZ ID**, e recebam por **webhook** as mensagens de resposta e as mudanças de status.

O formato das mensagens e dos webhooks segue de perto a Cloud API da Meta (WhatsApp Business Platform), para reduzir o custo de adaptação de integrações existentes.

**Status:** proposta (RFC PHZ-0001). Nada aqui está implementado.""",
    """PHIZ business messaging API. It lets third-party systems (CRMs, customer-service platforms such as Blip and Salesforce, or the merchant's own systems) send messages to PHIZ users identified by **phone number** or **PHIZ ID**, and receive replies and status changes through a **webhook**.

Message and webhook payloads closely follow Meta's Cloud API (WhatsApp Business Platform) to keep the cost of adapting existing integrations low.

**Status:** proposal (RFC PHZ-0001). Nothing here is implemented yet.""",
    """PHIZ 企业消息 API。第三方系统（CRM、Blip 和 Salesforce 等客服平台，或商户自有系统）可以通过 **手机号** 或 **PHIZ ID** 向 PHIZ 用户发送消息，并通过 **Webhook** 接收用户回复和状态变更。

消息与 Webhook 的数据结构尽量对齐 Meta Cloud API（WhatsApp Business Platform），以降低现有集成的改造成本。

**状态：** 提案（RFC PHZ-0001），尚未实现。""",
)

SCHEMAS = {
    "TokenRequest": {
        "type": "object",
        "required": ["grant_type", "client_id", "client_secret"],
        "properties": {
            "grant_type": {"type": "string", "enum": ["client_credentials"]},
            "client_id": {"type": "string", "example": "app_2Fk81PzQ",
                           "description": T("ID do app (client_id) gerado na Área do Desenvolvedor.",
                                            "App ID (client_id) issued in the Developer area.",
                                            "在开发者中心生成的应用 ID（client_id）。")},
            "client_secret": {"type": "string", "format": "password", "example": "phzsk_live_9c1f…",
                               "description": T("Secret do app. Exibido uma única vez na criação ou rotação.",
                                                "App secret. Shown only once, at creation or rotation.",
                                                "应用密钥，仅在创建或轮换时显示一次。")},
            "scope": {"type": "string", "example": "messages:send messages:read",
                      "description": T("Escopos solicitados, separados por espaço. Se omitido, recebe todos os escopos concedidos ao app.",
                                       "Requested scopes, space separated. If omitted, all scopes granted to the app are issued.",
                                       "以空格分隔的请求范围。省略时签发应用已获授权的全部范围。")},
        },
    },
    "TokenResponse": {
        "type": "object",
        "required": ["access_token", "token_type", "expires_in", "scope"],
        "properties": {
            "access_token": {"type": "string", "example": "eyJhbGciOiJFUzI1NiIsImtpZCI6InBoei0yMDI2LTEwIn0…"},
            "token_type": {"type": "string", "enum": ["Bearer"]},
            "expires_in": {"type": "integer", "example": 3600,
                           "description": T("Validade em segundos.", "Lifetime in seconds.", "有效期（秒）。")},
            "scope": {"type": "string", "example": "messages:send messages:read webhooks:manage"},
            "merchant_id": {"type": "string", "example": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57"},
        },
    },
    "TokenInfo": {
        "type": "object",
        "properties": {
            "active": {"type": "boolean", "example": True},
            "app_id": {"type": "string", "example": "app_2Fk81PzQ"},
            "merchant_id": {"type": "string", "example": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57"},
            "scope": {"type": "string", "example": "messages:send messages:read"},
            "senders": {"type": "array", "items": {"type": "string"}, "example": ["7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57", "1231"],
                        "description": T("Remetentes que este app pode usar.", "Senders this app may use.", "此应用可使用的发送方。")},
            "expires_at": {"type": "string", "format": "date-time", "example": "2026-10-15T12:30:00Z"},
        },
    },
    "Merchant": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "example": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57"},
            "name": {"type": "string", "example": "Loja Exemplo Ltda."},
            "status": {"type": "string", "enum": ["active", "restricted", "suspended"]},
            "verification": {"type": "string", "enum": ["unverified", "pending", "verified"]},
            "created_at": {"type": "string", "format": "date-time"},
        },
    },
    "Sender": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "example": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57"},
            "type": {"type": "string", "enum": ["merchant", "channel"], "example": "merchant",
                      "description": T("`merchant`: o próprio comerciante, remetente padrão que todo comerciante tem. `channel`: um canal do comerciante, opcional.",
                                       "`merchant`: the merchant itself, the default sender every merchant has. `channel`: one of the merchant's channels, optional.",
                                       "`merchant`：商户本身，每个商户都有的默认发送方。`channel`：商户的频道，可选。")},
            "conversation_type": {"type": "string", "enum": ["business_account", "channel_service"], "example": "business_account",
                                  "description": T("Tipo de conversa no PhizChat (Contas públicas › Service): `business_account` para type = merchant, `channel_service` para type = channel.",
                                                   "PhizChat conversation type (Public Accounts › Service): `business_account` for type = merchant, `channel_service` for type = channel.",
                                                   "PhizChat 会话类型（公众号 › Service）：type = merchant 对应 `business_account`，type = channel 对应 `channel_service`。")},
            "display_name": {"type": "string", "example": "Loja Exemplo"},
            "channel_id": {"type": "string", "nullable": True, "example": None,
                           "description": T("Preenchido apenas quando type = channel.", "Filled only when type = channel.", "仅当 type = channel 时有值。")},
            "status": {"type": "string", "enum": ["connected", "pending_review", "disabled"]},
            "messaging_limit_tier": {"type": "string", "example": "TIER_1K",
                                     "description": T("Quantos destinatários únicos podem receber mensagens iniciadas pela empresa em 24 h.",
                                                      "How many unique recipients may receive business-initiated messages in 24 h.",
                                                      "24 小时内可接收企业主动消息的唯一用户数上限。")},
            "quality_rating": {"type": "string", "enum": ["GREEN", "YELLOW", "RED", "UNKNOWN"]},
        },
    },
    "SenderList": {"type": "object", "properties": {"data": {"type": "array", "items": ref("Sender")}, "paging": ref("Paging")}},
    "Paging": {"type": "object", "properties": {"next_cursor": {"type": "string", "nullable": True, "example": "c2VuZGVyX2lkPXNuZF85"}}},
    "Recipient": {
        "description": T(
            "Destinatário. Informe `to` e, se não for telefone, `to_type`. Telefone em formato E.164.",
            "Recipient. Provide `to` and, if it is not a phone number, `to_type`. Phone numbers use E.164.",
            "接收方。填写 `to`；若不是手机号，需指定 `to_type`。手机号采用 E.164 格式。"),
        "type": "object",
    },
    "SendMessageRequest": {
        "type": "object",
        "required": ["to", "type"],
        "properties": {
            "messaging_product": {"type": "string", "enum": ["phiz"], "default": "phiz",
                                  "description": T("Opcional; mantido por compatibilidade com a Cloud API.",
                                                   "Optional; kept for Cloud API compatibility.",
                                                   "可选；为兼容 Cloud API 而保留。")},
            "recipient_type": {"type": "string", "enum": ["individual"], "default": "individual"},
            "to": {"type": "string", "example": "+5511987654321",
                   "description": T("Telefone E.164 ou PHIZ ID do destinatário.",
                                    "Recipient phone number (E.164) or PHIZ ID.",
                                    "接收方手机号（E.164）或 PHIZ ID。")},
            "to_type": {"type": "string", "enum": ["phone", "phiz_id"], "default": "phone"},
            "type": {"type": "string",
                     "enum": ["text", "image", "video", "audio", "document", "location", "interactive", "reaction", "template"],
                     "description": T("`template` fica reservado para a futura Marketing API.",
                                      "`template` is reserved for the future Marketing API.",
                                      "`template` 预留给后续的 Marketing API。")},
            "text": ref("TextContent"),
            "image": ref("MediaContent"),
            "video": ref("MediaContent"),
            "audio": ref("MediaContent"),
            "document": ref("MediaContent"),
            "location": ref("LocationContent"),
            "interactive": ref("InteractiveContent"),
            "reaction": ref("ReactionContent"),
            "context": {"type": "object", "properties": {"message_id": {"type": "string"}},
                        "description": T("Responde (cita) uma mensagem anterior.", "Replies to (quotes) an earlier message.", "引用回复之前的消息。")},
            "biz_opaque_callback_data": {"type": "string", "maxLength": 512, "example": "pedido=48213",
                                         "description": T("Texto livre devolvido em todos os webhooks de status desta mensagem.",
                                                          "Free text echoed back in every status webhook for this message.",
                                                          "自定义文本，会在此消息的所有状态 Webhook 中原样返回。")},
        },
    },
    "TextContent": {"type": "object", "required": ["body"], "properties": {
        "body": {"type": "string", "maxLength": 4096, "example": "Olá, Maria! Seu pedido #48213 foi enviado."},
        "preview_url": {"type": "boolean", "default": False}}},
    "MediaContent": {"type": "object",
        "description": T("Informe `id` (recomendado) ou `link`, ambos devolvidos pelo upload em `POST /v1/{sender_id}/media`.",
                         "Provide `id` (recommended) or `link`, both returned by the upload to `POST /v1/{sender_id}/media`.",
                         "提供 `id`（推荐）或 `link`，二者均由 `POST /v1/{sender_id}/media` 上传后返回。"),
        "anyOf": [{"required": ["id"]}, {"required": ["link"]}], "properties": {
        "id": {"type": "string", "example": "pmed.01JB2K7Q9X",
               "description": T("ID da mídia devolvido pelo upload. Válido até `expires_at`.",
                                "Media ID returned by the upload. Valid until `expires_at`.",
                                "上传后返回的媒体 ID，在 `expires_at` 之前有效。")},
        "link": {"type": "string", "format": "uri", "example": "https://media.phiz.chat/biz/pmed.01JB2K7Q9X",
                 "description": T("Link PHIZ devolvido pelo upload. URLs de terceiros são recusadas com erro 2302.",
                                  "PHIZ link returned by the upload. Third-party URLs are rejected with error 2302.",
                                  "上传后返回的 PHIZ 链接。第三方 URL 会被拒绝并返回错误 2302。")},
        "caption": {"type": "string", "maxLength": 1024, "description": T("Não se aplica a áudio.", "Not used for audio.", "音频不适用。")},
        "filename": {"type": "string", "description": T("Só para document.", "Document only.", "仅适用于 document。")}}},
    "MediaUploadRequest": {"type": "object", "required": ["file", "type"], "properties": {
        "messaging_product": {"type": "string", "enum": ["phiz"]},
        "type": {"type": "string", "example": "application/pdf",
                 "description": T("Tipo MIME do arquivo. Precisa estar na tabela de formatos da seção 09.",
                                  "MIME type of the file. Must be in the formats table in section 09.",
                                  "文件的 MIME 类型，须在第 09 节的格式表中。")},
        "file": {"type": "string", "format": "binary"}}},
    "Media": {"type": "object", "properties": {
        "id": {"type": "string", "example": "pmed.01JB2K7Q9X"},
        "link": {"type": "string", "format": "uri", "example": "https://media.phiz.chat/biz/pmed.01JB2K7Q9X"},
        "mime_type": {"type": "string", "example": "application/pdf"},
        "file_size": {"type": "integer", "example": 184320},
        "sha256": {"type": "string", "example": "9b1f…"},
        "expires_at": {"type": "string", "format": "date-time", "example": "2026-11-19T14:00:00Z",
                       "description": T("Fim do armazenamento temporário (proposta: 30 dias após o upload). Depois disso, `id` e `link` deixam de valer.",
                                        "End of temporary storage (proposed: 30 days after upload). After it, `id` and `link` stop working.",
                                        "临时存储截止时间（建议：上传后 30 天）。到期后 `id` 和 `link` 失效。")}}},
    "LocationContent": {"type": "object", "required": ["latitude", "longitude"], "properties": {
        "latitude": {"type": "number", "example": -23.5614}, "longitude": {"type": "number", "example": -46.6559},
        "name": {"type": "string", "example": "Loja Paulista"}, "address": {"type": "string"}}},
    "InteractiveContent": {"type": "object", "properties": {
        "type": {"type": "string", "enum": ["button", "list"]},
        "body": {"type": "object", "properties": {"text": {"type": "string"}}},
        "action": {"type": "object", "properties": {
            "buttons": {"type": "array", "maxItems": 3, "items": {"type": "object", "properties": {
                "type": {"type": "string", "enum": ["reply"]},
                "reply": {"type": "object", "properties": {"id": {"type": "string"}, "title": {"type": "string", "maxLength": 20}}}}}}}}}},
    "ReactionContent": {"type": "object", "properties": {"message_id": {"type": "string"}, "emoji": {"type": "string", "example": "👍"}}},
    "SendMessageResponse": {
        "type": "object",
        "properties": {
            "messaging_product": {"type": "string", "example": "phiz"},
            "contacts": {"type": "array", "items": {"type": "object", "properties": {
                "input": {"type": "string", "example": "+5511987654321"},
                "phiz_id": {"type": "string", "nullable": True, "example": None,
                            "description": T("Preenchido apenas se o destinatário já conversou com este remetente.",
                                             "Filled only if the recipient has already talked to this sender.",
                                             "仅当接收方曾与该发送方对话时返回。")}}}},
            "messages": {"type": "array", "items": {"type": "object", "properties": {
                "id": {"type": "string", "example": "pmid.01JA9VZ6T8R3"},
                "message_status": {"type": "string", "enum": ["accepted"]}}}},
        },
    },
    "MessageStatus": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "example": "pmid.01JA9VZ6T8R3"},
            "sender_id": {"type": "string", "example": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57"},
            "status": {"type": "string", "enum": ["accepted", "sent", "delivered", "read", "failed"]},
            "updated_at": {"type": "string", "format": "date-time"},
            "biz_opaque_callback_data": {"type": "string", "nullable": True},
            "errors": {"type": "array", "items": ref("ErrorDetail")},
        },
    },
    "MarkReadRequest": {"type": "object", "required": ["status", "message_id"], "properties": {
        "messaging_product": {"type": "string", "enum": ["phiz"]},
        "status": {"type": "string", "enum": ["read"]},
        "message_id": {"type": "string", "example": "pmid.IN_01JA9W2C"},
        "typing_indicator": {"type": "boolean", "default": False}}},
    "WebhookConfig": {
        "type": "object",
        "required": ["url", "verify_token"],
        "properties": {
            "url": {"type": "string", "format": "uri", "example": "https://integracao.lojaexemplo.com.br/phiz/webhook"},
            "verify_token": {"type": "string", "writeOnly": True, "example": "um-texto-que-so-voce-conhece",
                             "description": T("Texto definido por você e devolvido no handshake GET.",
                                              "Text you choose, sent back in the GET handshake.",
                                              "由您设定，会在 GET 握手时回传。")},
            "fields": {"type": "array", "items": {"type": "string", "enum": ["messages", "message_status", "sender_update", "account_update"]},
                       "example": ["messages", "message_status"]},
            "status": {"type": "string", "readOnly": True, "enum": ["verified", "pending_verification", "failing", "disabled"]},
        },
    },
    "WebhookEvent": {
        "type": "object",
        "description": T("Envelope de todos os eventos. Pode agrupar vários eventos do mesmo comerciante.",
                         "Envelope for every event. May batch several events of the same merchant.",
                         "所有事件的外层结构，可批量包含同一商户的多个事件。"),
        "properties": {
            "object": {"type": "string", "enum": ["phiz_merchant_account"]},
            "entry": {"type": "array", "items": {"type": "object", "properties": {
                "id": {"type": "string", "example": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57"},
                "changes": {"type": "array", "items": {"type": "object", "properties": {
                    "field": {"type": "string", "enum": ["messages", "message_status", "sender_update", "account_update"]},
                    "value": {"type": "object"}}}}}}},
        },
    },
    "ErrorDetail": {"type": "object", "properties": {
        "code": {"type": "integer", "example": 2104}, "title": {"type": "string", "example": "recipient_not_reachable"},
        "message": {"type": "string"}, "href": {"type": "string", "format": "uri"}}},
    "OAuthError": {"type": "object", "description": "RFC 6749 §5.2", "properties": {
        "error": {"type": "string", "enum": ["invalid_request", "invalid_client", "invalid_scope", "unsupported_grant_type"]},
        "error_description": {"type": "string", "example": "Client authentication failed."}}},
    "Error": {
        "type": "object",
        "properties": {"error": {"type": "object", "properties": {
            "code": {"type": "integer", "example": 1003},
            "type": {"type": "string", "example": "invalid_request"},
            "message": {"type": "string", "example": "Field 'to' must be E.164 when to_type is 'phone'."},
            "details": {"type": "array", "items": {"type": "object", "properties": {"field": {"type": "string"}, "issue": {"type": "string"}}}},
            "trace_id": {"type": "string", "example": "trc_9f2c41ab"}}}},
    },
}


MEDIA_EXAMPLE = {"id": "pmed.01JB2K7Q9X", "link": "https://media.phiz.chat/biz/pmed.01JB2K7Q9X", "mime_type": "application/pdf",
                 "file_size": 184320, "sha256": "9b1f…", "expires_at": "2026-11-19T14:00:00Z"}


def resp(desc, schema=None, example=None, headers=None):
    r = {"description": desc}
    if schema:
        c = {"schema": schema}
        if example is not None:
            c["example"] = example
        r["content"] = {"application/json": c}
    if headers:
        r["headers"] = headers
    return r


RESPONSES = {
    "BadRequest": resp(T("Requisição inválida.", "Invalid request.", "请求无效。"), ref("Error")),
    "Unauthorized": resp(T("Token ausente, inválido ou expirado.", "Missing, invalid or expired token.", "令牌缺失、无效或已过期。"), ref("Error"),
                         {"error": {"code": 1101, "type": "unauthorized", "message": "Access token expired.", "trace_id": "trc_1a2b"}}),
    "Forbidden": resp(T("A integração não tem o escopo ou acesso ao remetente.", "The app lacks the scope or access to the sender.", "应用缺少所需范围或无权使用该发送方。"), ref("Error")),
    "NotFound": resp(T("Recurso não encontrado.", "Resource not found.", "资源不存在。"), ref("Error")),
    "TooManyRequests": resp(T("Limite de requisições atingido. Respeite Retry-After.", "Rate limit reached. Honour Retry-After.", "超出速率限制，请遵循 Retry-After。"), ref("Error"),
                            headers={"Retry-After": {"schema": {"type": "integer"}}}),
    "ServerError": resp(T("Erro interno. Pode ser repetido com a mesma Idempotency-Key.", "Internal error. Safe to retry with the same Idempotency-Key.", "服务器内部错误，可使用相同的 Idempotency-Key 重试。"), ref("Error")),
}


def op(tag, summary, desc, opid, **kw):
    o = {"tags": [tag], "summary": summary, "description": desc, "operationId": opid}
    o.update(kw)
    return o


PATHS = {
    "/oauth/token": {"post": op("Auth",
        T("Obter access token", "Get access token", "获取访问令牌"),
        T("Troca client_id e client_secret por um access token Bearer (OAuth 2.0, RFC 6749 §4.4). Não há refresh token: quando o token expirar, peça outro. Aceita `application/x-www-form-urlencoded` (padrão OAuth) e `application/json`.",
          "Exchanges client_id and client_secret for a Bearer access token (OAuth 2.0, RFC 6749 §4.4). There is no refresh token: when the token expires, request a new one. Accepts `application/x-www-form-urlencoded` (OAuth standard) and `application/json`.",
          "使用 client_id 和 client_secret 换取 Bearer 访问令牌（OAuth 2.0，RFC 6749 §4.4）。不提供刷新令牌：令牌过期后重新申请即可。支持 `application/x-www-form-urlencoded`（OAuth 标准）和 `application/json`。"),
        "getToken",
        security=[],
        requestBody={"required": True, "content": {
            "application/x-www-form-urlencoded": {"schema": ref("TokenRequest")},
            "application/json": {"schema": ref("TokenRequest"),
                                 "example": {"grant_type": "client_credentials", "client_id": "app_2Fk81PzQ", "client_secret": "phzsk_live_9c1f…", "scope": "messages:send messages:read"}}}},
        responses={"200": resp(T("Token emitido.", "Token issued.", "令牌已签发。"), ref("TokenResponse"),
                               {"access_token": "eyJhbGciOiJFUzI1NiIs…", "token_type": "Bearer", "expires_in": 3600, "scope": "messages:send messages:read", "merchant_id": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57"}),
                   "400": resp(T("Pedido inválido (`invalid_request`, `invalid_scope`, `unsupported_grant_type`).", "Invalid request (`invalid_request`, `invalid_scope`, `unsupported_grant_type`).", "请求无效（`invalid_request`、`invalid_scope`、`unsupported_grant_type`）。"), ref("OAuthError")),
                   "401": resp(T("Credenciais inválidas (`invalid_client`).", "Invalid credentials (`invalid_client`).", "凭证无效（`invalid_client`）。"), ref("OAuthError"), {"error": "invalid_client", "error_description": "Client authentication failed."}),
                   "429": err("TooManyRequests")})},
    "/oauth/revoke": {"post": op("Auth",
        T("Revogar token", "Revoke token", "撤销令牌"),
        T("Revoga um access token antes da expiração (RFC 7009). Sempre responde 200, mesmo se o token já era inválido.",
          "Revokes an access token before it expires (RFC 7009). Always returns 200, even if the token was already invalid.",
          "在过期前撤销访问令牌（RFC 7009）。即使令牌已无效也返回 200。"),
        "revokeToken", security=[],
        requestBody={"required": True, "content": {"application/x-www-form-urlencoded": {"schema": {"type": "object", "required": ["token", "client_id", "client_secret"], "properties": {
            "token": {"type": "string"}, "client_id": {"type": "string"}, "client_secret": {"type": "string"}}}}}},
        responses={"200": {"description": "OK"}})},
    "/v1/me": {"get": op("Auth",
        T("Inspecionar token atual", "Inspect current token", "查看当前令牌"),
        T("Retorna app, comerciante, escopos e remetentes autorizados do token usado. Útil para diagnosticar integrações (equivale ao debug_token da Meta).",
          "Returns the app, merchant, scopes and allowed senders of the token in use. Useful to debug integrations (equivalent to Meta's debug_token).",
          "返回当前令牌对应的应用、商户、范围和可用发送方，便于排查集成问题（相当于 Meta 的 debug_token）。"),
        "getMe", responses={"200": resp("OK", ref("TokenInfo")), "401": err("Unauthorized")})},
    "/v1/merchants/{merchant_id}": {"get": op("Account",
        T("Consultar conta de comerciante", "Get merchant account", "查询商户账号"),
        T("Dados da conta de comerciante dona do app.", "Details of the merchant account that owns the app.", "应用所属商户账号的信息。"),
        "getMerchant", parameters=[MERCHANT_ID],
        responses={"200": resp("OK", ref("Merchant")), **STD_ERRORS, "404": err("NotFound")})},
    "/v1/merchants/{merchant_id}/senders": {"get": op("Account",
        T("Listar remetentes", "List senders", "列出发送方"),
        T("Remetentes que a integração pode usar: o próprio comerciante (sempre presente) e, se houver, os canais liberados.",
          "Senders the integration may use: the merchant itself (always present) and, if any, the allowed channels.",
          "集成可使用的发送方：商户本身（始终存在），以及已授权的频道（如有）。"),
        "listSenders", parameters=[MERCHANT_ID,
            {"name": "cursor", "in": "query", "schema": {"type": "string"}},
            {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 25, "maximum": 100}}],
        responses={"200": resp("OK", ref("SenderList")), **STD_ERRORS})},
    "/v1/senders/{sender_id}": {"get": op("Account",
        T("Consultar remetente", "Get sender", "查询发送方"),
        T("Status, limite de envio e qualidade do remetente.", "Sender status, messaging limit and quality.", "发送方状态、发送额度与质量评级。"),
        "getSender", parameters=[SENDER_ID],
        responses={"200": resp("OK", ref("Sender")), **STD_ERRORS, "404": err("NotFound")})},
    "/v1/{sender_id}/messages": {"post": op("Messages",
        T("Enviar mensagem", "Send message", "发送消息"),
        T("""Envia uma mensagem para um telefone (E.164) ou PHIZ ID, em nome do comerciante (`sender_id` = `merchant_id`) ou, opcionalmente, por um de seus canais. A resposta `202` só confirma que a mensagem foi aceita; o resultado final (`sent`, `delivered`, `read` ou `failed`) chega pelo webhook `message_status`.

Mensagens iniciadas pelo comerciante seguem a política de opt-in, que será definida por Produto.

O mesmo endpoint com `status: read` marca uma mensagem recebida como lida (compatível com a Cloud API).""",
          """Sends a message to a phone number (E.164) or PHIZ ID, on behalf of the merchant (`sender_id` = `merchant_id`) or, optionally, through one of its channels. The `202` response only confirms the message was accepted; the final outcome (`sent`, `delivered`, `read` or `failed`) arrives through the `message_status` webhook.

Merchant-initiated messages follow the opt-in policy, to be defined by Product.

The same endpoint with `status: read` marks an inbound message as read (Cloud API compatible).""",
          """以商户名义（`sender_id` = `merchant_id`）或可选地通过商户的某个频道，向手机号（E.164）或 PHIZ ID 发送消息。`202` 仅表示消息已被受理；最终结果（`sent`、`delivered`、`read` 或 `failed`）通过 `message_status` Webhook 推送。

商户主动发送的消息需遵守选择接收（opt-in）策略，该策略由产品定义。

同一接口传入 `status: read` 可将收到的消息标记为已读（兼容 Cloud API）。"""),
        "sendMessage", parameters=[SENDER_ID, IDEMPOTENCY],
        requestBody={"required": True, "content": {"application/json": {
            "schema": {"oneOf": [ref("SendMessageRequest"), ref("MarkReadRequest")]},
            "examples": {
                "text_phone": {"summary": T("Texto para telefone", "Text to phone number", "向手机号发送文本"), "value": {
                    "messaging_product": "phiz", "to": "+5511987654321", "to_type": "phone", "type": "text",
                    "text": {"body": "Olá, Maria! Seu pedido #48213 foi enviado.", "preview_url": False},
                    "biz_opaque_callback_data": "pedido=48213"}},
                "text_phiz_id": {"summary": T("Texto para PHIZ ID", "Text to PHIZ ID", "向 PHIZ ID 发送文本"), "value": {
                    "to": "839201447", "to_type": "phiz_id", "type": "text", "text": {"body": "Seu cupom chegou: PHIZ10"}}},
                "image": {"summary": T("Imagem pelo id da mídia", "Image by media id", "通过媒体 id 发送图片"), "value": {
                    "to": "+5511987654321", "type": "image", "image": {"id": "pmed.01JB2K3H2D", "caption": "Nota fiscal"}}},
                "audio": {"summary": T("Áudio pelo id da mídia", "Audio by media id", "通过媒体 id 发送音频"), "value": {
                    "to": "+5511987654321", "type": "audio", "audio": {"id": "pmed.01JB2K4M7A"}}},
                "video": {"summary": T("Vídeo pelo link PHIZ", "Video by PHIZ link", "通过 PHIZ 链接发送视频"), "value": {
                    "to": "839201447", "to_type": "phiz_id", "type": "video",
                    "video": {"link": "https://media.phiz.chat/biz/pmed.01JB2K5V1C", "caption": "Como montar seu produto"}}},
                "document": {"summary": T("Documento", "Document", "文档"), "value": {
                    "to": "+5511987654321", "type": "document",
                    "document": {"id": "pmed.01JB2K7Q9X", "filename": "nota-fiscal-48213.pdf", "caption": "Nota fiscal do pedido #48213"}}},
                "buttons": {"summary": T("Botões de resposta", "Reply buttons", "快捷回复按钮"), "value": {
                    "to": "+5511987654321", "type": "interactive", "interactive": {"type": "button",
                        "body": {"text": "Confirma a entrega amanhã entre 9h e 12h?"},
                        "action": {"buttons": [{"type": "reply", "reply": {"id": "confirmar", "title": "Confirmar"}},
                                                {"type": "reply", "reply": {"id": "reagendar", "title": "Reagendar"}}]}}}},
                "mark_read": {"summary": T("Marcar como lida", "Mark as read", "标记为已读"), "value": {
                    "messaging_product": "phiz", "status": "read", "message_id": "pmid.IN_01JA9W2C"}},
            }}}},
        responses={"202": resp(T("Mensagem aceita para envio.", "Message accepted for delivery.", "消息已受理。"), ref("SendMessageResponse"),
                               {"messaging_product": "phiz", "contacts": [{"input": "+5511987654321", "phiz_id": None}],
                                "messages": [{"id": "pmid.01JA9VZ6T8R3", "message_status": "accepted"}]}),
                   **STD_ERRORS,
                   "409": resp(T("Idempotency-Key reutilizada com corpo diferente.", "Idempotency-Key reused with a different body.", "Idempotency-Key 被用于不同的请求体。"), ref("Error")),
                   "422": resp(T("Envio não permitido pela política de opt-in, tipo não permitido para o remetente, ou mídia expirada (2303).", "Sending not allowed by the opt-in policy, type not allowed for the sender, or media expired (2303).", "选择接收策略不允许此次发送、该发送方不允许此类型，或媒体已过期（2303）。"), ref("Error"),
                               {"error": {"code": 2201, "type": "policy_violation", "message": "Sending to this recipient is not allowed by the opt-in policy.", "trace_id": "trc_77ac"}})})},
    "/v1/{sender_id}/media": {"post": op("Media",
        T("Enviar mídia (upload)", "Upload media", "上传媒体"),
        T("""Envia um arquivo para o armazenamento temporário da PHIZ e devolve `id` e `link` para usar no envio. Formato e tamanho são checados aqui: fora da tabela da seção 09, responde 415 (2304) ou 413 (2305).

O arquivo fica disponível até `expires_at` (proposta: 30 dias) e pode ser usado em vários envios de remetentes da mesma conta de comerciante. Requer o escopo `messages:send`.""",
          """Uploads a file to PHIZ temporary storage and returns the `id` and `link` to use when sending. Format and size are checked here: outside the table in section 09, it answers 415 (2304) or 413 (2305).

The file stays available until `expires_at` (proposed: 30 days) and can be used in many sends by senders of the same merchant account. Requires the `messages:send` scope.""",
          """将文件上传到 PHIZ 临时存储，返回发送时使用的 `id` 和 `link`。格式和大小在此校验：不符合第 09 节表格时返回 415（2304）或 413（2305）。

文件在 `expires_at` 之前可用（建议 30 天），可被同一商户账号下的发送方多次使用。需要 `messages:send` 范围。"""),
        "uploadMedia", parameters=[SENDER_ID],
        requestBody={"required": True, "content": {"multipart/form-data": {"schema": ref("MediaUploadRequest")}}},
        responses={"200": resp(T("Mídia armazenada.", "Media stored.", "媒体已存储。"), ref("Media"), MEDIA_EXAMPLE),
                   **STD_ERRORS,
                   "413": resp(T("Arquivo acima do tamanho máximo do tipo (2305).", "File above the maximum size for its type (2305).", "文件超过该类型的大小上限（2305）。"), ref("Error")),
                   "415": resp(T("Formato não aceito (2304).", "Format not accepted (2304).", "格式不受支持（2304）。"), ref("Error"))})},
    "/v1/media/{media_id}": {
        "get": op("Media", T("Consultar mídia", "Get media", "查询媒体"),
                  T("Link, tipo, tamanho e validade de uma mídia enviada por upload.", "Link, type, size and expiry of an uploaded media file.", "查询已上传媒体的链接、类型、大小和有效期。"),
                  "getMedia", parameters=[{"name": "media_id", "in": "path", "required": True, "schema": {"type": "string"}, "example": "pmed.01JB2K7Q9X"}],
                  responses={"200": resp("OK", ref("Media"), MEDIA_EXAMPLE), **STD_ERRORS, "404": err("NotFound")}),
        "delete": op("Media", T("Remover mídia", "Delete media", "删除媒体"),
                     T("Apaga a mídia antes do prazo. Envios que ainda usem o `id` ou o `link` falham com 2303.", "Deletes the media before it expires. Sends that still use the `id` or `link` fail with 2303.", "在到期前删除媒体。仍使用该 `id` 或 `link` 的发送将返回 2303。"),
                     "deleteMedia", parameters=[{"name": "media_id", "in": "path", "required": True, "schema": {"type": "string"}, "example": "pmed.01JB2K7Q9X"}],
                     responses={"204": {"description": T("Mídia removida.", "Media deleted.", "媒体已删除。")}, **STD_ERRORS, "404": err("NotFound")})},
    "/v1/messages/{message_id}": {"get": op("Messages",
        T("Consultar status da mensagem", "Get message status", "查询消息状态"),
        T("Último status conhecido de uma mensagem enviada. Use como contingência; o webhook continua sendo a fonte principal. Dados retidos por 30 dias.",
          "Latest known status of a sent message. Use as a fallback; the webhook remains the primary source. Data retained for 30 days.",
          "查询已发送消息的最新状态，作为兜底手段；Webhook 仍为主要来源。数据保留 30 天。"),
        "getMessage", parameters=[{"name": "message_id", "in": "path", "required": True, "schema": {"type": "string"}, "example": "pmid.01JA9VZ6T8R3"}],
        responses={"200": resp("OK", ref("MessageStatus"), {"id": "pmid.01JA9VZ6T8R3", "sender_id": "1231", "status": "delivered",
                                                            "updated_at": "2026-10-15T11:42:07Z", "biz_opaque_callback_data": "pedido=48213", "errors": []}),
                   **STD_ERRORS, "404": err("NotFound")})},
    "/v1/apps/{app_id}/webhook": {
        "get": op("Webhooks", T("Consultar webhook", "Get webhook", "查询 Webhook"),
                  T("Configuração e saúde da assinatura de webhook do app.", "App webhook subscription settings and health.", "应用 Webhook 订阅配置及健康状态。"),
                  "getWebhook", parameters=[APP_ID], responses={"200": resp("OK", ref("WebhookConfig")), **STD_ERRORS}),
        "put": op("Webhooks", T("Configurar webhook", "Set webhook", "配置 Webhook"),
                  T("Define URL, verify_token e eventos. A PHIZ faz o handshake GET na URL antes de ativar; se falhar, responde 422.",
                    "Sets URL, verify_token and events. PHIZ performs the GET handshake on the URL before activating; if it fails, returns 422.",
                    "设置 URL、verify_token 和订阅事件。PHIZ 会先对 URL 发起 GET 握手，失败则返回 422。"),
                  "setWebhook", parameters=[APP_ID],
                  requestBody={"required": True, "content": {"application/json": {"schema": ref("WebhookConfig")}}},
                  responses={"200": resp("OK", ref("WebhookConfig")), **STD_ERRORS,
                             "422": resp(T("Handshake de verificação falhou.", "Verification handshake failed.", "验证握手失败。"), ref("Error"))}),
        "delete": op("Webhooks", T("Remover webhook", "Remove webhook", "删除 Webhook"),
                     T("Para de enviar eventos para o app.", "Stops delivering events to the app.", "停止向应用推送事件。"),
                     "deleteWebhook", parameters=[APP_ID], responses={"204": {"description": "No Content"}, **STD_ERRORS})},
    "/v1/apps/{app_id}/webhook/test": {"post": op("Webhooks",
        T("Enviar evento de teste", "Send test event", "发送测试事件"),
        T("Dispara um evento `messages` de exemplo, assinado, para a URL configurada.", "Fires a signed sample `messages` event to the configured URL.", "向已配置的 URL 推送一条已签名的 `messages` 示例事件。"),
        "testWebhook", parameters=[APP_ID],
        requestBody={"content": {"application/json": {"schema": {"type": "object", "properties": {"field": {"type": "string", "enum": ["messages", "message_status"]}}}}}},
        responses={"202": {"description": "Accepted"}, **STD_ERRORS})},
    "/v1/apps/{app_id}/webhook/deliveries": {"get": op("Webhooks",
        T("Listar entregas de webhook", "List webhook deliveries", "列出 Webhook 投递记录"),
        T("Histórico das últimas 72 h com status HTTP, tentativas e latência. Permite reenviar entregas que falharam.",
          "History of the last 72 h with HTTP status, attempts and latency. Failed deliveries can be replayed.",
          "最近 72 小时的投递记录，含 HTTP 状态、重试次数与延迟，可重放失败的投递。"),
        "listDeliveries", parameters=[APP_ID, {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["succeeded", "failed", "pending"]}}],
        responses={"200": {"description": "OK"}, **STD_ERRORS})},
    "/v1/apps/{app_id}/webhook/deliveries/{delivery_id}/replay": {"post": op("Webhooks",
        T("Reenviar entrega", "Replay delivery", "重放投递"),
        T("Reenvia um evento com o mesmo `X-Phiz-Delivery-Id`.", "Re-sends an event with the same `X-Phiz-Delivery-Id`.", "使用相同 `X-Phiz-Delivery-Id` 重新推送事件。"),
        "replayDelivery", parameters=[APP_ID, {"name": "delivery_id", "in": "path", "required": True, "schema": {"type": "string"}}],
        responses={"202": {"description": "Accepted"}, **STD_ERRORS})},
}

INBOUND_EXAMPLE = {
    "object": "phiz_merchant_account",
    "entry": [{"id": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57", "changes": [{"field": "messages", "value": {
        "messaging_product": "phiz",
        "metadata": {"sender_id": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57", "sender_type": "merchant", "conversation_type": "business_account", "display_name": "Loja Exemplo"},
        "contacts": [{"profile": {"name": "Maria Souza"}, "phiz_id": "839201447", "phone": "+5511987654321"}],
        "messages": [{"from": "839201447", "id": "pmid.IN_01JA9W2C", "timestamp": "1760528527", "type": "text",
                      "text": {"body": "Quero reagendar a entrega"}, "context": {"id": "pmid.01JA9VZ6T8R3"}}]}}]}],
}
STATUS_EXAMPLE = {
    "object": "phiz_merchant_account",
    "entry": [{"id": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57", "changes": [{"field": "message_status", "value": {
        "messaging_product": "phiz",
        "metadata": {"sender_id": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57", "sender_type": "merchant", "conversation_type": "business_account", "display_name": "Loja Exemplo"},
        "statuses": [{"id": "pmid.01JA9VZ6T8R3", "status": "delivered", "timestamp": "1760528410",
                      "recipient_id": "839201447", "biz_opaque_callback_data": "pedido=48213",
                      "conversation": {"id": "conv_01JA9W", "origin": {"type": "service"}, "expires_at": "1760614810"}}]}}]}],
}
FAILED_EXAMPLE = {
    "object": "phiz_merchant_account",
    "entry": [{"id": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57", "changes": [{"field": "message_status", "value": {
        "messaging_product": "phiz",
        "metadata": {"sender_id": "7f3e2a10-5b8c-4d21-9e6f-2a1c0b9d4e57", "sender_type": "merchant", "conversation_type": "business_account", "display_name": "Loja Exemplo"},
        "statuses": [{"id": "pmid.01JA9X0QW1", "status": "failed", "timestamp": "1760528600", "recipient_id": "+5511900000000",
                      "errors": [{"code": 2104, "title": "recipient_not_reachable",
                                  "message": "The phone number is not linked to a PHIZ account or blocked this sender.",
                                  "href": "https://developers.phiz.chat/docs/errors#2104"}]}]}}]}],
}

SIG_HEADERS = {
    "X-Phiz-Signature-256": {"schema": {"type": "string"}, "example": "sha256=6f1c…",
                             "description": T("HMAC-SHA256 de `{timestamp}.{corpo bruto}` com o webhook secret do app.",
                                              "HMAC-SHA256 of `{timestamp}.{raw body}` using the app's webhook secret.",
                                              "使用应用 webhook secret 对 `{timestamp}.{原始请求体}` 计算的 HMAC-SHA256。")},
    "X-Phiz-Timestamp": {"schema": {"type": "integer"}, "example": 1760528527,
                         "description": T("Unix epoch do envio. Rejeite se diferir mais de 5 min.", "Unix epoch of the send. Reject if more than 5 min off.", "发送时的 Unix 时间戳，偏差超过 5 分钟应拒绝。")},
    "X-Phiz-Delivery-Id": {"schema": {"type": "string"}, "example": "dlv_01JA9W2D7K",
                           "description": T("Igual em todas as tentativas do mesmo evento. Use para descartar duplicados.",
                                            "Same across retries of the same event. Use it to drop duplicates.",
                                            "同一事件的所有重试均相同，可用于去重。")},
}

WEBHOOKS = {
    "verification": {"get": {
        "tags": ["Webhooks"],
        "summary": T("Handshake de verificação (GET no seu servidor)", "Verification handshake (GET on your server)", "验证握手（对您服务器发起的 GET）"),
        "description": T("A PHIZ chama sua URL com `hub.mode=subscribe`, `hub.verify_token` e `hub.challenge`. Confira o token e responda 200 com o valor de `hub.challenge` em texto puro.",
                         "PHIZ calls your URL with `hub.mode=subscribe`, `hub.verify_token` and `hub.challenge`. Check the token and answer 200 with the `hub.challenge` value as plain text.",
                         "PHIZ 会携带 `hub.mode=subscribe`、`hub.verify_token` 和 `hub.challenge` 调用您的 URL。校验令牌后，以纯文本返回 200 和 `hub.challenge` 的值。"),
        "parameters": [
            {"name": "hub.mode", "in": "query", "schema": {"type": "string", "enum": ["subscribe"]}},
            {"name": "hub.verify_token", "in": "query", "schema": {"type": "string"}},
            {"name": "hub.challenge", "in": "query", "schema": {"type": "string"}, "example": "1158201444"}],
        "responses": {"200": {"description": T("Corpo = hub.challenge.", "Body = hub.challenge.", "响应体 = hub.challenge。"),
                              "content": {"text/plain": {"schema": {"type": "string"}, "example": "1158201444"}}}}}},
    "messages": {"post": {
        "tags": ["Webhooks"],
        "summary": T("Mensagem recebida do usuário", "Message received from the user", "收到用户消息"),
        "description": T("Enviado quando um usuário PHIZ manda mensagem para um remetente do comerciante. Responda 2xx em até 10 s e processe de forma assíncrona.",
                         "Sent when a PHIZ user messages one of the merchant's senders. Answer 2xx within 10 s and process asynchronously.",
                         "当 PHIZ 用户向商户的发送方发送消息时推送。请在 10 秒内返回 2xx，并异步处理。"),
        "parameters": [{"name": k, "in": "header", "required": True, **{kk: vv for kk, vv in v.items()}} for k, v in SIG_HEADERS.items()],
        "requestBody": {"content": {"application/json": {"schema": ref("WebhookEvent"), "example": INBOUND_EXAMPLE}}},
        "responses": {"200": {"description": "OK"}}}},
    "message_status": {"post": {
        "tags": ["Webhooks"],
        "summary": T("Mudança de status de mensagem enviada", "Status change of a sent message", "已发送消息的状态变更"),
        "description": T("Um evento por transição: `sent` → `delivered` → `read`, ou `failed` com `errors`. A ordem de chegada não é garantida; use `timestamp`.",
                         "One event per transition: `sent` → `delivered` → `read`, or `failed` with `errors`. Arrival order is not guaranteed; use `timestamp`.",
                         "每次状态变化推送一次：`sent` → `delivered` → `read`，或带 `errors` 的 `failed`。不保证到达顺序，请以 `timestamp` 为准。"),
        "parameters": [{"name": k, "in": "header", "required": True, **{kk: vv for kk, vv in v.items()}} for k, v in SIG_HEADERS.items()],
        "requestBody": {"content": {"application/json": {"schema": ref("WebhookEvent"),
                                                         "examples": {"delivered": {"value": STATUS_EXAMPLE}, "failed": {"value": FAILED_EXAMPLE}}}}},
        "responses": {"200": {"description": "OK"}}}},
}

SPEC = {
    "openapi": "3.1.0",
    "info": {"title": "PHIZ Business Messaging API", "version": "1.0.0-draft",
             "description": INFO_DESC,
             "contact": {"name": "PHIZ Open Platform", "url": "https://open.phiz.chat"}},
    "servers": [
        {"url": "https://{gateway}/gateway/business", "description": T("Produção: gateway atual da PHIZ, prefixo /gateway/business", "Production: current PHIZ gateway, /gateway/business prefix", "生产环境：现有 PHIZ 网关，前缀 /gateway/business"),
         "variables": {"gateway": {"default": "gateway.phiz.chat", "description": T("Host do gateway de produção (valor ilustrativo).", "Production gateway host (illustrative value).", "生产网关主机（示例值）。")}}},
        {"url": "https://{gateway}/gateway/business", "description": T("Sandbox: gateway de testes (Openapi-test), mesmo prefixo", "Sandbox: test gateway (Openapi-test), same prefix", "沙箱环境：测试网关（Openapi-test），相同前缀"),
         "variables": {"gateway": {"default": "gateway-test.phiz.chat", "description": T("Host do gateway de testes (valor ilustrativo).", "Test gateway host (illustrative value).", "测试网关主机（示例值）。")}}},
    ],
    "tags": TAGS,
    "security": [{"bearerAuth": []}],
    "paths": PATHS,
    "webhooks": WEBHOOKS,
    "components": {
        "securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
            "oauth2": {"type": "oauth2", "flows": {"clientCredentials": {"tokenUrl": "https://gateway.phiz.chat/gateway/business/oauth/token", "scopes": {
                "messages:send": T("Enviar mensagens e mídias", "Send messages and media", "发送消息和媒体"),
                "messages:read": T("Ler status de mensagens", "Read message statuses", "读取消息状态"),
                "webhooks:manage": T("Gerenciar webhook do app", "Manage app webhook", "管理应用 Webhook"),
                "account:read": T("Ler conta e remetentes", "Read account and senders", "读取账号与发送方"),
                "templates:manage": T("Reservado para a Marketing API", "Reserved for the Marketing API", "预留给 Marketing API")}}}}},
        "schemas": SCHEMAS,
        "responses": RESPONSES,
    },
}

EXAMPLES = {"inbound": INBOUND_EXAMPLE, "status": STATUS_EXAMPLE, "failed": FAILED_EXAMPLE}


def build(lang):
    return resolve(copy.deepcopy(SPEC), lang)


if __name__ == "__main__":
    for lang in ("pt", "en", "zh"):
        s = build(lang)
        with open(f"out/phiz-messaging-api.{lang}.openapi.yaml", "w") as f:
            yaml.safe_dump(s, f, allow_unicode=True, sort_keys=False, width=110)
    print("ok")
