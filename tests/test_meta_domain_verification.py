"""Ficheiro de verificação de domínio da Meta na raiz do site."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as site

TOKEN = "blj9d2hmf73otrtcilhc7x0ncqix03"
PATH = f"/{TOKEN}.html"
HOSTS = ("ai-gov.network", "www.ai-gov.network")


def test_verification_file_is_the_token_without_newline():
    raw = open(
        os.path.join(site.app.static_folder, f"{TOKEN}.html"),
        "rb",
    ).read()
    assert raw == TOKEN.encode("ascii")
    assert not raw.endswith(b"\n")


def test_verification_route_returns_exact_body():
    response = site.app.test_client().get(PATH)
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert response.headers["Content-Type"] == "text/html"
    assert response.data == TOKEN.encode("ascii")
    assert response.headers.get("Location") is None


def test_verification_route_does_not_redirect_on_www_or_apex():
    client = site.app.test_client()
    for host in HOSTS:
        for scheme in ("https", "http"):
            response = client.get(PATH, base_url=f"{scheme}://{host}")
            assert response.status_code == 200, f"{scheme}://{host}"
            assert response.data == TOKEN.encode("ascii")
            assert response.headers["Content-Type"] == "text/html"
            assert response.headers.get("Location") is None
