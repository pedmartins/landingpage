"""O menu móvel tem de existir em todas as páginas com o cabeçalho do site."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import render_template

import app as site


ROUTES = [
    ("/", "Abrir menu", False),
    ("/en", "Open menu", False),
    ("/framework", "Abrir menu", False),
    ("/en/framework", "Open menu", False),
    ("/observatorio", "Abrir menu", False),
    ("/en/observatory", "Open menu", False),
    ("/framework/agentes", "Abrir menu", True),
    ("/en/framework/agents", "Open menu", True),
    ("/publicacoes", "Abrir menu", False),
    ("/publicacoes/ai-gov", "Abrir menu", False),
    ("/en/publicacoes", "Open menu", False),
    ("/en/publicacoes/ai-gov", "Open menu", False),
    ("/politica-de-privacidade", "Abrir menu", False),
    ("/en/privacy-policy", "Open menu", False),
    ("/termos", "Abrir menu", False),
    ("/en/terms", "Open menu", False),
    ("/book", "Abrir menu", False),
    ("/en/book", "Open menu", False),
    ("/lab", "Open menu", False),
]


def _assert_menu(html, label, wide=False):
    assert html.count('class="nav-toggle"') == 1
    assert 'aria-controls="site-nav-links"' in html
    assert 'aria-expanded="false"' in html
    assert f'aria-label="{label}"' in html
    assert 'data-label-close="Fechar menu"' in html or 'data-label-close="Close menu"' in html
    assert 'id="site-nav-links"' in html
    assert "\u2630" in html  # ☰
    assert "max-width: 820px" in html
    assert "Escape" in html
    if wide:
        assert "nav-collapse-wide" in html
    else:
        assert "nav-collapse-wide" not in html.split("<nav", 1)[-1].split(">", 1)[0]


def test_routed_pages_expose_the_menu_button():
    client = site.app.test_client()
    for path, label, wide in ROUTES:
        page = client.get(path)
        assert page.status_code == 200, path
        _assert_menu(page.get_data(as_text=True), label, wide)


def test_article_and_training_templates():
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
        pt_course = render_template("formacao.html", course=course, lang="pt")
        en_course = render_template("formacao.html", course=course, lang="en")
        pt_article = render_template("article.html", article=article, lang="pt")
        en_article = render_template("article.html", article=article, lang="en")
    _assert_menu(pt_course, "Abrir menu")
    _assert_menu(en_course, "Open menu")
    _assert_menu(pt_article, "Abrir menu")
    _assert_menu(en_article, "Open menu")
    assert 'data-label-close="Fechar menu"' in pt_course
    assert 'data-label-close="Close menu"' in en_article
