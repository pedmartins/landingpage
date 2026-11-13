"""Rotas de formação para o Flask (ai-gov.network).

Registar na app:
    from formacao_bp import formacao_bp
    app.register_blueprint(formacao_bp)
"""
from flask import Blueprint, abort, jsonify, render_template
from markupsafe import Markup

from wc_catalog import get_catalog, get_course

try:  # o HTML vem do teu próprio WordPress, mas higienizar não custa nada
    import bleach
    _TAGS = {"p", "strong", "em", "ul", "ol", "li", "h3", "h4", "hr", "br", "a"}
    def clean(html: str) -> Markup:
        return Markup(bleach.clean(html or "", tags=_TAGS, attributes={"a": ["href", "title"]}, strip=True))
except ImportError:  # pragma: no cover
    def clean(html: str) -> Markup:
        return Markup(html or "")

formacao_bp = Blueprint("formacao", __name__, template_folder="templates")
formacao_bp.add_app_template_filter(clean, "clean_html")


@formacao_bp.get("/formacao")
def lista():
    return render_template("formacao/lista.html", cursos=get_catalog())


@formacao_bp.get("/formacao/<slug>")
def detalhe(slug: str):
    curso = get_course(slug)
    if not curso:
        abort(404)
    return render_template("formacao/detalhe.html", curso=curso)


@formacao_bp.get("/api/formacao.json")
def api():
    """JSON público só com o que já é público na página (útil para testes)."""
    return jsonify([{k: c[k] for k in ("slug", "name", "standard", "level", "image", "editions")}
                    for c in get_catalog()])
