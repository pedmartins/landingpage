# app.py
import os
import requests
from flask import Flask, render_template

app = Flask(__name__)

# URL base do WordPress — define a variável de ambiente WP_API_URL
# Exemplo: https://o-teu-site.railway.app
WP_API_URL = os.environ.get("WP_API_URL", "").rstrip("/")

# URL base do bucket R2 (Cloudflare) para servir imagens
# Exemplo: https://pub-XXXX.r2.dev  ou  https://media.example.com
R2_BASE_URL = os.environ.get("R2_BASE_URL", "").rstrip("/")


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


def get_wp_posts(per_page=12):
    """Obtém artigos publicados via WordPress REST API."""
    if not WP_API_URL:
        return []
    try:
        resp = requests.get(
            f"{WP_API_URL}/wp-json/wp/v2/posts",
            params={
                "per_page": per_page,
                "status": "publish",
                "_embed": True,          # inclui imagem em destaque e autor
            },
            timeout=6,
        )
        resp.raise_for_status()
        posts = resp.json()

        result = []
        for p in posts:
            # Imagem em destaque
            featured_img = None
            try:
                featured_img = (
                    p["_embedded"]["wp:featuredmedia"][0]["source_url"]
                )
            except (KeyError, IndexError, TypeError):
                pass

            # Aplicar transformação para URL do bucket R2
            featured_img = transform_image_url(featured_img)

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
    posts = get_wp_posts(per_page=3)   # últimos 3 artigos para a homepage
    return render_template("index.html", posts=posts)


@app.route("/publicacoes")
def publicacoes():
    posts = get_wp_posts()
    wp_configured = bool(WP_API_URL)
    return render_template("publicacoes.html", posts=posts, wp_configured=wp_configured)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
