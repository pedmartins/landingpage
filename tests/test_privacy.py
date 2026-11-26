"""Páginas legais e rodapé."""
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
    assert "Prestação dos nossos serviços de consultoria de dados" in body
    assert "Envio de informação sobre formação e eventos" in body
    assert "TODO" not in body
    assert "morada" not in body.lower()
    assert "AI-GOV.NETWORK é uma marca da LINKWITH UNIPESSOAL, LDA" in body
    assert 'href="/termos"' in body
    assert 'href="/politica-de-privacidade"' in body

    en = client.get("/en/privacy-policy")
    assert en.status_code == 200
    en_body = en.get_data(as_text=True)
    assert "Provision of our data consulting services" in en_body
    assert "Management of consultation bookings and related communications" in en_body
    assert "Sending information about training and events" in en_body
    assert "Compliance with legal and regulatory obligations" in en_body
    assert "Improvement of our services and user experience" in en_body
    assert "Statistical and website performance analysis" in en_body
    assert "17 November 2026" in en_body
    assert "TODO" not in en_body
    assert "postal address" not in en_body.lower()
    assert 'href="/en/terms"' in en_body

    terms = client.get("/termos")
    assert terms.status_code == 200
    terms_body = terms.get_data(as_text=True)
    assert "Termos de" in terms_body
    assert "lei portuguesa" in terms_body
    assert 'href="/politica-de-privacidade"' in terms_body

    terms_en = client.get("/en/terms")
    assert terms_en.status_code == 200
    assert "Terms of" in terms_en.get_data(as_text=True)
    assert "Portuguese law" in terms_en.get_data(as_text=True)

    home = client.get("/")
    assert home.status_code == 200
    home_body = home.get_data(as_text=True)
    assert "AI-GOV.NETWORK é uma marca da LINKWITH UNIPESSOAL, LDA" in home_body
    assert home_body.count("<footer") == 1

    home_en = client.get("/en")
    assert home_en.status_code == 200
    home_en_body = home_en.get_data(as_text=True)
    assert "AI-GOV.NETWORK is a brand of LINKWITH UNIPESSOAL, LDA" in home_en_body
    assert "Terms" in home_en_body
    assert home_en_body.count("<footer") == 1

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    xml = sitemap.get_data(as_text=True)
    assert "/politica-de-privacidade" in xml
    assert "/en/privacy-policy" in xml
    assert "/termos" in xml
    assert "/en/terms" in xml

    for path in ("/framework", "/en/framework", "/observatorio", "/en/observatory", "/book", "/en/book",
                 "/publicacoes", "/en/publicacoes", "/lab"):
        page = client.get(path)
        assert page.status_code == 200, path
        html = page.get_data(as_text=True)
        assert html.count("<footer") == 1, path
        if path.startswith("/en") or path == "/lab":
            assert "Privacy Policy" in html, path
            assert 'href="/en/terms"' in html, path
        else:
            assert "Política de Privacidade" in html, path
            assert 'href="/termos"' in html, path
