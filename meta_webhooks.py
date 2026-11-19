"""Callback de webhooks da Meta em /webhooks/meta.

Cobre mensagens WhatsApp Business, mensagens Instagram, Lead Ads (leadgen)
e alterações ao catálogo de produtos.

Não há sessão nem CSRF neste projeto. A única autenticação é o token de
verificação (GET) e o HMAC X-Hub-Signature-256 (POST). Se no futuro existir
proteção CSRF global, este blueprint tem de ficar isento: a Meta não envia
cookies nem token de formulário. As vistas estão marcadas com csrf_exempt
para esse caso.
"""
import hashlib
import hmac
import json
import os
import re

from flask import Blueprint, Response, current_app, request

meta_webhooks_bp = Blueprint("meta_webhooks", __name__)

# Corpos de webhook da Meta são pequenos (eventos, não ficheiros). 1 MiB
# corta pedidos abusivos sem rejeitar um lote legítimo de eventos.
MAX_BODY_BYTES = 1024 * 1024

_OBJECT_RE = re.compile(r"[a-z0-9_]{1,64}")
_FIELD_RE = re.compile(r"[A-Za-z0-9_]{1,64}")
_ID_RE = re.compile(r"[A-Za-z0-9_.=+\-/:.]{1,256}")
_TOKEN_RE = re.compile(r"[a-z0-9_]{1,32}")

_CATALOG_OBJECTS = {"product_catalog", "catalog"}
_CATALOG_FIELDS = {
    "products",
    "product_feed",
    "product_review",
    "product_item",
    "items_batch",
    "localized_items",
    "catalog",
}
_LEADGEN_ID_KEYS = (
    "leadgen_id",
    "page_id",
    "form_id",
    "ad_id",
    "adgroup_id",
    "adset_id",
)
_CATALOG_ID_KEYS = (
    "catalog_id",
    "product_id",
    "product_item_id",
    "product_feed_id",
    "retailer_id",
    "item_id",
    "retailer_product_group_id",
    "variant_id",
)
_IG_ID_KEYS = ("id", "comment_id", "media_id", "post_id", "parent_id")


def handle_whatsapp(entry):
    # TODO: enfileirar mensagens e estados do WhatsApp Business.
    # Nos logs, só ids (wamid, phone_number_id, id da conta). Nunca o corpo
    # da mensagem, wa_id, número apresentado ou nome do contacto.
    return None


def handle_instagram(entry):
    # TODO: enfileirar eventos de mensagens e alterações do Instagram.
    # Nos logs, só ids. Nunca o texto da mensagem, usernames ou comentários.
    return None


def handle_leadgen(entry, change):
    # TODO: ir buscar a lead à Graph API com leadgen_id.
    # Nunca registar field_data (nomes, emails, telefones).
    return None


def handle_catalog(entry, change):
    # TODO: sincronizar o item do catálogo a partir dos ids de produto.
    return None


def _forbidden():
    return Response("Forbidden", status=403, mimetype="text/plain")


def _safe_id(value):
    """Id opaco (não um telefone ou email que tenha sido passado por engano)."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        if value < 0:
            return None
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None
    if _ID_RE.fullmatch(text):
        return text
    return None


def _object_name(value):
    if isinstance(value, str) and _OBJECT_RE.fullmatch(value):
        return value
    return "unknown"


def _field_name(value):
    if isinstance(value, str) and _FIELD_RE.fullmatch(value):
        return value
    return None


def _token(value):
    if isinstance(value, str) and _TOKEN_RE.fullmatch(value):
        return value
    return None


def _id_list(items):
    found = []
    if not isinstance(items, list):
        return found
    for item in items:
        if isinstance(item, dict):
            safe = _safe_id(item.get("id"))
            if safe:
                found.append(safe)
    return found


def _log(summary):
    clean = {}
    for key, value in summary.items():
        if value is None or value == [] or value == "":
            continue
        clean[key] = value
    current_app.logger.info(
        "meta_webhook %s",
        json.dumps(clean, sort_keys=True, separators=(",", ":")),
    )


def _run(handler, *args):
    try:
        handler(*args)
    except Exception:
        current_app.logger.exception(
            "meta_webhook handler %s failed", handler.__name__
        )


def _signature_matches(raw, provided, secret):
    digest = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    expected = "sha256=" + digest
    if not isinstance(provided, str):
        return False
    return hmac.compare_digest(expected, provided)


def _read_body(limit):
    """Lê no máximo limit+1 bytes. None se o corpo exceder o limite."""
    if request.content_length is not None and request.content_length > limit:
        return None
    buf = bytearray()
    stream = request.stream
    while len(buf) <= limit:
        chunk = stream.read(min(65536, limit - len(buf) + 1))
        if not chunk:
            break
        buf.extend(chunk)
    if len(buf) > limit:
        return None
    return bytes(buf)


def _is_catalog_field(field):
    if not field:
        return False
    return field in _CATALOG_FIELDS or field.startswith("product_") or "catalog" in field


def _is_catalog_object(obj):
    return obj in _CATALOG_OBJECTS or "catalog" in obj


def _summarize_whatsapp_change(entry, change):
    value = change.get("value") if isinstance(change.get("value"), dict) else {}
    metadata = value.get("metadata") if isinstance(value.get("metadata"), dict) else {}
    messages = value.get("messages") if isinstance(value.get("messages"), list) else []
    statuses = value.get("statuses") if isinstance(value.get("statuses"), list) else []
    types = []
    for message in messages:
        if isinstance(message, dict):
            kind = _token(message.get("type"))
            if kind:
                types.append(kind)
    status_names = []
    conversation_ids = []
    for status in statuses:
        if not isinstance(status, dict):
            continue
        name = _token(status.get("status"))
        if name:
            status_names.append(name)
        conversation = status.get("conversation")
        if isinstance(conversation, dict):
            cid = _safe_id(conversation.get("id"))
            if cid:
                conversation_ids.append(cid)
    error_codes = []
    errors = value.get("errors")
    if isinstance(errors, list):
        for error in errors:
            if isinstance(error, dict) and isinstance(error.get("code"), int) and not isinstance(error.get("code"), bool):
                error_codes.append(error["code"])
    summary = {
        "object": "whatsapp_business_account",
        "entry_id": _safe_id(entry.get("id")),
        "field": _field_name(change.get("field")),
        "phone_number_id": _safe_id(metadata.get("phone_number_id")),
        "message_ids": _id_list(messages),
        "message_types": types,
        "status_ids": _id_list(statuses),
        "statuses": status_names,
        "conversation_ids": conversation_ids,
        "error_codes": error_codes,
    }
    return summary


def _summarize_instagram_change(entry, change):
    value = change.get("value") if isinstance(change.get("value"), dict) else {}
    summary = {
        "object": "instagram",
        "entry_id": _safe_id(entry.get("id")),
        "field": _field_name(change.get("field")),
    }
    for key in _IG_ID_KEYS:
        safe = _safe_id(value.get(key))
        if safe:
            summary[key] = safe
    sender = value.get("from") if isinstance(value.get("from"), dict) else None
    if sender:
        from_id = _safe_id(sender.get("id"))
        if from_id:
            summary["from_id"] = from_id
    return summary


def _summarize_instagram_messaging(entry, messaging):
    message_ids = []
    sender_ids = []
    recipient_ids = []
    for event in messaging:
        if not isinstance(event, dict):
            continue
        message = event.get("message") if isinstance(event.get("message"), dict) else {}
        mid = _safe_id(message.get("mid"))
        if mid:
            message_ids.append(mid)
        read = event.get("read") if isinstance(event.get("read"), dict) else {}
        read_mid = _safe_id(read.get("mid"))
        if read_mid:
            message_ids.append(read_mid)
        sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}
        recipient = event.get("recipient") if isinstance(event.get("recipient"), dict) else {}
        sender_id = _safe_id(sender.get("id"))
        recipient_id = _safe_id(recipient.get("id"))
        if sender_id:
            sender_ids.append(sender_id)
        if recipient_id:
            recipient_ids.append(recipient_id)
    return {
        "object": "instagram",
        "entry_id": _safe_id(entry.get("id")),
        "field": "messages",
        "message_ids": message_ids,
        "sender_ids": sender_ids,
        "recipient_ids": recipient_ids,
    }


def _summarize_leadgen(entry, change):
    value = change.get("value") if isinstance(change.get("value"), dict) else {}
    summary = {
        "object": "page",
        "entry_id": _safe_id(entry.get("id")),
        "field": "leadgen",
    }
    for key in _LEADGEN_ID_KEYS:
        safe = _safe_id(value.get(key))
        if safe:
            summary[key] = safe
    return summary


def _summarize_catalog(entry, change, obj):
    value = change.get("value") if isinstance(change.get("value"), dict) else {}
    summary = {
        "object": obj,
        "entry_id": _safe_id(entry.get("id")),
        "field": _field_name(change.get("field")),
    }
    for key in _CATALOG_ID_KEYS:
        safe = _safe_id(value.get(key))
        if safe:
            summary[key] = safe
    nested = None
    for key in ("products", "product_ids", "items"):
        if isinstance(value.get(key), list):
            nested = value[key]
            break
    product_ids = []
    if isinstance(nested, list):
        product_ids.extend(_id_list(nested))
        for item in nested:
            safe = _safe_id(item)
            if safe:
                product_ids.append(safe)
    if product_ids:
        summary["product_ids"] = product_ids
    return summary


def _dispatch_whatsapp(entry):
    changes = entry.get("changes")
    logged = False
    if isinstance(changes, list):
        for change in changes:
            if isinstance(change, dict):
                _log(_summarize_whatsapp_change(entry, change))
                logged = True
    if not logged:
        _log({
            "object": "whatsapp_business_account",
            "entry_id": _safe_id(entry.get("id")),
        })
    _run(handle_whatsapp, entry)


def _dispatch_instagram(entry):
    changes = entry.get("changes")
    messaging = entry.get("messaging")
    logged = False
    if isinstance(changes, list):
        for change in changes:
            if isinstance(change, dict):
                _log(_summarize_instagram_change(entry, change))
                logged = True
    if isinstance(messaging, list) and messaging:
        _log(_summarize_instagram_messaging(entry, messaging))
        logged = True
    if not logged:
        _log({"object": "instagram", "entry_id": _safe_id(entry.get("id"))})
    _run(handle_instagram, entry)


def _dispatch_page(entry):
    changes = entry.get("changes")
    if not isinstance(changes, list) or not changes:
        _log({"object": "page", "entry_id": _safe_id(entry.get("id"))})
        return
    for change in changes:
        if not isinstance(change, dict):
            continue
        field = _field_name(change.get("field"))
        if field == "leadgen":
            _log(_summarize_leadgen(entry, change))
            _run(handle_leadgen, entry, change)
        elif _is_catalog_field(field):
            _log(_summarize_catalog(entry, change, "page"))
            _run(handle_catalog, entry, change)
        else:
            _log({
                "object": "page",
                "entry_id": _safe_id(entry.get("id")),
                "field": field,
            })


def _dispatch_catalog(entry, obj):
    changes = entry.get("changes")
    logged = False
    if isinstance(changes, list):
        for change in changes:
            if isinstance(change, dict):
                _log(_summarize_catalog(entry, change, obj))
                _run(handle_catalog, entry, change)
                logged = True
    if not logged:
        _log({"object": obj, "entry_id": _safe_id(entry.get("id"))})


def _dispatch_unknown(entry, obj):
    fields = []
    changes = entry.get("changes")
    if isinstance(changes, list):
        for change in changes:
            if isinstance(change, dict):
                name = _field_name(change.get("field"))
                if name:
                    fields.append(name)
    _log({
        "object": obj,
        "entry_id": _safe_id(entry.get("id")),
        "fields": fields,
    })


def dispatch(payload):
    """Encaminha cada entry para o handler do objeto/campo."""
    if not isinstance(payload, dict):
        return
    obj = _object_name(payload.get("object"))
    entries = payload.get("entry")
    if not isinstance(entries, list) or not entries:
        _log({"object": obj})
        return
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if obj == "whatsapp_business_account":
            _dispatch_whatsapp(entry)
        elif obj == "instagram":
            _dispatch_instagram(entry)
        elif obj == "page":
            _dispatch_page(entry)
        elif _is_catalog_object(obj):
            _dispatch_catalog(entry, obj)
        else:
            _dispatch_unknown(entry, obj)


@meta_webhooks_bp.route("/webhooks/meta", methods=["GET"])
def meta_webhook_verify():
    expected = os.environ.get("META_VERIFY_TOKEN")
    if not expected:
        current_app.logger.warning(
            "META_VERIFY_TOKEN is not set; rejecting Meta webhook verification"
        )
        return _forbidden()

    mode = request.args.get("hub.mode", "")
    given = request.args.get("hub.verify_token", "")
    # Comparar sempre que o token existe, para a verificação ser em tempo constante.
    token_ok = isinstance(given, str) and hmac.compare_digest(given, expected)
    if mode == "subscribe" and token_ok:
        challenge = request.args.get("hub.challenge", "")
        return Response(challenge, status=200, mimetype="text/plain")
    return _forbidden()


@meta_webhooks_bp.route("/webhooks/meta", methods=["POST"])
def meta_webhook_receive():
    secret = os.environ.get("META_APP_SECRET")
    if not secret:
        current_app.logger.warning(
            "META_APP_SECRET is not set; rejecting Meta webhook event"
        )
        return _forbidden()

    raw = _read_body(MAX_BODY_BYTES)
    if raw is None:
        current_app.logger.warning(
            "meta_webhook rejected: body exceeds %s bytes", MAX_BODY_BYTES
        )
        return Response("Payload Too Large", status=413, mimetype="text/plain")

    provided = request.headers.get("X-Hub-Signature-256") or ""
    if not _signature_matches(raw, provided, secret):
        current_app.logger.warning("meta_webhook rejected: invalid signature")
        return _forbidden()

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        current_app.logger.warning("meta_webhook rejected: invalid json")
        return Response("Bad Request", status=400, mimetype="text/plain")

    if not isinstance(payload, dict):
        current_app.logger.warning("meta_webhook rejected: payload is not an object")
        return Response("Bad Request", status=400, mimetype="text/plain")

    dispatch(payload)
    return Response("EVENT_RECEIVED", status=200, mimetype="text/plain")


meta_webhook_verify.csrf_exempt = True
meta_webhook_receive.csrf_exempt = True
