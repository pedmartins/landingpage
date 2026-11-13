"""Gera CSV de importação WooCommerce com o catálogo PECB da CISODPO.

Estrutura: 1 produto agrupado por curso (visível na loja) + produtos externos
filhos (ocultos no catálogo): uma por edição futura + uma 'sob consulta'.
Fonte: https://cisodpo.com/academy/pecb-training (consultada a 2026-11-13).
"""
import csv, datetime, sys
from urllib.parse import urlencode

TODAY = datetime.date(2026, 11, 13)
BASE = "https://cisodpo.com/academy/pecb-training"
CAT_ROOT = "Formação > Formação Certificada PECB"

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# código, nome, norma, nível, área PT, tags, intro PT, público PT, intro EN, audience EN, edições 2026
COURSES = [
    ("27001-LI", "ISO/IEC 27001 Lead Implementer", "ISO/IEC 27001", "Lead Implementer", "Segurança da Informação", ["ISO 27001", "Segurança da Informação", "SGSI"],
     "Prepara-o para planear, implementar, gerir e manter um Sistema de Gestão de Segurança da Informação (SGSI) segundo a ISO/IEC 27001, desde a análise de contexto e definição do âmbito até à preparação para a auditoria de certificação.",
     "Responsáveis de segurança da informação (CISO), gestores de projeto, consultores e equipas de conformidade que lideram a implementação de um SGSI.",
     "Prepares you to plan, implement, manage and maintain an Information Security Management System (ISMS) based on ISO/IEC 27001, from context analysis and scoping through to readiness for the certification audit.",
     "Information security leads (CISOs), project managers, consultants and compliance teams leading an ISMS implementation.",
     [(1, 5, 9), (7, 6, 10)]),
    ("27001-LA", "ISO/IEC 27001 Lead Auditor", "ISO/IEC 27001", "Lead Auditor", "Segurança da Informação", ["ISO 27001", "Auditoria", "SGSI"],
     "Desenvolve as competências para planear, conduzir, reportar e acompanhar auditorias a Sistemas de Gestão de Segurança da Informação, aplicando os princípios da ISO 19011 e os requisitos da ISO/IEC 17021-1.",
     "Auditores internos e externos, consultores e profissionais que pretendem liderar auditorias de certificação ou de primeira, segunda e terceira parte a um SGSI.",
     "Builds the skills to plan, conduct, report on and follow up audits of Information Security Management Systems, applying the principles of ISO 19011 and the requirements of ISO/IEC 17021-1.",
     "Internal and external auditors, consultants and professionals who want to lead first-, second- or third-party ISMS audits.",
     [(1, 19, 23), (7, 20, 24)]),
    ("27701-LI", "ISO/IEC 27701 Lead Implementer", "ISO/IEC 27701", "Lead Implementer", "Gestão de Privacidade", ["ISO 27701", "Privacidade", "RGPD"],
     "Ensina a implementar e gerir um Sistema de Gestão da Informação de Privacidade (PIMS) segundo a ISO/IEC 27701, articulando os controlos de privacidade com as obrigações do RGPD.",
     "Encarregados de proteção de dados (DPO), juristas, responsáveis de segurança e consultores que estruturam programas de privacidade.",
     "Teaches you to implement and manage a Privacy Information Management System (PIMS) based on ISO/IEC 27701, aligning privacy controls with GDPR obligations.",
     "Data protection officers (DPOs), legal counsel, security leads and consultants building privacy programmes.",
     [(2, 2, 6), (8, 3, 7)]),
    ("27701-LA", "ISO/IEC 27701 Lead Auditor", "ISO/IEC 27701", "Lead Auditor", "Gestão de Privacidade", ["ISO 27701", "Privacidade", "Auditoria"],
     "Prepara-o para planear e conduzir auditorias a Sistemas de Gestão da Informação de Privacidade (PIMS), avaliando a conformidade com a ISO/IEC 27701 segundo boas práticas de auditoria.",
     "Auditores, DPO, consultores de privacidade e profissionais de conformidade que avaliam programas de proteção de dados.",
     "Prepares you to plan and conduct audits of Privacy Information Management Systems (PIMS), assessing conformity with ISO/IEC 27701 using recognised audit practice.",
     "Auditors, DPOs, privacy consultants and compliance professionals assessing data protection programmes.",
     [(2, 16, 20), (8, 17, 21)]),
    ("22301-LI", "ISO 22301 Lead Implementer", "ISO 22301", "Lead Implementer", "Continuidade de Negócio", ["ISO 22301", "Continuidade de Negócio", "Resiliência"],
     "Cobre a implementação de um Sistema de Gestão de Continuidade de Negócio (SGCN) segundo a ISO 22301: análise de impacto no negócio, estratégias de continuidade, planos de resposta e exercícios.",
     "Gestores de continuidade e de risco, responsáveis de operações e de TI, e consultores de resiliência organizacional.",
     "Covers implementing a Business Continuity Management System (BCMS) based on ISO 22301: business impact analysis, continuity strategies, response plans and exercising.",
     "Business continuity and risk managers, operations and IT leads, and organisational resilience consultants.",
     [(3, 2, 6), (9, 7, 11)]),
    ("22301-LA", "ISO 22301 Lead Auditor", "ISO 22301", "Lead Auditor", "Continuidade de Negócio", ["ISO 22301", "Continuidade de Negócio", "Auditoria"],
     "Desenvolve as competências para auditar Sistemas de Gestão de Continuidade de Negócio, desde o planeamento da auditoria até ao relatório e ao acompanhamento de não conformidades.",
     "Auditores internos e externos, gestores de continuidade e consultores que avaliam a maturidade de planos de continuidade.",
     "Builds the skills to audit Business Continuity Management Systems, from audit planning to reporting and follow-up of nonconformities.",
     "Internal and external auditors, continuity managers and consultants assessing the maturity of continuity arrangements.",
     [(3, 16, 20), (9, 21, 25)]),
    ("27005-LRM", "ISO/IEC 27005 Lead Risk Manager", "ISO/IEC 27005", "Lead Risk Manager", "Gestão de Risco", ["ISO 27005", "Gestão de Risco", "Segurança da Informação"],
     "Foca-se na gestão do risco de segurança da informação segundo a ISO/IEC 27005: identificação, análise, avaliação e tratamento de riscos, integrados no ciclo de um SGSI.",
     "Gestores de risco, responsáveis de segurança, auditores e consultores que conduzem avaliações de risco de segurança da informação.",
     "Focuses on information security risk management based on ISO/IEC 27005: risk identification, analysis, evaluation and treatment, integrated into the ISMS cycle.",
     "Risk managers, security leads, auditors and consultants running information security risk assessments.",
     [(4, 6, 10), (10, 5, 9)]),
    ("31000-LRM", "ISO 31000 Lead Risk Manager", "ISO 31000", "Lead Risk Manager", "Gestão de Risco", ["ISO 31000", "Gestão de Risco", "ERM"],
     "Aborda a conceção e operação de um quadro de gestão de risco organizacional segundo os princípios e diretrizes da ISO 31000, aplicável a qualquer tipo de risco e de organização.",
     "Gestores de risco, membros de funções de controlo, auditores e quadros que integram a gestão de risco na governação.",
     "Addresses the design and operation of an enterprise risk management framework based on the principles and guidelines of ISO 31000, applicable to any type of risk and organisation.",
     "Risk managers, control-function staff, auditors and executives embedding risk management in governance.",
     [(4, 20, 24), (10, 19, 23)]),
    ("42001-LI", "ISO/IEC 42001 Lead Implementer", "ISO/IEC 42001", "Lead Implementer", "Gestão de IA", ["ISO 42001", "AI Governance", "AI Act", "IA Responsável"],
     "Prepara-o para implementar um Sistema de Gestão de Inteligência Artificial (SGIA) segundo a ISO/IEC 42001: políticas, avaliação de impacto e de risco de sistemas de IA, controlos e melhoria contínua — uma base sólida para a conformidade com o AI Act.",
     "Responsáveis de governação de IA, equipas de dados e de conformidade, gestores de risco e consultores que estruturam a governação de sistemas de IA.",
     "Prepares you to implement an Artificial Intelligence Management System (AIMS) based on ISO/IEC 42001: policies, AI system impact and risk assessment, controls and continual improvement — a solid foundation for EU AI Act compliance.",
     "AI governance leads, data and compliance teams, risk managers and consultants structuring the governance of AI systems.",
     [(5, 4, 8), (11, 2, 6)]),
    ("42001-LA", "ISO/IEC 42001 Lead Auditor", "ISO/IEC 42001", "Lead Auditor", "Gestão de IA", ["ISO 42001", "AI Governance", "Auditoria", "IA Responsável"],
     "Desenvolve as competências para auditar Sistemas de Gestão de Inteligência Artificial segundo a ISO/IEC 42001, avaliando a eficácia dos controlos de governação, risco e ciclo de vida de sistemas de IA.",
     "Auditores, funções de conformidade e de auditoria interna, e consultores que avaliam a governação de IA em organizações reguladas.",
     "Builds the skills to audit Artificial Intelligence Management Systems against ISO/IEC 42001, assessing the effectiveness of governance, risk and AI lifecycle controls.",
     "Auditors, compliance and internal audit functions, and consultants assessing AI governance in regulated organisations.",
     [(5, 18, 22), (11, 16, 20)]),
    ("DORA-LM", "DORA Lead Manager", "DORA (Regulamento (UE) 2022/2554)", "Lead Manager", "Regulamentação UE", ["DORA", "Resiliência Operacional Digital", "Setor Financeiro"],
     "Cobre os requisitos do Regulamento DORA: gestão do risco de TIC, gestão e reporte de incidentes, testes de resiliência operacional digital, risco de terceiros prestadores de TIC e partilha de informação.",
     "Funções de risco, conformidade, segurança e TI de entidades financeiras, e consultores que apoiam a implementação do DORA.",
     "Covers the requirements of the DORA Regulation: ICT risk management, incident management and reporting, digital operational resilience testing, ICT third-party risk and information sharing.",
     "Risk, compliance, security and IT functions at financial entities, and consultants supporting DORA implementation.",
     [(6, 1, 5), (12, 7, 11)]),
    ("NIS2-LI", "NIS 2 Directive Lead Implementer", "Diretiva NIS 2 (UE) 2022/2555", "Lead Implementer", "Regulamentação UE", ["NIS 2", "Cibersegurança", "Regulamentação UE"],
     "Prepara-o para implementar um programa de cibersegurança conforme a Diretiva NIS 2: medidas de gestão de risco, governação e responsabilidade dos órgãos de gestão, notificação de incidentes e segurança da cadeia de abastecimento.",
     "Responsáveis de segurança e de conformidade em entidades essenciais e importantes, gestores de TI e consultores de cibersegurança.",
     "Prepares you to implement a cybersecurity programme aligned with the NIS 2 Directive: risk management measures, management-body governance and accountability, incident notification and supply chain security.",
     "Security and compliance leads at essential and important entities, IT managers and cybersecurity consultants.",
     [(6, 15, 19), (12, 14, 18)]),
]

def url(sku, anchor=""):
    q = urlencode({"utm_source": "linkwith", "utm_medium": "referral",
                   "utm_campaign": "pecb-academy", "utm_content": sku.lower()})
    return f"{BASE}?{q}{anchor}"

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def parent_desc(name, ipt, apt, ien, aen, eds):
    if eds:
        pt_ed = "".join(f"<li>{d_pt}</li>" for d_pt, _ in eds)
        en_ed = "".join(f"<li>{d_en}</li>" for _, d_en in eds)
    else:
        pt_ed = "<li>Próximas edições a anunciar — peça informação ou uma sessão corporativa.</li>"
        en_ed = "<li>Next sessions to be announced — request information or a private corporate session.</li>"
    return (
        f"<h3>{esc(name)}</h3>"
        f"<p>{esc(ipt)}</p>"
        f"<p><strong>Para quem:</strong> {esc(apt)}</p>"
        "<ul>"
        "<li><strong>Duração:</strong> 5 dias</li>"
        "<li><strong>Formato:</strong> online em direto (Microsoft Teams), presencial em Lisboa e no Porto, ou sessão corporativa privada</li>"
        "<li><strong>Língua:</strong> português ou inglês</li>"
        "<li><strong>Certificação:</strong> inclui preparação e exame oficial PECB; após aprovação, pode candidatar-se à credencial PECB correspondente, consoante a experiência profissional</li>"
        "</ul>"
        f"<p><strong>Próximas edições:</strong></p><ul>{pt_ed}</ul>"
        "<p><em>Formação ministrada pela CISODPO, parceiro oficial PECB. A inscrição é concluída no site da CISODPO.</em></p>"
        "<hr />"
        f"<h3>{esc(name)} (EN)</h3>"
        f"<p>{esc(ien)}</p>"
        f"<p><strong>Who it is for:</strong> {esc(aen)}</p>"
        "<ul>"
        "<li><strong>Duration:</strong> 5 days</li>"
        "<li><strong>Format:</strong> live online (Microsoft Teams), classroom in Lisbon and Porto, or private corporate session</li>"
        "<li><strong>Language:</strong> Portuguese or English</li>"
        "<li><strong>Certification:</strong> includes preparation and the official PECB exam; once you pass, you can apply for the corresponding PECB credential, subject to professional experience</li>"
        "</ul>"
        f"<p><strong>Upcoming sessions:</strong></p><ul>{en_ed}</ul>"
        "<p><em>Delivered by CISODPO, an official PECB partner. Enrolment is completed on the CISODPO website.</em></p>"
    )

HEAD = ["Type", "SKU", "Name", "Published", "Is featured?", "Visibility in catalog",
        "Short description", "Description", "In stock?", "Categories", "Tags",
        "Grouped products", "External URL", "Button text", "Position"]
NATTR = 8
for i in range(1, NATTR + 1):
    HEAD += [f"Attribute {i} name", f"Attribute {i} value(s)", f"Attribute {i} visible", f"Attribute {i} global"]

def attrs(lst):
    out = []
    for n, v, glob in lst:
        out += [n, v, "1", "1" if glob else "0"]
    out += [""] * (4 * (NATTR - len(lst)))
    return out

FORMATS_ALL = "Online em direto (Microsoft Teams), Presencial (Lisboa), Presencial (Porto), Sessão corporativa privada"
children, parents = [], []
for pos, (code, name, norma, nivel, area, tags, ipt, apt, ien, aen, ed2026) in enumerate(COURSES):
    psku = f"LW-PECB-{code}"
    cat = f"{CAT_ROOT} > {area}"
    common = [("Organismo certificador", "PECB", True), ("Norma / Regulamento", norma, True),
              ("Nível", nivel, True), ("Duração", "5 dias", False)]
    kids, eds_txt = [], []
    for m, d1, d2 in ed2026:
        start, end = datetime.date(2026, m, d1), datetime.date(2026, m, d2)
        if start <= TODAY:
            continue
        sku = f"{psku}-{start.isoformat()}"
        d_pt = f"{d1}–{d2} {MESES[m-1]} 2026 · online (Microsoft Teams)"
        d_en = f"{MONTHS[m-1]} {d1}–{d2}, 2026 · live online (Microsoft Teams)"
        eds_txt.append((d_pt, d_en))
        kids.append(sku)
        children.append(["external", sku, f"{name} — {d_pt}", "-1", "0", "hidden",
            f"<p>Edição de {d_pt}. Inscrição no site da CISODPO.</p><p><em>Session {d_en}. Enrol on the CISODPO website.</em></p>",
            "", "1", cat, ", ".join(["PECB"] + tags), "", url(sku), "Inscrever na CISODPO / Enrol", str(len(kids)),
            *attrs(common + [("Formato", "Online em direto (Microsoft Teams)", True),
                             ("Língua", "Português, English", True),
                             ("Data de início", start.isoformat(), False),
                             ("Data de fim", end.isoformat(), False)])])
    csku = f"{psku}-CONSULTA"
    kids.append(csku)
    children.append(["external", csku, f"{name} — Próximas edições e sessões corporativas (sob consulta)", "-1", "0", "hidden",
        "<p>Novas datas, formato presencial (Lisboa/Porto) ou sessão corporativa privada para a sua organização.</p>"
        "<p><em>New dates, classroom format (Lisbon/Porto) or a private corporate session for your organisation.</em></p>",
        "", "1", cat, ", ".join(["PECB"] + tags), "", url(csku, "#contact"),
        "Pedir informação / Enquire", str(len(kids)),
        *attrs(common + [("Formato", FORMATS_ALL, True), ("Língua", "Português, English", True)])])
    short = (f"<p>Formação certificada PECB de 5 dias, com exame oficial incluído. Online, presencial ou corporativa.</p>"
             f"<p><em>5-day PECB certified course, official exam included. Online, classroom or corporate.</em></p>")
    parents.append(["grouped", psku, f"PECB {name}", "-1", "1" if code.startswith("42001") else "0", "visible",
        short, parent_desc(name, ipt, apt, ien, aen, eds_txt), "1", cat, ", ".join(["PECB"] + tags),
        ", ".join(kids), "", "", str(pos + 1),
        *attrs(common + [("Formato", FORMATS_ALL, True), ("Língua", "Português, English", True),
                         ("Exame", "Exame oficial PECB incluído", False),
                         ("Formador", "CISODPO — parceiro oficial PECB", False)])])

with open(sys.argv[1], "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    w.writerow(HEAD)
    w.writerows(children)   # filhos primeiro: os agrupados referenciam SKUs já existentes
    w.writerows(parents)
print(len(children), "filhos;", len(parents), "cursos")
