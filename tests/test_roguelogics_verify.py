"""Ficheiro de verificação RogueLogics em /.well-known/."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as site

TOKEN = "78023cdc952e3ddd0a77f356c62ad4e376c76d0b"
PATH = "/.well-known/roguelogics-verify.txt"
HOSTS = ("ai-gov.network", "www.ai-gov.network")


def test_verification_file_is_the_token_plus_one_newline():
    raw = open(
        os.path.join(site.app.static_folder, ".well-known", "roguelogics-verify.txt"),
        "rb",
    ).read()
    assert raw == TOKEN.encode("ascii") + b"\n"
    assert raw.count(b"\n") == 1


def test_verification_route_returns_exact_body():
    response = site.app.test_client().get(PATH)
    assert response.status_code == 200
    assert response.mimetype == "text/plain"
    assert response.headers["Content-Type"] == "text/plain"
    assert response.data == TOKEN.encode("ascii") + b"\n"
    assert response.headers.get("Location") is None


def test_verification_route_does_not_redirect_on_www_or_apex():
    client = site.app.test_client()
    for host in HOSTS:
        for scheme in ("https", "http"):
            response = client.get(PATH, base_url=f"{scheme}://{host}")
            assert response.status_code == 200, f"{scheme}://{host}"
            assert response.data == TOKEN.encode("ascii") + b"\n"
            assert response.headers["Content-Type"] == "text/plain"
            assert response.headers.get("Location") is None
