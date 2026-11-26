"""O Observatório tem detalhe em inglês e o seletor de idioma aponta para a página equivalente."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as site

# Cada página mostra um único atalho para a equivalente na outra língua.
PAIRS = [
    ("/", "/en", "EN"),
    ("/en", "/", "PT"),
    ("/framework", "/en/framework", "EN"),
    ("/en/framework", "/framework", "PT"),
    ("/observatorio", "/en/observatory", "EN"),
    ("/en/observatory", "/observatorio", "PT"),
    ("/framework/agentes", "/en/framework/agents", "EN"),
    ("/en/framework/agents", "/framework/agentes", "PT"),
    ("/publicacoes", "/en/publicacoes/ai-gov", "EN"),
    ("/en/publicacoes", "/publicacoes/ai-gov", "PT"),
    ("/book", "/en/book", "EN"),
    ("/en/book", "/book", "PT"),
    ("/politica-de-privacidade", "/en/privacy-policy", "EN"),
    ("/en/privacy-policy", "/politica-de-privacidade", "PT"),
    ("/termos", "/en/terms", "EN"),
    ("/en/terms", "/termos", "PT"),
]


def test_language_switch_points_at_the_equivalent_page():
    client = site.app.test_client()
    for path, target, label in PAIRS:
        page = client.get(path)
        assert page.status_code == 200, path
        html = page.get_data(as_text=True)
        assert f'href="{target}">{label}<' in html, path


def test_observatory_detail_exists_in_both_languages():
    client = site.app.test_client()
    pt = client.get("/observatorio")
    en = client.get("/en/observatory")
    assert pt.status_code == 200 and en.status_code == 200
    pt_html = pt.get_data(as_text=True)
    en_html = en.get_data(as_text=True)
    assert 'src="/static/observatorio/procura-tic-anuncios-pt-ue.html"' in pt_html
    assert 'src="/static/observatorio/ict-specialist-demand-pt-eu.html"' in en_html
    assert 'href="/en/observatory">EN<' in pt_html
    assert 'href="/observatorio">PT<' in en_html
    assert "Procura de especialistas TIC" in pt_html
    assert "Demand for ICT specialists" in en_html

    home_en = client.get("/en").get_data(as_text=True)
    assert 'href="/en/observatory"' in home_en
    assert "Explore the data (PT)" not in home_en
    home_pt = client.get("/").get_data(as_text=True)
    assert 'href="/observatorio"' in home_pt

    detail = client.get("/static/observatorio/ict-specialist-demand-pt-eu.html")
    assert detail.status_code == 200
    body = detail.get_data(as_text=True)
    assert "Portugal seeks proportionally twice the share of ICT specialists" in body
    assert "How to read this" in body
    assert "Recruitment difficulty" in body
    assert "Como ler" not in body
    assert "Dificuldade de recrutamento" not in body
    assert "anúncios" not in body


NOTE_URL = "https://ec.europa.eu/eurostat/documents/7894008/20552398/methodological-note.pdf/df235c60-fc19-c1d2-d218-312ecbdf65c6"
PT_NOTE = (
    'Fonte — Eurostat, anúncios de emprego online. '
    f'<a href="{NOTE_URL}" target="_blank" rel="noopener noreferrer">Série estatística em desenvolvimento</a>, '
    "com cobertura parcial das vagas de emprego. A representatividade varia por profissão e setor."
)
EN_NOTE = (
    "Source — Eurostat, online job advertisements. "
    f'<a href="{NOTE_URL}" target="_blank" rel="noopener noreferrer">Statistical series under development</a>, '
    "covering only some job vacancies. Representativeness varies by occupation and sector."
)


def test_online_ads_source_note_is_exact_in_both_languages():
    client = site.app.test_client()
    pt_home = client.get("/").get_data(as_text=True)
    en_home = client.get("/en").get_data(as_text=True)
    pt_detail = client.get("/static/observatorio/procura-tic-anuncios-pt-ue.html").get_data(as_text=True)
    en_detail = client.get("/static/observatorio/ict-specialist-demand-pt-eu.html").get_data(as_text=True)
    assert PT_NOTE in pt_home and PT_NOTE in pt_detail
    assert EN_NOTE in en_home and EN_NOTE in en_detail
    assert "estatística experimental" not in pt_home
    assert "experimental statistics" not in en_home
    assert "estatística experimental" not in pt_detail
    assert "experimental statistics" not in en_detail.lower()
