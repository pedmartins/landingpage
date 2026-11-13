"""Catálogo de formação (WooCommerce → Flask), só produtos publicados.

Lê a WooCommerce REST API v3 com uma chave só de leitura e devolve um
catálogo normalizado: um curso (produto agrupado) com as suas edições
(produtos externos filhos). Rascunhos, privados e pendentes nunca entram,
porque todos os pedidos levam status=publish.

Variáveis de ambiente (definir no serviço Flask no Railway, nunca no código):
    WC_URL          https://wordpress-railway-production-2939.up.railway.app
    WC_CK / WC_CS   consumer key / secret (permissão: Leitura)
    WC_SKU_PREFIX   LW-PECB-            (opcional)
    WC_CACHE_TTL    900                 (segundos, opcional)

Exportação para ficheiro (snapshot):
    python wc_catalog.py export catalogo.json
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import sys
import threading
import time

import requests

log = logging.getLogger(__name__)

WC_URL = os.environ.get("WC_URL", "").rstrip("/")
WC_CK = os.environ.get("WC_CK", "")
WC_CS = os.environ.get("WC_CS", "")
SKU_PREFIX = os.environ.get("WC_SKU_PREFIX", "LW-PECB-")
CACHE_TTL = int(os.environ.get("WC_CACHE_TTL", "900"))
TIMEOUT = 15

# Só estes campos vêm da API (respostas mais leves)
_FIELDS = ("id,name,slug,type,status,sku,menu_order,short_description,description,"
           "external_url,button_text,categories,tags,images,attributes,grouped_products")


# ---------------------------------------------------------------- HTTP
def _get_all(path: str, params: dict) -> list[dict]:
    """GET paginado à API v3 (100 por página, segue X-WP-TotalPages)."""
    if not (WC_URL and WC_CK and WC_CS):
        raise RuntimeError("WC_URL, WC_CK e WC_CS têm de estar definidos")
    out, page = [], 1
    with requests.Session() as s:
        s.auth = (WC_CK, WC_CS)  # Basic auth: exige HTTPS (o WP deteta-o via X-Forwarded-Proto)
        while True:
            r = s.get(f"{WC_URL}/wp-json/wc/v3/{path}", timeout=TIMEOUT,
                      params={**params, "per_page": 100, "page": page, "_fields": _FIELDS})
            r.raise_for_status()
            out.extend(r.json())
            if page >= int(r.headers.get("X-WP-TotalPages", 1)):
                return out
            page += 1


def _fetch_raw() -> tuple[list[dict], list[dict]]:
    parents = [p for p in _get_all("products", {"status": "publish", "type": "grouped"})
               if (p.get("sku") or "").startswith(SKU_PREFIX)]
    ids = sorted({cid for p in parents for cid in p.get("grouped_products", [])})
    children = []
    for i in range(0, len(ids), 100):  # include aceita até 100 ids por pedido
        children += _get_all("products", {"status": "publish",
                                          "include": ",".join(map(str, ids[i:i + 100]))})
    return parents, children


# ---------------------------------------------------------- normalização
def _attrs(p: dict) -> dict[str, list[str]]:
    return {a["name"]: a.get("options", []) for a in p.get("attributes", []) if a.get("visible", True)}


def _date(v: list[str]) -> str | None:
    try:
        return dt.date.fromisoformat(v[0]).isoformat()
    except (IndexError, ValueError):
        return None


def _image(p: dict) -> dict | None:
    img = (p.get("images") or [None])[0]
    return {"src": img["src"], "alt": img.get("alt") or p["name"]} if img else None


def normalize(parents: list[dict], children: list[dict], today: dt.date | None = None) -> list[dict]:
    today = today or dt.date.today()
    by_id = {c["id"]: c for c in children if c.get("status") == "publish"}
    courses = []
    for p in sorted(parents, key=lambda x: (x.get("menu_order", 0), x["name"])):
        if p.get("status") != "publish":  # defesa extra
            continue
        editions, enquiry = [], None
        for cid in p.get("grouped_products", []):
            c = by_id.get(cid)
            if not c:  # filho em rascunho ou apagado
                continue
            a = _attrs(c)
            item = {"id": c["id"], "name": c["name"], "url": c.get("external_url"),
                    "button_text": c.get("button_text") or "Inscrever",
                    "start": _date(a.get("Data de início", [])),
                    "end": _date(a.get("Data de fim", [])),
                    "format": a.get("Formato", [])}
            if (c.get("sku") or "").endswith("-CONSULTA"):
                enquiry = item
            elif item["start"] and item["start"] >= today.isoformat():
                editions.append(item)  # edições passadas ficam de fora
        a = _attrs(p)
        courses.append({
            "id": p["id"], "slug": p["slug"], "sku": p.get("sku"), "name": p["name"],
            "short_description": p.get("short_description", ""),
            "description": p.get("description", ""),
            "image": _image(p),
            "categories": [c["name"] for c in p.get("categories", [])],
            "tags": [t["name"] for t in p.get("tags", [])],
            "standard": (a.get("Norma / Regulamento") or [None])[0],
            "level": (a.get("Nível") or [None])[0],
            "attributes": a,
            "editions": sorted(editions, key=lambda e: e["start"]),
            "enquiry": enquiry,
        })
    return courses


# ------------------------------------------------------------- cache
_lock = threading.Lock()
_cache: dict = {"at": 0.0, "data": None}


def get_catalog(force: bool = False) -> list[dict]:
    """Catálogo em cache (TTL). Se o WordPress falhar, serve a última versão boa."""
    with _lock:
        fresh = _cache["data"] is not None and time.time() - _cache["at"] < CACHE_TTL
        if fresh and not force:
            return _cache["data"]
        try:
            _cache["data"] = normalize(*_fetch_raw())
            _cache["at"] = time.time()
        except Exception:
            log.exception("Falha a ler o catálogo WooCommerce")
            if _cache["data"] is None:
                raise
        return _cache["data"]


def get_course(slug: str) -> dict | None:
    return next((c for c in get_catalog() if c["slug"] == slug), None)


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "export":
    data = get_catalog(force=True)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump({"generated_at": dt.datetime.now().isoformat(timespec="seconds"),
                   "courses": data}, f, ensure_ascii=False, indent=2)
    print(f"{len(data)} cursos exportados para {sys.argv[2]}")
