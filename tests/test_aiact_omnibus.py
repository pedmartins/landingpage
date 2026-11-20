"""Omnibus copy on the AI Act pages, in Portuguese and English."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as site

PT = {
    "/framework": [
        "Atualização — Omnibus Digital sobre IA.",
        "Regulamento (UE) 2026/1744, em vigor desde 27 de julho de 2026",
        "Mesmo sem obrigações específicas, aplica-se o dever de literacia em IA (art. 4.º).",
        "Aplicável desde 2 de agosto de 2026 (o Omnibus não adiou estas obrigações).",
        "2 de dezembro de 2026",
        "Calendário revisto (Omnibus): sistemas do Anexo III",
        "2 de dezembro de 2027",
        "2 de agosto de 2028",
        "art. 27.º",
        "Biometria (Anexo III, ponto 1)",
        "Anexo I",
        "Às proibições em vigor desde fevereiro de 2025",
        "conteúdo íntimo não consentido",
        "small mid-caps",
        "entidades públicas ou privadas",
        "identificação biométrica remota em tempo real",
        "recolha não direcionada de imagens faciais",
        "policiamento preditivo",
        "Inferência de emoções no trabalho e na educação",
        "modelos de IA de finalidade geral (GPAI)",
        "Regulamento (UE) 2024/1689 (Artificial Intelligence Act), em vigor desde agosto de 2024, alterado pelo Regulamento (UE) 2026/1744",
        "https://www.whitecase.com/insight-alert/eu-ai-omnibus-enters-force-amending-ai-act",
    ],
}
EN = {
    "/en/framework": [
        "Update — Digital Omnibus on AI.",
        "Regulation (EU) 2026/1744, in force since 27 July 2026",
        "the AI literacy duty applies (Article 4)",
        "the Omnibus did not postpone these obligations",
        "2 December 2026",
        "Annex III systems, including credit, insurance, employment and education, from 2 December 2027",
        "2 August 2028",
        "Article 27",
        "Biometrics (Annex III, point 1)",
        "Annex I",
        "non-consensual intimate content",
        "child sexual abuse material",
        "small mid-caps, the lower of the two applies",
        "public or private entities",
        "real-time remote biometric identification",
        "untargeted scraping of facial images",
        "predictive policing",
        "Emotion recognition in the workplace and in education",
        "General-purpose AI (GPAI) models",
        "as amended by Regulation (EU) 2026/1744 (Digital Omnibus on AI), in force since 27 July 2026",
    ],
}

ABSENT = {
    "/framework": [
        "sistemas de recomendação com impacto nas escolhas",
        "sistemas de reconhecimento de emoções, deepfakes",
        "entidades governamentais",
        "vigilância biométrica em tempo real em espaços públicos",
    ],
    "/en/framework": [
        "emotion recognition systems, deepfakes",
        "recommendation systems that materially influence",
        "Social scoring by government entities",
        "real-time biometric surveillance in public spaces",
    ],
}


def test_omnibus_copy_is_present_and_shared_cell_stays():
    client = site.app.test_client()
    for path, needles in {**PT, **EN}.items():
        page = client.get(path)
        assert page.status_code == 200, path
        html = page.get_data(as_text=True)
        for needle in needles:
            assert needle in html, (path, needle)
        for needle in ABSENT[path]:
            assert needle not in html, (path, needle)
        assert html.count('class="info-panel"') == 4
        assert "grid-area: 1 / 1" in html
        assert 'class="gpai-note"' in html
        assert 'class="date-badge"' in html
        assert 'id="pyramid-svg"' in html
