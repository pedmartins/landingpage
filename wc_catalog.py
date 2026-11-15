"""Cliente server-side do catálogo PECB em WooCommerce.

Contrato: api/openapi.pt.yaml e api/openapi.en.yaml do projeto
woocommerce-pecb. O host reutiliza WP_API_URL (ou WC_URL como override) e as
credenciais WC_CK/WC_CS são lidas exclusivamente no servidor.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import threading
import time

import requests


log = logging.getLogger(__name__)

# O catálogo e as publicações vivem no mesmo WordPress. WC_URL só é
# necessário quando o WooCommerce estiver noutro host; por omissão reutiliza
# o WP_API_URL já configurado para as publicações.
WC_URL = (os.environ.get("WC_URL") or os.environ.get("WP_API_URL", "")).rstrip("/")
WC_CK = os.environ.get("WC_CK", "")
WC_CS = os.environ.get("WC_CS", "")
SKU_PREFIX = os.environ.get("WC_SKU_PREFIX", "LW-PECB-")
CACHE_TTL = int(os.environ.get("WC_CACHE_TTL", "900"))
TIMEOUT = 10
# O WordPress no Railway pode estar a arrancar (ou a acordar) e responder 502/503/504:
# repetimos o pedido algumas vezes antes de desistir.
RETRY_STATUS = {502, 503, 504}
RETRY_DELAYS = (2, 5)  # segundos entre tentativas (3 tentativas no total)
# Depois de uma falha sem dados em cache, não voltamos a tentar em cada visita.
FAIL_COOLDOWN = int(os.environ.get("WC_FAIL_COOLDOWN", "60"))

_FIELDS = (
    "id,name,slug,type,status,sku,menu_order,catalog_visibility,"
    "short_description,description,external_url,button_text,images,"
    "categories,tags,attributes,grouped_products,meta_data,date_modified_gmt"
)


def _get_with_retry(session: requests.Session, url: str, params: dict) -> requests.Response:
    """GET com novas tentativas para erros transitórios (WordPress a arrancar)."""
    for attempt, delay in enumerate((*RETRY_DELAYS, None), start=1):
        try:
            response = session.get(url, params=params, timeout=TIMEOUT)
            if response.status_code not in RETRY_STATUS or delay is None:
                return response
            log.warning("WooCommerce respondeu %s (tentativa %s); nova tentativa em %ss",
                        response.status_code, attempt, delay)
        except (requests.ConnectionError, requests.Timeout):
            if delay is None:
                raise
            log.warning("WooCommerce sem resposta (tentativa %s); nova tentativa em %ss", attempt, delay)
        time.sleep(delay)
    raise RuntimeError("inalcançável")


def _get_all(path: str, params: dict) -> list[dict]:
    """Consulta paginada à API REST v3, sempre limitada a publicados."""
    if not (WC_URL and WC_CK and WC_CS):
        raise RuntimeError("WP_API_URL (ou WC_URL), WC_CK e WC_CS têm de estar definidos")

    requested = dict(params)
    requested["status"] = "publish"
    products: list[dict] = []
    page = 1

    with requests.Session() as session:
        session.auth = (WC_CK, WC_CS)
        while True:
            response = _get_with_retry(
                session,
                f"{WC_URL}/wp-json/wc/v3/{path}",
                {
                    **requested,
                    "per_page": 100,
                    "page": page,
                    "_fields": _FIELDS,
                },
            )
            response.raise_for_status()
            products.extend(response.json())
            if page >= int(response.headers.get("X-WP-TotalPages", 1)):
                return products
            page += 1


def _fetch_raw() -> tuple[list[dict], list[dict]]:
    parents = [
        product
        for product in _get_all(
            "products",
            {
                "type": "grouped",
                "orderby": "menu_order",
                "order": "asc",
            },
        )
        if (product.get("sku") or "").startswith(SKU_PREFIX)
        and not (product.get("sku") or "").endswith("-CONSULTA")
    ]

    child_ids = sorted(
        {
            child_id
            for product in parents
            for child_id in product.get("grouped_products", [])
        }
    )
    children: list[dict] = []
    for offset in range(0, len(child_ids), 100):
        children.extend(
            _get_all(
                "products",
                {"include": ",".join(map(str, child_ids[offset : offset + 100]))},
            )
        )
    return parents, children


def _attributes(product: dict) -> dict[str, list[str]]:
    return {
        attribute["name"]: attribute.get("options", [])
        for attribute in product.get("attributes", [])
        if attribute.get("visible", True)
    }


def _meta(product: dict, key: str) -> str:
    for item in product.get("meta_data", []):
        if item.get("key") == key:
            return str(item.get("value") or "")
    return ""


def _iso_date(values: list[str]) -> str | None:
    try:
        return dt.date.fromisoformat(values[0]).isoformat()
    except (IndexError, TypeError, ValueError):
        return None


def normalize(
    parents: list[dict], children: list[dict], today: dt.date | None = None
) -> list[dict]:
    """Normaliza cursos e remove rascunhos e sessões anteriores a hoje."""
    today = today or dt.date.today()
    published_children = {
        child["id"]: child for child in children if child.get("status") == "publish"
    }
    courses: list[dict] = []

    for parent in sorted(
        parents, key=lambda item: (item.get("menu_order", 0), item.get("name", ""))
    ):
        if parent.get("status") != "publish":
            continue

        editions: list[dict] = []
        enquiry = None
        for child_id in parent.get("grouped_products", []):
            child = published_children.get(child_id)
            if not child:
                continue

            attrs = _attributes(child)
            edition = {
                "id": child["id"],
                "name": child.get("name", ""),
                "url": child.get("external_url") or "",
                "button_text": child.get("button_text") or "Inscrever",
                "start": _iso_date(attrs.get("Data de início", [])),
                "end": _iso_date(attrs.get("Data de fim", [])),
                "format": attrs.get("Formato", []),
            }
            if (child.get("sku") or "").endswith("-CONSULTA"):
                enquiry = edition
            elif edition["start"] and edition["start"] >= today.isoformat():
                editions.append(edition)

        attrs = _attributes(parent)
        enrol_url = _meta(parent, "lw_enrol_url") or (enquiry or {}).get("url") or ""

        # Datas no próprio curso (uma sessão por curso, sem produto de edição).
        own_start = _iso_date(attrs.get("Data de início", []))
        if own_start and own_start >= today.isoformat() and not any(
            item["start"] == own_start for item in editions
        ):
            editions.append({
                "id": parent["id"],
                "name": parent.get("name", ""),
                "url": enrol_url,
                "button_text": _meta(parent, "lw_button_text") or "Inscrever",
                "start": own_start,
                "end": _iso_date(attrs.get("Data de fim", [])),
                "format": attrs.get("Formato", [])[:1],
            })

        courses.append(
            {
                "id": parent["id"],
                "slug": parent["slug"],
                "sku": parent.get("sku") or "",
                "name": parent.get("name", ""),
                "short_description": parent.get("short_description", ""),
                "categories": [
                    category["name"] for category in parent.get("categories", [])
                ],
                "standard": (attrs.get("Norma / Regulamento") or [None])[0],
                "level": (attrs.get("Nível") or [None])[0],
                "duration": (attrs.get("Duração") or [None])[0],
                "language": (attrs.get("Língua") or [None])[0],
                "editions": sorted(editions, key=lambda item: item["start"]),
                "enquiry": enquiry,
                "enrol_url": enrol_url,
            }
        )
    return courses


_cache_lock = threading.Lock()
_cache: dict = {"at": 0.0, "data": None, "failed_at": 0.0}


def is_configured() -> bool:
    return bool(WC_URL and WC_CK and WC_CS)


def get_catalog(force: bool = False) -> list[dict]:
    """Catálogo em cache; numa falha serve a última resposta válida."""
    with _cache_lock:
        fresh = (
            _cache["data"] is not None
            and time.time() - _cache["at"] < CACHE_TTL
        )
        if fresh and not force:
            return _cache["data"]
        cooling = time.time() - _cache["failed_at"] < FAIL_COOLDOWN
        if cooling and not force:
            if _cache["data"] is None:
                raise RuntimeError("Catálogo indisponível (a aguardar nova tentativa)")
            return _cache["data"]

        try:
            _cache["data"] = normalize(*_fetch_raw())
            _cache["at"] = time.time()
            _cache["failed_at"] = 0.0
        except Exception:
            _cache["failed_at"] = time.time()
            log.exception("Falha a ler o catálogo de formação no WooCommerce")
            if _cache["data"] is None:
                raise
        return _cache["data"]
