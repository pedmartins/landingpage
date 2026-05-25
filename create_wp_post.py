"""
Cria ou atualiza um artigo no WordPress a partir de um ficheiro JSON.

Uso:
    python3 create_wp_post.py artigos/grounding-mechanics-ai-organisations.json

    # Forçar update de post existente pelo ID:
    python3 create_wp_post.py artigos/grounding-mechanics-ai-organisations.json --id 3030

Estrutura do JSON:
    {
      "title":      "Título do artigo",
      "slug":       "slug-do-artigo",
      "status":     "draft" | "publish",
      "excerpt":    "Resumo curto.",
      "tags":       ["tag1", "tag2"],
      "image_path": "artigos/cover.jpg" | null,
      "wp_post_id": 3030,              ← preenchido automaticamente após criação
      "content":    "<p>HTML...</p>"
    }

Após publicar, apaga este ficheiro (contém credenciais).
"""

import sys
import json
import os
import mimetypes
import requests
from requests.auth import HTTPBasicAuth

# ── Credenciais ───────────────────────────────────────────────────────────────
WP_URL  = "https://wordpress-railway-production-2939.up.railway.app"
WP_USER = "cGFjMi5ldQo"
WP_PASS = "GyHH RfW7 BWhl 4Mh7 V5TQ Iehe"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# ─────────────────────────────────────────────────────────────────────────────


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_auth(auth):
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/users/me", auth=auth, timeout=10)
    if r.status_code != 200:
        print(f"✗ Erro de autenticação ({r.status_code}): {r.text[:200]}")
        sys.exit(1)
    print(f"✓ Autenticado como: {r.json().get('name')}")


def get_or_create_tags(tag_names, auth):
    """Devolve lista de IDs de tags, criando as que não existem."""
    ids = []
    for name in tag_names:
        # Verificar se existe
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/tags",
            params={"search": name},
            auth=auth, timeout=10
        )
        existing = [t for t in r.json() if t["name"].lower() == name.lower()]
        if existing:
            ids.append(existing[0]["id"])
        else:
            rc = requests.post(
                f"{WP_URL}/wp-json/wp/v2/tags",
                json={"name": name},
                auth=auth, timeout=10
            )
            if rc.status_code in (200, 201):
                ids.append(rc.json()["id"])
    return ids


def upload_image(image_path, auth):
    """Faz upload da imagem e devolve o media ID."""
    abs_path = os.path.join(BASE_DIR, image_path) if not os.path.isabs(image_path) else image_path
    if not os.path.exists(abs_path):
        print(f"  ⚠ Imagem não encontrada: {abs_path}")
        return None

    mime, _ = mimetypes.guess_type(abs_path)
    filename = os.path.basename(abs_path)

    with open(abs_path, "rb") as f:
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": mime or "application/octet-stream",
            },
            data=f,
            auth=auth,
            timeout=30,
        )
    if r.status_code in (200, 201):
        media_id = r.json()["id"]
        print(f"  ✓ Imagem publicada (ID: {media_id})")
        return media_id
    else:
        print(f"  ⚠ Falha no upload da imagem ({r.status_code}): {r.text[:200]}")
        return None


def find_post_by_slug(slug, auth):
    """Procura post existente pelo slug. Devolve ID ou None."""
    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/posts",
        params={"slug": slug, "status": "any"},
        auth=auth, timeout=10
    )
    results = r.json()
    if isinstance(results, list) and results:
        return results[0]["id"]
    return None


def save_post_id(json_path, post_id):
    """Guarda o wp_post_id no JSON para reutilização futura."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["wp_post_id"] = post_id
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ wp_post_id {post_id} guardado no JSON")


def create_or_update_post(data, auth, json_path, force_id=None):
    tag_ids = []
    if data.get("tags"):
        print("  → A criar/verificar tags…")
        tag_ids = get_or_create_tags(data["tags"], auth)

    media_id = None
    if data.get("image_path"):
        print("  → A fazer upload da imagem…")
        media_id = upload_image(data["image_path"], auth)

    payload = {
        "title":   data["title"],
        "content": data["content"],
        "status":  data.get("status", "draft"),
        "slug":    data.get("slug", ""),
        "excerpt": data.get("excerpt", ""),
    }
    if tag_ids:
        payload["tags"] = tag_ids
    if media_id:
        payload["featured_media"] = media_id

    # Determinar se é criação ou update
    post_id = force_id or data.get("wp_post_id")
    if not post_id and data.get("slug"):
        print("  → A verificar se post já existe pelo slug…")
        post_id = find_post_by_slug(data["slug"], auth)
        if post_id:
            print(f"  → Post encontrado (ID: {post_id}) — a fazer update")

    if post_id:
        # UPDATE
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
            json=payload,
            auth=auth,
            timeout=20,
        )
        action = "atualizado"
    else:
        # CREATE
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            json=payload,
            auth=auth,
            timeout=20,
        )
        action = "criado"

    if r.status_code in (200, 201):
        post = r.json()
        print(f"\n✓ Post {action} em modo '{post['status']}'")
        print(f"  ID:    {post['id']}")
        print(f"  Link:  {post['link']}")
        print(f"\n  Editar: {WP_URL}/wp-admin/post.php?post={post['id']}&action=edit")
        # Guardar ID no JSON para updates futuros
        save_post_id(json_path, post["id"])
    else:
        print(f"\n✗ Erro {r.status_code}: {r.text[:400]}")


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 create_wp_post.py <ficheiro.json> [--id POST_ID]")
        print("Exemplo: python3 create_wp_post.py artigos/grounding-mechanics-ai-organisations.json")
        print("Update:  python3 create_wp_post.py artigos/grounding-mechanics-ai-organisations.json --id 3030")
        sys.exit(1)

    json_path = sys.argv[1]
    if not os.path.isabs(json_path):
        json_path = os.path.join(BASE_DIR, json_path)

    if not os.path.exists(json_path):
        print(f"✗ Ficheiro não encontrado: {json_path}")
        sys.exit(1)

    # Verificar flag --id
    force_id = None
    if "--id" in sys.argv:
        idx = sys.argv.index("--id")
        try:
            force_id = int(sys.argv[idx + 1])
            print(f"→ Modo update forçado (ID: {force_id})")
        except (IndexError, ValueError):
            print("✗ --id requer um número inteiro")
            sys.exit(1)

    print(f"→ A carregar: {json_path}")
    data = load_json(json_path)
    print(f"  Título: {data['title']}")

    auth = HTTPBasicAuth(WP_USER, WP_PASS)
    check_auth(auth)
    create_or_update_post(data, auth, json_path, force_id=force_id)


if __name__ == "__main__":
    main()
