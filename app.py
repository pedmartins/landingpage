# app.py
import os
import requests
from flask import Flask, render_template

app = Flask(__name__)

# URL base do WordPress — define a variável de ambiente WP_API_URL
# Exemplo: https://o-teu-site.railway.app
WP_API_URL = os.environ.get("WP_API_URL", "").rstrip("/")


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
    return render_template("index.html")


@app.route("/publicacoes")
def publicacoes():
    posts = get_wp_posts()
    wp_configured = bool(WP_API_URL)
    return render_template("publicacoes.html", posts=posts, wp_configured=wp_configured)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
