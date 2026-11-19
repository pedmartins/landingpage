"""Ícone do site e marca no cabeçalho."""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
from flask import render_template

import app as site

CREAM = (251, 252, 246)
LIME = (169, 221, 34)

ICON_LINK = '<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">'
PNG_LINK = '<link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32.png">'
APPLE_LINK = '<link rel="apple-touch-icon" sizes="180x180" href="/static/apple-touch-icon.png">'
MARK = 'class="nav-mark"'
MARK_VIEWBOX = 'viewBox="0 0 850 910"'

ROUTES = [
    "/",
    "/en",
    "/framework",
    "/en/framework",
    "/observatorio",
    "/framework/agentes",
    "/en/framework/agents",
    "/publicacoes",
    "/en/publicacoes",
    "/politica-de-privacidade",
    "/en/privacy-policy",
    "/termos",
    "/en/terms",
    "/book",
    "/en/book",
    "/lab",
]


def _lime_runs(im):
    y = im.height // 2
    runs = []
    current = None
    for x in range(im.width):
        lime = im.getpixel((x, y))[:3] == LIME
        if lime != current:
            runs.append(lime)
            current = lime
    return runs


def test_svg_icon_file():
    svg = open(os.path.join(site.app.static_folder, "favicon.svg"), encoding="utf-8").read()
    assert 'viewBox="0 0 1024 879"' in svg
    assert 'fill="#FBFCF6"' in svg
    assert 'fill="#A9DD22"' in svg
    assert svg.count("<rect") == 4


def test_png_fallbacks_are_square_and_centered():
    folder = site.app.static_folder
    png32 = Image.open(os.path.join(folder, "favicon-32.png"))
    apple = Image.open(os.path.join(folder, "apple-touch-icon.png"))
    assert png32.size == (32, 32)
    assert apple.size == (180, 180)
    for im in (png32, apple):
        assert im.mode == "RGB"
        assert im.getpixel((0, 0)) == CREAM
        assert im.getpixel((im.width - 1, im.height - 1)) == CREAM
        assert im.getpixel((im.width // 2, im.height // 2)) == LIME
        # Three lime bars separated by cream, group centered.
        runs = _lime_runs(im)
        assert runs == [False, True, False, True, False, True, False], runs


def test_favicon_ico_route():
    client = site.app.test_client()
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.mimetype == "image/x-icon"
    ico = Image.open(io.BytesIO(response.data))
    assert ico.format == "ICO"
    assert set(ico.info["sizes"]) == {(16, 16), (32, 32), (48, 48)}

    svg = client.get("/static/favicon.svg")
    assert svg.status_code == 200
    assert svg.mimetype == "image/svg+xml"
    png = client.get("/static/favicon-32.png")
    assert png.status_code == 200
    assert png.mimetype == "image/png"


def _assert_icons(html):
    assert html.count(ICON_LINK) == 1
    assert PNG_LINK in html
    assert APPLE_LINK in html
    assert html.count(MARK) == 1
    assert MARK_VIEWBOX in html
    assert 'fill="currentColor"' in html
    assert 'aria-hidden="true"' in html
    # The mark is inside the same link as the name.
    brand = html.split('class="nav-brand"', 1)[1].split("</a>", 1)[0]
    assert MARK in brand
    assert "Pedro Martins" in brand
    assert brand.index(MARK) < brand.index("Pedro Martins")


def test_every_routed_page_has_icon_and_header_mark():
    client = site.app.test_client()
    for path in ROUTES:
        page = client.get(path)
        assert page.status_code == 200, path
        _assert_icons(page.get_data(as_text=True))


def test_article_and_training_templates_have_icon_and_header_mark():
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
        pages = [
            render_template("formacao.html", course=course, lang="pt"),
            render_template("formacao.html", course=course, lang="en"),
            render_template("article.html", article=article, lang="pt"),
            render_template("article.html", article=article, lang="en"),
        ]
    for html in pages:
        _assert_icons(html)
