"""Páginas de privacidade e rodapé legal."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as site


def test_privacy_pages_and_sitemap():
    client = site.app.test_client()

    pt = client.get("/politica-de-privacidade")
    assert pt.status_code == 200
    body = pt.get_data(as_text=True)
    assert "LINKWITH UNIPESSOAL, LDA" in body
    assert "NIPC 517054124" in body
    assert "info@ai-gov.network" in body
    assert "17 de novembro de 2026" in body
    assert "www.cnpd.pt" in body
    assert "TODO:" in body
    assert "Política de Privacidade" in body
    assert 'href="/politica-de-privacidade"' in body

    en = client.get("/en/privacy-policy")
    assert en.status_code == 200
    en_body = en.get_data(as_text=True)
    assert "Privacy Policy" in en_body
    assert "17 November 2026" in en_body
    assert 'href="/en/privacy-policy"' in en_body
    assert "TODO:" in en_body

    home = client.get("/")
    assert home.status_code == 200
    home_body = home.get_data(as_text=True)
    assert "ai-gov.network é uma marca da LINKWITH UNIPESSOAL, LDA" in home_body
    assert home_body.count("<footer") == 1

    home_en = client.get("/en")
    assert home_en.status_code == 200
    home_en_body = home_en.get_data(as_text=True)
    assert "ai-gov.network is a brand of LINKWITH UNIPESSOAL, LDA" in home_en_body
    assert home_en_body.count("<footer") == 1

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    xml = sitemap.get_data(as_text=True)
    assert "/politica-de-privacidade" in xml
    assert "/en/privacy-policy" in xml

    for path in ("/framework", "/en/framework", "/observatorio", "/book", "/en/book",
                 "/publicacoes", "/en/publicacoes", "/lab"):
        page = client.get(path)
        assert page.status_code == 200, path
        html = page.get_data(as_text=True)
        assert html.count("<footer") == 1, path
        if path.startswith("/en") or path == "/lab":
            assert "Privacy Policy" in html, path
        else:
            assert "Política de Privacidade" in html, path
