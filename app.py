# app.py
import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# URL base do WordPress — define a variável de ambiente WP_API_URL
# Exemplo: https://o-teu-site.railway.app
WP_API_URL = os.environ.get("WP_API_URL", "").rstrip("/")

# URL base do bucket R2 (Cloudflare) para servir imagens
# Exemplo: https://pub-XXXX.r2.dev  ou  https://media.example.com
R2_BASE_URL = os.environ.get("R2_BASE_URL", "").rstrip("/")

# Thumbnails alternativos para cards — sobrepõem a featured image do WordPress
# Formato: slug → path relativo no R2 (sem o R2_BASE_URL)
CARD_THUMBNAILS = {
    "confirmation-bias-llm": "/wp-content/uploads/2026/06/Confirmation-Bias.png",
}


def transform_image_url(url):
    """Substitui o domínio do WordPress pelo domínio do bucket R2,
    mantendo o path completo (o WP Offload Media replica a estrutura).
    Ex: https://wordpress.../wp-content/uploads/2026/05/grounding-cover.png
        → https://pub-XXX.r2.dev/wp-content/uploads/2026/05/grounding-cover.png
    """
    if not url or not R2_BASE_URL:
        return url
    if WP_API_URL and url.startswith(WP_API_URL):
        return R2_BASE_URL + url[len(WP_API_URL):]
    return url


def get_category_id(slug):
    """Devolve o ID numérico de uma categoria pelo slug, ou None se não encontrar."""
    if not WP_API_URL:
        return None
    try:
        r = requests.get(
            f"{WP_API_URL}/wp-json/wp/v2/categories",
            params={"slug": slug, "per_page": 1},
            timeout=4,
        )
        data = r.json()
        return data[0]["id"] if data else None
    except Exception:
        return None


def get_wp_posts(per_page=12, category_slug=None):
    """Obtém artigos publicados via WordPress REST API.
    Se category_slug for fornecido, filtra por essa categoria.
    """
    if not WP_API_URL:
        return []
    try:
        params = {
            "per_page": per_page,
            "status": "publish",
            "_embed": "wp:featuredmedia",
        }
        if category_slug:
            cat_id = get_category_id(category_slug)
            if cat_id:
                params["categories"] = cat_id

        resp = requests.get(
            f"{WP_API_URL}/wp-json/wp/v2/posts",
            params=params,
            timeout=6,
        )
        resp.raise_for_status()
        posts = resp.json()

        result = []
        for p in posts:
            # Imagem em destaque — tenta via _embed, fallback via media endpoint
            featured_img = None
            try:
                featured_img = (
                    p["_embedded"]["wp:featuredmedia"][0]["source_url"]
                )
            except (KeyError, IndexError, TypeError):
                pass

            # Fallback: se _embed não devolveu nada, consulta o media endpoint
            if not featured_img and p.get("featured_media"):
                try:
                    m = requests.get(
                        f"{WP_API_URL}/wp-json/wp/v2/media/{p['featured_media']}",
                        timeout=4,
                    )
                    if m.status_code == 200:
                        featured_img = m.json().get("source_url")
                except Exception:
                    pass

            # Aplicar transformação para URL do bucket R2
            featured_img = transform_image_url(featured_img)

            # Override do thumbnail para card se existir mapeamento local
            if p["slug"] in CARD_THUMBNAILS and R2_BASE_URL:
                featured_img = R2_BASE_URL + CARD_THUMBNAILS[p["slug"]]

            # Excerto — limpar tags HTML residuais
            excerpt_raw = p.get("excerpt", {}).get("rendered", "")
            excerpt = (
                excerpt_raw
                .replace("<p>", "").replace("</p>", "")
                .replace("\n", " ")
                .strip()
            )
            if excerpt.endswith("[&hellip;]"):
                excerpt = excerpt[:-10].rstrip() + "…"

            result.append({
                "id":           p["id"],
                "title":        p["title"]["rendered"],
                "excerpt":      excerpt,
                "date":         p["date"][:10],          # YYYY-MM-DD
                "link":         p["link"],
                "featured_img": featured_img,
                "slug":         p["slug"],
            })
        return result
    except Exception:
        return []


@app.route("/")
def home():
    posts = get_wp_posts(per_page=3, category_slug="ai-gov")
    return render_template("index.html", posts=posts)


@app.route("/en")
def home_en():
    posts = get_wp_posts(per_page=3, category_slug="ai-gov")
    return render_template("index_en.html", posts=posts)


@app.route("/framework")
def framework():
    return render_template("conhecer_framework.html")


@app.route("/en/framework")
def framework_en():
    return render_template("conhecer_framework_en.html")


@app.route("/publicacoes")
def publicacoes():
    # Suporta ?category=ai-gov na query string
    cat = 'ai-gov'
    posts = get_wp_posts(category_slug=cat)
    wp_configured = bool(WP_API_URL)
    return render_template("publicacoes.html", posts=posts, wp_configured=wp_configured, active_category=cat)


@app.route("/publicacoes/<category_slug>")
def publicacoes_categoria(category_slug):
    cat = 'ai-gov'
    posts = get_wp_posts(category_slug=cat)
    wp_configured = bool(WP_API_URL)
    return render_template("publicacoes.html", posts=posts, wp_configured=wp_configured, active_category=category_slug)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
