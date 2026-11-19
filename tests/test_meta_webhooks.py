"""Callback /webhooks/meta: verificação GET e assinatura POST."""
import hashlib
import hmac
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as site
import meta_webhooks


VERIFY = "verify-token-test"
SECRET = "app-secret-test"


def _sign(body, secret=SECRET):
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return "sha256=" + digest


def _client():
    return site.app.test_client()


def _post(client, body, signature):
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Hub-Signature-256"] = signature
    return client.post("/webhooks/meta", data=body, headers=headers)


def test_verify_success(monkeypatch):
    monkeypatch.setenv("META_VERIFY_TOKEN", VERIFY)
    challenge = "1158201444"
    rv = _client().get(
        "/webhooks/meta?hub.mode=subscribe"
        f"&hub.verify_token={VERIFY}&hub.challenge={challenge}"
    )
    assert rv.status_code == 200
    assert rv.get_data(as_text=True) == challenge
    assert rv.mimetype == "text/plain"


def test_verify_wrong_token(monkeypatch):
    monkeypatch.setenv("META_VERIFY_TOKEN", VERIFY)
    rv = _client().get(
        "/webhooks/meta?hub.mode=subscribe&hub.verify_token=nope&hub.challenge=999"
    )
    assert rv.status_code == 403
    assert rv.mimetype == "text/plain"
    assert "999" not in rv.get_data(as_text=True)


def test_verify_wrong_mode(monkeypatch):
    monkeypatch.setenv("META_VERIFY_TOKEN", VERIFY)
    rv = _client().get(
        "/webhooks/meta?hub.mode=unsubscribe"
        f"&hub.verify_token={VERIFY}&hub.challenge=999"
    )
    assert rv.status_code == 403
    assert "999" not in rv.get_data(as_text=True)


def test_verify_missing_env_logs_warning(monkeypatch, caplog):
    monkeypatch.delenv("META_VERIFY_TOKEN", raising=False)
    with caplog.at_level(logging.WARNING, logger=site.app.logger.name):
        rv = _client().get(
            "/webhooks/meta?hub.mode=subscribe&hub.verify_token=x&hub.challenge=999"
        )
    assert rv.status_code == 403
    assert "999" not in rv.get_data(as_text=True)
    assert "META_VERIFY_TOKEN" in caplog.text


def test_verify_empty_env_is_rejected(monkeypatch):
    monkeypatch.setenv("META_VERIFY_TOKEN", "")
    rv = _client().get(
        "/webhooks/meta?hub.mode=subscribe&hub.verify_token=&hub.challenge=999"
    )
    assert rv.status_code == 403
    assert "999" not in rv.get_data(as_text=True)


def test_post_valid_signature_whatsapp(monkeypatch, caplog):
    monkeypatch.setenv("META_APP_SECRET", SECRET)
    seen = {}

    def fake(entry):
        seen["id"] = entry["id"]

    monkeypatch.setattr(meta_webhooks, "handle_whatsapp", fake)
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "waba-1",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "15551212",
                        "phone_number_id": "pnid-9",
                    },
                    "contacts": [{
                        "wa_id": "351912345678",
                        "profile": {"name": "Ada Lovelace"},
                    }],
                    "messages": [{
                        "from": "351912345678",
                        "id": "wamid.ABC",
                        "timestamp": "1710000000",
                        "type": "text",
                        "text": {"body": "super-secret-body"},
                    }],
                    "statuses": [{
                        "id": "wamid.STATUS",
                        "status": "delivered",
                        "recipient_id": "351900000001",
                        "conversation": {"id": "conv-1"},
                    }],
                },
            }],
        }],
    }
    body = json.dumps(payload).encode()
    with caplog.at_level(logging.INFO, logger=site.app.logger.name):
        rv = _post(_client(), body, _sign(body))
    assert rv.status_code == 200
    assert rv.get_data(as_text=True) == "EVENT_RECEIVED"
    assert rv.mimetype == "text/plain"
    assert seen["id"] == "waba-1"
    text = caplog.text
    for present in (
        "wamid.ABC",
        "wamid.STATUS",
        "pnid-9",
        "waba-1",
        "conv-1",
        "messages",
        "whatsapp_business_account",
    ):
        assert present in text
    for absent in (
        "super-secret-body",
        "351912345678",
        "351900000001",
        "Ada Lovelace",
        "15551212",
        SECRET,
    ):
        assert absent not in text


def test_post_invalid_signature(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", SECRET)
    called = {"n": 0}
    monkeypatch.setattr(
        meta_webhooks,
        "handle_whatsapp",
        lambda entry: called.__setitem__("n", called["n"] + 1),
    )
    body = json.dumps({
        "object": "whatsapp_business_account",
        "entry": [{"id": "waba-1", "changes": []}],
    }).encode()
    rv = _post(_client(), body, "sha256=" + ("0" * 64))
    assert rv.status_code == 403
    assert "EVENT_RECEIVED" not in rv.get_data(as_text=True)
    assert called["n"] == 0


def test_post_missing_signature(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", SECRET)
    body = b'{"object":"instagram","entry":[]}'
    rv = _post(_client(), body, None)
    assert rv.status_code == 403


def test_post_wrong_prefix(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", SECRET)
    body = b'{"object":"instagram","entry":[]}'
    digest = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    rv = _post(_client(), body, "sha1=" + digest)
    assert rv.status_code == 403


def test_post_tampered_body(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", SECRET)
    body = b'{"object":"instagram","entry":[]}'
    tampered = b'{"object":"instagram","entry":[{"id":"ig-1"}]}'
    rv = _post(_client(), tampered, _sign(body))
    assert rv.status_code == 403


def test_post_missing_secret_logs_warning(monkeypatch, caplog):
    monkeypatch.delenv("META_APP_SECRET", raising=False)
    body = b'{"object":"instagram","entry":[]}'
    with caplog.at_level(logging.WARNING, logger=site.app.logger.name):
        rv = _post(_client(), body, _sign(body))
    assert rv.status_code == 403
    assert "META_APP_SECRET" in caplog.text
    assert "EVENT_RECEIVED" not in rv.get_data(as_text=True)


def test_instagram_leadgen_and_catalog(monkeypatch, caplog):
    monkeypatch.setenv("META_APP_SECRET", SECRET)
    seen = {"instagram": 0, "leadgen": 0, "catalog": 0}

    monkeypatch.setattr(
        meta_webhooks, "handle_instagram",
        lambda entry: seen.__setitem__("instagram", seen["instagram"] + 1),
    )
    monkeypatch.setattr(
        meta_webhooks, "handle_leadgen",
        lambda entry, change: seen.__setitem__("leadgen", seen["leadgen"] + 1),
    )
    monkeypatch.setattr(
        meta_webhooks, "handle_catalog",
        lambda entry, change: seen.__setitem__("catalog", seen["catalog"] + 1),
    )

    instagram = {
        "object": "instagram",
        "entry": [{
            "id": "ig-user-1",
            "messaging": [{
                "sender": {"id": "sender-1"},
                "recipient": {"id": "recipient-1"},
                "message": {"mid": "mid.1", "text": "hello-private-text"},
            }],
        }],
    }
    leadgen = {
        "object": "page",
        "entry": [{
            "id": "page-1",
            "changes": [{
                "field": "leadgen",
                "value": {
                    "leadgen_id": "lead-9",
                    "page_id": "page-1",
                    "form_id": "form-3",
                    "field_data": [
                        {"name": "email", "values": ["person@example.com"]},
                        {"name": "phone_number", "values": ["+351900000000"]},
                    ],
                },
            }],
        }],
    }
    catalog = {
        "object": "product_catalog",
        "entry": [{
            "id": "catalog-1",
            "changes": [{
                "field": "product_feed",
                "value": {
                    "product_feed_id": "feed-7",
                    "product_id": "prod-2",
                    "title": "Private Product Title",
                },
            }],
        }],
    }
    client = _client()
    with caplog.at_level(logging.INFO, logger=site.app.logger.name):
        for payload in (instagram, leadgen, catalog):
            body = json.dumps(payload).encode()
            rv = _post(client, body, _sign(body))
            assert rv.status_code == 200, payload["object"]
            assert rv.get_data(as_text=True) == "EVENT_RECEIVED"
    assert seen == {"instagram": 1, "leadgen": 1, "catalog": 1}
    text = caplog.text
    for present in ("mid.1", "sender-1", "lead-9", "form-3", "feed-7", "prod-2", "leadgen"):
        assert present in text
    for absent in (
        "hello-private-text",
        "person@example.com",
        "+351900000000",
        "Private Product Title",
        "field_data",
    ):
        assert absent not in text


def test_handler_error_still_returns_event_received(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", SECRET)

    def boom(entry):
        raise RuntimeError("handler failed")

    monkeypatch.setattr(meta_webhooks, "handle_instagram", boom)
    body = json.dumps({
        "object": "instagram",
        "entry": [{"id": "ig-1", "messaging": [{"message": {"mid": "m1"}}]}],
    }).encode()
    rv = _post(_client(), body, _sign(body))
    assert rv.status_code == 200
    assert rv.get_data(as_text=True) == "EVENT_RECEIVED"


def test_invalid_json_is_rejected(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", SECRET)
    body = b"not-json"
    rv = _post(_client(), body, _sign(body))
    assert rv.status_code == 400


def test_body_over_limit_is_rejected(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", SECRET)
    monkeypatch.setattr(meta_webhooks, "MAX_BODY_BYTES", 64)
    body = b'{"object":"instagram","pad":"' + (b"x" * 200) + b'"}'
    rv = _post(_client(), body, _sign(body))
    assert rv.status_code == 413


def test_webhook_is_not_in_sitemap_or_nav(monkeypatch):
    monkeypatch.setenv("META_VERIFY_TOKEN", VERIFY)
    client = _client()
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "/webhooks/meta" not in sitemap.get_data(as_text=True)
    for path in ("/", "/en"):
        page = client.get(path)
        assert page.status_code == 200
        assert "/webhooks/meta" not in page.get_data(as_text=True)
