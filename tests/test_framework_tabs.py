"""Os separadores do framework mudam de nome sem mudar os endereços."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as site


def _tabs(html):
    start = html.find('class="fw-tabs"')
    end = html.find("</nav>", start)
    return html[start:end]


def test_framework_tab_labels_and_links():
    client = site.app.test_client()
    pt = client.get("/framework").get_data(as_text=True)
    en = client.get("/en/framework").get_data(as_text=True)
    pt_agents = client.get("/framework/agentes").get_data(as_text=True)
    en_agents = client.get("/en/framework/agents").get_data(as_text=True)

    assert '>Regulamentação</a>' in _tabs(pt)
    assert '>Agentes AI</a>' in _tabs(pt)
    assert 'href="/framework"' in _tabs(pt)
    assert 'href="/framework/agentes"' in _tabs(pt)
    assert ">AI Act</a>" not in _tabs(pt)
    assert "O AI Act foi alterado" in pt
    assert "EU AI Act — Regulamentação Europeia" in pt
    assert "EU AI Act — European Regulation" in en
    pubs = client.get("/publicacoes").get_data(as_text=True)
    assert "regulamentação europeia" in pubs
    assert "regulação europeia" not in pubs

    assert '>Regulation</a>' in _tabs(en)
    assert '>Agentic AI</a>' in _tabs(en)
    assert 'href="/en/framework"' in _tabs(en)
    assert 'href="/en/framework/agents"' in _tabs(en)
    assert ">AI Act</a>" not in _tabs(en)
    assert "The AI Act was amended" in en

    assert '>Regulamentação</a>' in _tabs(pt_agents)
    assert '>Agentes AI</a>' in _tabs(pt_agents)
    assert '>Regulation</a>' in _tabs(en_agents)
    assert '>Agentic AI</a>' in _tabs(en_agents)
    assert "AI agents" in en_agents
