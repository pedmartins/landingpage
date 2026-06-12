# app.py
import os
import html as html_lib
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template, request, abort, jsonify

app = Flask(__name__)

# URL base do WordPress — define a variável de ambiente WP_API_URL
# Exemplo: https://o-teu-site.railway.app
WP_API_URL = os.environ.get("WP_API_URL", "").rstrip("/")

# Zoho Bookings — URL do iframe da Booking Page (Embed/Share)
# Exemplo: https://NOME.zohobookings.eu/portal-embed#/SERVICO
ZOHO_BOOKINGS_URL = os.environ.get("ZOHO_BOOKINGS_URL", "")

# Cloudflare Workers AI
CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "")
CF_API_TOKEN  = os.environ.get("CF_API_TOKEN", "")

CF_MODELS = [
    {"id": "@cf/meta/llama-3.2-3b-instruct",          "label": "Llama 3.2 · 3B"},
    {"id": "@cf/meta/llama-3.1-8b-instruct-fp8-fast", "label": "Llama 3.1 · 8B"},
    {"id": "@cf/mistral/mistral-7b-instruct-v0.1",    "label": "Mistral · 7B"},
    {"id": "@cf/meta/llama-3.1-8b-instruct-fp8-fast",  "label": "Llama 3.1 · 8B · v2"},
]

HBR_SCENARIOS = [
    {
        "id": "differentiation",
        "tension": "Differentiation vs. Cost Leadership",
        "option_a": "Differentiation — invest in innovation, build unique features, justify a premium price.",
        "option_b": "Cost Leadership — standardise the product, reduce costs, compete on price.",
        "context": "A mid-sized B2B software company in a competitive market is reviewing its strategic direction. Its margins are under pressure from lower-cost competitors, but its clients consistently rate product quality highly.",
    },
    {
        "id": "automation",
        "tension": "Automation vs. Human Augmentation",
        "option_a": "Full Automation — replace manual workflows with AI-driven processes to maximise efficiency.",
        "option_b": "Human Augmentation — use AI to assist and amplify human decision-making, keeping people central.",
        "context": "A financial services firm is deploying AI across its operations. Regulators require explainability and accountability for all client-facing decisions.",
    },
    {
        "id": "horizon",
        "tension": "Short-term vs. Long-term",
        "option_a": "Short-term focus — optimise for this year's profitability, reduce R&D spend, return cash to shareholders.",
        "option_b": "Long-term investment — prioritise capability building, accept lower near-term margins to secure future positioning.",
        "context": "A listed industrial company faces pressure from activist shareholders demanding higher returns, while management believes the sector is on the verge of a technology shift.",
    },
    {
        "id": "innovation",
        "tension": "Radical vs. Incremental Innovation",
        "option_a": "Radical innovation — invest in a discontinuous new product that could cannibalise the existing business.",
        "option_b": "Incremental innovation — continuously improve the current product line to defend market share.",
        "context": "A consumer electronics manufacturer with strong brand equity is watching a new technology category emerge that its current product line does not address.",
    },
    {
        "id": "structure",
        "tension": "Centralisation vs. Decentralisation",
        "option_a": "Centralisation — consolidate decision-making at headquarters to ensure consistency and control.",
        "option_b": "Decentralisation — push authority to regional or business unit leaders to improve speed and local relevance.",
        "context": "A multinational retailer operating in 18 countries is designing its governance model following a major acquisition that added significant regional diversity.",
    },
    {
        "id": "competition",
        "tension": "Competition vs. Collaboration",
        "option_a": "Compete aggressively — invest in capturing market share from rivals through pricing and product superiority.",
        "option_b": "Collaborate via ecosystem — form alliances, share platforms, and co-create standards with competitors.",
        "context": "A telecom operator is evaluating its position in a market where infrastructure costs are rising and new entrants are fragmenting consumer attention.",
    },
    {
        "id": "exploration",
        "tension": "Exploration vs. Exploitation",
        "option_a": "Exploration — allocate resources to discover new markets, technologies, and business models.",
        "option_b": "Exploitation — concentrate resources on deepening current capabilities and extracting value from existing assets.",
        "context": "A professional services firm with a dominant position in its core practice is generating strong cash flows but sees its addressable market maturing.",
    },
]


import re

def parse_choice(text):
    """Extrai a opção recomendada (A/B) a partir do texto do modelo.
    Procura primeiro a frase de recomendação explícita ('I recommend Option X'),
    com fallback para a primeira opção mencionada. Devolve 'A', 'B' ou None.
    """
    if not text:
        return None
    t = text.lower()
    # Formato obrigatório no system prompt: "I recommend Option X"
    m = re.search(r"\bi recommend\b[^.]*?option\s+([ab])", t)
    if m:
        return m.group(1).upper()
    # Fallback: qualquer frase de recomendação não-negada
    m = re.search(r"(?<!not )recommend\w*\b[^.]*?option\s+([ab])", t)
    if m:
        return m.group(1).upper()
    ia, ib = t.find("option a"), t.find("option b")
    if ia != -1 and (ib == -1 or ia < ib):
        return "A"
    if ib != -1:
        return "B"
    return None


def call_cf_model(model_id, prompt):
    """Chama um modelo Cloudflare Workers AI e devolve o texto gerado."""
    if not CF_ACCOUNT_ID or not CF_API_TOKEN:
        return {"error": "CF credentials not configured"}
    try:
        r = requests.post(
            f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{model_id}",
            headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
            json={"messages": [
                {"role": "system", "content": (
                    "You are a strategic adviser. Given a business context and two strategic options, "
                    "you must recommend exactly one option. Start your response with 'I recommend Option A' "
                    "or 'I recommend Option B', then explain your reasoning in 3-4 sentences. Be direct and concise."
                )},
                {"role": "user", "content": prompt},
            ]},
            timeout=30,
        )
        data = r.json()
        if not data.get("success", True):
            errors = data.get("errors") or []
            msg = errors[0].get("message", "API error") if errors else f"HTTP {r.status_code}"
            return {"text": "", "error": msg}
        result = data.get("result") or {}
        text = result.get("response", "")
        return {"text": text, "choice": parse_choice(text), "error": None}
    except Exception as e:
        return {"text": "", "error": str(e)}

# URL base do bucket R2 (Cloudflare) para servir imagens
# Exemplo: https://pub-XXXX.r2.dev  ou  https://media.example.com
R2_BASE_URL = os.environ.get("R2_BASE_URL", "").rstrip("/")

# Thumbnails alternativos para cards — sobrepõem a featured image do WordPress
# Formato: slug → path relativo no R2 (sem o R2_BASE_URL)
CARD_THUMBNAILS = {
    "confirmation-bias-llm":    "/2026/06/f2eer10W-Confirmation-Bias.png",
    "confirmation-bias-llm-en": "/2026/06/f2eer10W-Confirmation-Bias.png",
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


def get_taxonomy_id(endpoint, slug):
    """Devolve o ID numérico de uma categoria ou tag pelo slug, ou None."""
    if not WP_API_URL:
        return None
    try:
        r = requests.get(
            f"{WP_API_URL}/wp-json/wp/v2/{endpoint}",
            params={"slug": slug, "per_page": 1},
            timeout=4,
        )
        data = r.json()
        return data[0]["id"] if data else None
    except Exception:
        return None


def get_category_id(slug):
    return get_taxonomy_id("categories", slug)


def get_tag_id(slug):
    return get_taxonomy_id("tags", slug)


_wp_author_cache = None

def get_wp_author(user_id=1):
    """Obtém dados do autor principal via WP REST API, com cache em memória."""
    global _wp_author_cache
    if _wp_author_cache is not None:
        return _wp_author_cache
    if not WP_API_URL:
        return {}
    try:
        r = requests.get(
            f"{WP_API_URL}/wp-json/wp/v2/users/{user_id}",
            timeout=4,
        )
        if r.status_code == 200:
            a = r.json()
            full_name = html_lib.unescape(a.get("name", ""))
            initials  = "".join(w[0] for w in full_name.split()[:2]).upper() or "PM"
            _wp_author_cache = {
                "name":        full_name,
                "initials":    initials,
                "url":         a.get("url", ""),
                "description": html_lib.unescape(a.get("description", "")),
            }
            return _wp_author_cache
    except Exception:
        pass
    return {}


@app.context_processor
def inject_author():
    """Disponibiliza {{ wp_author }} em todos os templates."""
    return {"wp_author": get_wp_author()}


def get_wp_posts(per_page=12, category_slug=None, tag_slug=None):
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
        if tag_slug:
            tag_id = get_tag_id(tag_slug)
            if tag_id:
                params["tags"] = tag_id

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

            # Construir URL Flask em vez de usar o link do WordPress
            post_slug = p["slug"]
            if post_slug.endswith("-en"):
                flask_link = f"/article/{post_slug[:-3]}?lang=en"
            else:
                flask_link = f"/article/{post_slug}"

            result.append({
                "id":           p["id"],
                "title":        html_lib.unescape(p["title"]["rendered"]),
                "excerpt":      html_lib.unescape(excerpt),
                "date":         p["date"][:10],          # YYYY-MM-DD
                "link":         flask_link,
                "featured_img": featured_img,
                "slug":         post_slug,
            })
        return result
    except Exception:
        return []


@app.route("/")
def home():
    posts = get_wp_posts(per_page=3, category_slug="ai-gov", tag_slug="lang-pt")
    return render_template("index.html", posts=posts)


@app.route("/en")
def home_en():
    posts = get_wp_posts(per_page=3, category_slug="ai-gov", tag_slug="lang-en")
    return render_template("index_en.html", posts=posts)


@app.route("/framework")
def framework():
    return render_template("conhecer_framework.html")


@app.route("/en/framework")
def framework_en():
    return render_template("conhecer_framework_en.html")


@app.route("/publicacoes")
def publicacoes():
    cat = 'ai-gov'
    posts = get_wp_posts(category_slug=cat, tag_slug="lang-pt")
    wp_configured = bool(WP_API_URL)
    return render_template("publicacoes.html", posts=posts, wp_configured=wp_configured, active_category=cat)


@app.route("/publicacoes/<category_slug>")
def publicacoes_categoria(category_slug):
    cat = 'ai-gov'
    posts = get_wp_posts(category_slug=cat, tag_slug="lang-pt")
    wp_configured = bool(WP_API_URL)
    return render_template("publicacoes.html", posts=posts, wp_configured=wp_configured, active_category=category_slug)


@app.route("/en/publicacoes")
def publicacoes_en():
    cat = 'ai-gov'
    posts = get_wp_posts(category_slug=cat, tag_slug="lang-en")
    wp_configured = bool(WP_API_URL)
    return render_template("publicacoes_en.html", posts=posts, wp_configured=wp_configured, active_category=cat)


@app.route("/en/publicacoes/<category_slug>")
def publicacoes_en_categoria(category_slug):
    cat = 'ai-gov'
    posts = get_wp_posts(category_slug=cat, tag_slug="lang-en")
    wp_configured = bool(WP_API_URL)
    return render_template("publicacoes_en.html", posts=posts, wp_configured=wp_configured, active_category=category_slug)


def get_wp_post_by_slug(wp_slug):
    """Obtém um artigo do WordPress pelo slug via REST API."""
    if not WP_API_URL:
        return None
    try:
        resp = requests.get(
            f"{WP_API_URL}/wp-json/wp/v2/posts",
            params={"slug": wp_slug, "status": "publish", "_embed": "wp:featuredmedia,wp:term,author"},
            timeout=6,
        )
        resp.raise_for_status()
        posts = resp.json()
        if not posts:
            return None
        p = posts[0]

        # Imagem em destaque
        featured_img = None
        try:
            featured_img = p["_embedded"]["wp:featuredmedia"][0]["source_url"]
        except (KeyError, IndexError, TypeError):
            pass
        featured_img = transform_image_url(featured_img)

        # Tags — excluir tags de idioma (lang-pt / lang-en)
        tags = []
        try:
            for term_group in p["_embedded"].get("wp:term", []):
                for term in term_group:
                    if term.get("taxonomy") == "post_tag":
                        name = term["name"]
                        if not name.startswith("lang-"):
                            tags.append(name)
        except (KeyError, TypeError):
            pass

        # Excerto
        excerpt_raw = p.get("excerpt", {}).get("rendered", "")
        excerpt = (
            excerpt_raw
            .replace("<p>", "").replace("</p>", "")
            .replace("\n", " ")
            .strip()
        )
        if excerpt.endswith("[&hellip;]"):
            excerpt = excerpt[:-10].rstrip() + "…"

        # Autor
        author = {}
        try:
            a = p["_embedded"]["author"][0]
            author = {
                "name": a.get("name", ""),
                "url":  a.get("url", ""),   # campo "Website" do perfil WP → LinkedIn
                "description": a.get("description", ""),
            }
        except (KeyError, IndexError, TypeError):
            pass

        return {
            "title":     html_lib.unescape(p["title"]["rendered"]),
            "slug":      p["slug"],
            "date":      p["date"][:10],
            "excerpt":   html_lib.unescape(excerpt),
            "content":   p["content"]["rendered"],
            "tags":      tags,
            "image_url": featured_img,
            "author":    author,
        }
    except Exception:
        return None


@app.route("/article/<slug>")
def article(slug):
    lang = request.args.get("lang", "pt")
    if lang not in ("pt", "en"):
        lang = "pt"

    # Tenta slug com sufixo de idioma, com fallback para o slug base
    if lang == "en":
        art = get_wp_post_by_slug(f"{slug}-en") or get_wp_post_by_slug(slug)
    else:
        art = get_wp_post_by_slug(slug) or get_wp_post_by_slug(f"{slug}-en")

    if art is None:
        abort(404)

    # Normalizar slug para o language switcher (slug base sem -en)
    art["slug"] = slug

    return render_template("article.html", article=art, lang=lang)


@app.route("/book")
def book():
    return render_template("book.html", zoho_url=ZOHO_BOOKINGS_URL)


@app.route("/en/book")
def book_en():
    return render_template("book_en.html", zoho_url=ZOHO_BOOKINGS_URL)


@app.route("/lab")
def lab():
    return render_template("lab.html", scenarios=HBR_SCENARIOS, models=CF_MODELS)


@app.route("/lab/api", methods=["POST"])
def lab_api():
    """Chama os modelos em paralelo e devolve as respostas."""
    data = request.get_json(force=True)
    scenario_id = data.get("scenario_id")
    scenario = next((s for s in HBR_SCENARIOS if s["id"] == scenario_id), None)
    if not scenario:
        return jsonify({"error": "Scenario not found"}), 400

    prompt = (
        f"Business context: {scenario['context']}\n\n"
        f"The leadership team is deciding between two strategic options:\n"
        f"Option A: {scenario['option_a']}\n"
        f"Option B: {scenario['option_b']}\n\n"
        f"Which option do you recommend?"
    )

    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(call_cf_model, m["id"], prompt): m
            for m in CF_MODELS
        }
        for future in as_completed(futures):
            model = futures[future]
            results[model["id"]] = {
                "label": model["label"],
                **future.result(),
            }

    return jsonify({"scenario": scenario, "results": results})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
