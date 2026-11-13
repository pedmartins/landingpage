"""Exporta os produtos PUBLICADOS do WooCommerce para JSON.

Equivale à lista wp-admin/edit.php?post_status=publish&post_type=product,
reduzida aos campos de que o Flask precisa (a "interface" de cada produto).

Uso:
    export WC_URL=https://wordpress-railway-production-2939.up.railway.app
    export WC_CK=ck_...  WC_CS=cs_...        # chave REST com permissão Leitura
    python export_produtos.py produtos.json                 # todos os publicados
    python export_produtos.py produtos.json --prefix LW-PECB-   # só os da formação
"""
import argparse, datetime as dt, json, os, sys
import requests

FIELDS = ("id,name,slug,type,status,sku,menu_order,catalog_visibility,permalink,"
          "short_description,description,external_url,button_text,images,"
          "categories,tags,attributes,grouped_products,date_modified")


def fetch(url, ck, cs):
    out, page = [], 1
    with requests.Session() as s:
        s.auth = (ck, cs)
        while True:
            r = s.get(f"{url}/wp-json/wc/v3/products", timeout=20,
                      params={"status": "publish", "per_page": 100, "page": page, "_fields": FIELDS})
            r.raise_for_status()
            out += r.json()
            if page >= int(r.headers.get("X-WP-TotalPages", 1)):
                return out
            page += 1


def interface(p):
    img = (p.get("images") or [None])[0]
    return {
        "id": p["id"], "sku": p.get("sku") or None, "slug": p["slug"], "name": p["name"],
        "type": p["type"],                                  # grouped | external | simple | variable
        "visibility": p.get("catalog_visibility"),          # visible | hidden ...
        "order": p.get("menu_order", 0),
        "short_description": p.get("short_description", ""),
        "description": p.get("description", ""),
        "image": {"src": img["src"], "alt": img.get("alt") or p["name"]} if img else None,
        "categories": [c["name"] for c in p.get("categories", [])],
        "tags": [t["name"] for t in p.get("tags", [])],
        "attributes": {a["name"]: a.get("options", []) for a in p.get("attributes", [])},
        "external_url": p.get("external_url") or None,      # só produtos externos
        "button_text": p.get("button_text") or None,
        "children": p.get("grouped_products") or [],        # só produtos agrupados
        "modified": p.get("date_modified"),
    }


def build(products, prefix=None):
    items = [interface(p) for p in products if p.get("status") == "publish"
             and (not prefix or (p.get("sku") or "").startswith(prefix))]
    ids = {i["id"] for i in items}
    for i in items:  # filhos que não estão publicados ficam fora das referências
        i["children"] = [c for c in i["children"] if c in ids]
    return {"exported_at": dt.datetime.now().isoformat(timespec="seconds"),
            "count": len(items), "products": sorted(items, key=lambda i: (i["order"], i["name"]))}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--prefix", help="filtrar por início de SKU, ex.: LW-PECB-")
    a = ap.parse_args()
    url, ck, cs = (os.environ.get(k, "") for k in ("WC_URL", "WC_CK", "WC_CS"))
    if not (url and ck and cs):
        sys.exit("Define WC_URL, WC_CK e WC_CS")
    data = build(fetch(url.rstrip("/"), ck, cs), a.prefix)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"{data['count']} produtos publicados exportados para {a.out}")
