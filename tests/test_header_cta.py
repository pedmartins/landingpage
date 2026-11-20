"""O cabeçalho troca a frase de missão por um convite para agendar."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import render_template

import app as site

PT_ROUTES = ["/", "/framework", "/observatorio", "/publicacoes", "/book", "/politica-de-privacidade", "/termos", "/framework/agentes"]
EN_ROUTES = ["/en", "/en/framework", "/en/publicacoes", "/en/book", "/en/privacy-policy", "/en/terms", "/en/framework/agents", "/lab"]


def test_header_cta_replaces_the_booking_button_and_keeps_the_mission():
    client = site.app.test_client()
    home = client.get("/").get_data(as_text=True)
    assert 'class="header-cta" href="/book"' in home
    assert "Disponível" in home and "Agendar sessão" in home
    assert "Agendar Sessão" not in home
    assert "Converter <strong>AI</strong> em vantagens competitivas reais e sustentáveis" in home
    assert 'class="page-mission"' in home
    # A frase saiu do sítio antigo, ao lado da marca.
    brand = home.split('class="nav-brand"', 1)[1].split("</a>", 1)[0]
    assert "vantagens competitivas" not in brand

    en = client.get("/en").get_data(as_text=True)
    assert 'class="header-cta" href="/en/book"' in en
    assert "Available" in en and "Talk to us" in en
    assert "Book a Call" not in en
    assert "Turning <strong>AI</strong> into real, sustainable competitive advantage" in en

    for path in PT_ROUTES:
        page = client.get(path)
        assert page.status_code == 200, path
        html = page.get_data(as_text=True)
        assert 'class="header-cta" href="/book"' in html, path
        assert 'class="page-mission"' in html, path
        assert 'class="nav-tagline"' not in html, path

    for path in EN_ROUTES:
        page = client.get(path)
        assert page.status_code == 200, path
        html = page.get_data(as_text=True)
        assert 'class="header-cta" href="/en/book"' in html, path
        assert 'class="page-mission"' in html, path
        assert 'class="nav-tagline"' not in html, path


def test_article_and_training_headers_follow_the_page_language():
    course = {
        "slug": "iso-42001",
        "name": "ISO 42001",
        "short_description": "",
        "description": "",
        "image": None,
        "category": "",
        "standard": "",
        "level": "",
        "duration": "",
        "languages": [],
        "sessions": [],
        "enquiry_url": "",
    }
    article = {
        "slug": "demo",
        "title": "Demo",
        "date": "2026-01-01",
        "excerpt": "",
        "content": "",
        "tags": [],
        "image_url": "",
        "author": {},
    }
    with site.app.app_context():
        pt_course = render_template("formacao.html", course=course, lang="pt", pt=True)
        en_course = render_template("formacao.html", course=course, lang="en", pt=False)
        pt_article = render_template("article.html", article=article, lang="pt")
        en_article = render_template("article.html", article=article, lang="en")
    assert 'href="/book"' in pt_course and 'href="/en/book"' in en_course
    assert 'href="/book"' in pt_article and 'href="/en/book"' in en_article
    assert "Agendar sessão" in pt_article and "Talk to us" in en_article
    assert "#A9DD22" in pt_course
    assert "prefers-reduced-motion" in pt_course
