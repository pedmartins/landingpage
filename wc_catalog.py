"""Cliente server-side do catálogo PECB em WooCommerce.

Contrato: api/openapi.pt.yaml e api/openapi.en.yaml do projeto
woocommerce-pecb. O host reutiliza WP_API_URL (ou WC_URL como override) e as
credenciais WC_CK/WC_CS são lidas exclusivamente no servidor.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import threading
import time
import unicodedata

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


def _option_values(attribute: dict) -> list[str]:
    options = attribute.get("options")
    if options is None:
        options = [
            term.get("name")
            for term in attribute.get("terms") or []
            if isinstance(term, dict) and term.get("name")
        ]
    if isinstance(options, str):
        options = [options]
    return [str(item).strip() for item in options or [] if item is not None and str(item).strip()]


def _attributes(product: dict, *, visible_only: bool = True) -> dict[str, list[str]]:
    """Atributos do produto. As datas podem estar ocultas na ficha, por isso
    a leitura de edições pede visible_only=False."""
    values: dict[str, list[str]] = {}
    for attribute in product.get("attributes", []):
        if visible_only and not attribute.get("visible", True):
            continue
        name = (attribute.get("name") or "").strip()
        if name:
            values[name] = _option_values(attribute)
    return values


def _meta(product: dict, key: str) -> str:
    for item in product.get("meta_data", []):
        if item.get("key") == key:
            return str(item.get("value") or "")
    return ""


def _english(product: dict) -> dict:
    """Versão inglesa guardada em meta (lw_*_en). Campos em falta ficam vazios (fallback PT no template)."""
    try:
        attrs = json.loads(_meta(product, "lw_attributes_en") or "{}")
    except ValueError:
        attrs = {}
    return {
        "name": _meta(product, "lw_name_en"),
        "short_description": _meta(product, "lw_short_description_en"),
        "description": _meta(product, "lw_description_en"),
        "button_text": _meta(product, "lw_button_text_en"),
        "category": _meta(product, "lw_category_en"),
        "attributes": attrs if isinstance(attrs, dict) else {},
    }


def _image(product: dict) -> dict | None:
    image = (product.get("images") or [None])[0]
    if not image:
        return None
    return {"src": image.get("src", ""), "alt": image.get("alt") or product.get("name", "")}


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text or "")
    stripped = "".join(char for char in normalized if not unicodedata.combining(char))
    return stripped.casefold().strip().rstrip(".")


def _text(value) -> str:
    if isinstance(value, (list, tuple)):
        return str(value[0]).strip() if value else ""
    return str(value or "").strip()


def _parse_day(value) -> str | None:
    """YYYY-MM-DD, mesmo dentro de outro texto, ou YYYYMMDD."""
    text = _text(value)
    compact = re.fullmatch(r"(20\d{2})(\d{2})(\d{2})", text)
    if compact:
        text = f"{compact.group(1)}-{compact.group(2)}-{compact.group(3)}"
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    if not match:
        return None
    try:
        return dt.date.fromisoformat(match.group(1)).isoformat()
    except ValueError:
        return None


def _parse_month(value) -> str | None:
    """YYYY-MM (mês de início) → primeiro dia desse mês, só para ordenar e filtrar."""
    match = re.fullmatch(r"(20\d{2})-(\d{2})", _text(value))
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        return None
    return dt.date(year, month, 1).isoformat()


def _lookup(attrs: dict[str, list[str]], *names: str) -> list[str]:
    folded = {_fold(key): value for key, value in attrs.items()}
    for name in names:
        found = folded.get(_fold(name))
        if found:
            return found
    return []


def _sku_day(sku: str) -> str | None:
    found = re.findall(r"20\d{2}-\d{2}-\d{2}", sku or "")
    return _parse_day(found[-1]) if found else None


_MONTHS = {
    "jan": 1, "janeiro": 1, "feb": 2, "fev": 2, "fevereiro": 2,
    "mar": 3, "marco": 3, "abr": 4, "abril": 4, "apr": 4,
    "mai": 5, "maio": 5, "may": 5, "jun": 6, "junho": 6,
    "jul": 7, "julho": 7, "ago": 8, "agosto": 8, "aug": 8,
    "set": 9, "setembro": 9, "sep": 9, "out": 10, "outubro": 10, "oct": 10,
    "nov": 11, "novembro": 11, "dez": 12, "dezembro": 12, "dec": 12,
}
_RANGE = re.compile(
    r"(\d{1,2})\s*[–—-]\s*(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\.?\s+(20\d{2})"
)


def _end_from_name(product: dict, start: str | None) -> str | None:
    """'7–11 dez 2026' no nome da edição, quando não há 'Data de fim'."""
    if not start:
        return None
    year_s, month_s, day_s = (int(part) for part in start.split("-"))
    text = " ".join(str(product.get(key) or "") for key in ("name", "short_description"))
    for match in _RANGE.finditer(text):
        day_1, day_2, month_name, year = match.groups()
        month = _MONTHS.get(_fold(month_name))
        if month != month_s or int(year) != year_s or int(day_1) != day_s:
            continue
        try:
            return dt.date(int(year), month, int(day_2)).isoformat()
        except ValueError:
            return None
    return None


def _resolve_start(product: dict, attrs: dict[str, list[str]]) -> tuple[str | None, str | None]:
    """Data de início da edição. Ordem: atributo (visível ou não), meta ACF,
    data no SKU, e por fim 'Mês de início' (YYYY-MM)."""
    for name in ("Data de início", "Data inicio", "Start date"):
        day = _parse_day(_lookup(attrs, name))
        if day:
            return day, "day"
    for key in ("data_inicio", "data_de_inicio"):
        day = _parse_day(_meta(product, key))
        if day:
            return day, "day"
    day = _sku_day(product.get("sku") or "")
    if day:
        return day, "day"
    month_value = _lookup(attrs, "Mês de início", "Mes de início")
    day = _parse_day(month_value)
    if day:
        return day, "day"
    month = _parse_month(month_value)
    if month:
        return month, "month"
    return None, None


def _resolve_end(product: dict, attrs: dict[str, list[str]], start: str | None) -> str | None:
    for name in ("Data de fim", "Data fim", "End date"):
        day = _parse_day(_lookup(attrs, name))
        if day:
            return day
    for key in ("data_fim", "data_de_fim"):
        day = _parse_day(_meta(product, key))
        if day:
            return day
    return _end_from_name(product, start)


def _is_upcoming(start: str | None, precision: str | None, today: dt.date) -> bool:
    """Sem data conta como edição por agendar. Um mês (YYYY-MM) conta enquanto
    esse mês não tiver terminado. Uma data completa anterior a hoje fica de fora."""
    if not start:
        return True
    if precision == "month":
        year, month, _day = (int(part) for part in start.split("-"))
        return (year, month) >= (today.year, today.month)
    return start >= today.isoformat()


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

            visible = _attributes(child)
            all_attrs = _attributes(child, visible_only=False)
            start, precision = _resolve_start(child, all_attrs)
            edition = {
                "id": child["id"],
                "name": child.get("name", ""),
                "url": child.get("external_url") or "",
                "button_text": child.get("button_text") or "Inscrever",
                "start": start,
                "end": _resolve_end(child, all_attrs, start),
                "start_precision": precision,
                "format": visible.get("Formato") or all_attrs.get("Formato", []),
                "button_text_en": _meta(child, "lw_button_text_en"),
            }
            if (child.get("sku") or "").endswith("-CONSULTA"):
                enquiry = edition
            elif _is_upcoming(start, precision, today):
                editions.append(edition)

        attrs = _attributes(parent)
        enrol_url = _meta(parent, "lw_enrol_url") or (enquiry or {}).get("url") or ""

        # Datas no próprio curso (uma sessão por curso, sem produto de edição).
        parent_attrs = _attributes(parent, visible_only=False)
        own_start, own_precision = _resolve_start(parent, parent_attrs)
        if (
            own_start
            and _is_upcoming(own_start, own_precision, today)
            and not any(item["start"] == own_start for item in editions)
        ):
            editions.append({
                "id": parent["id"],
                "name": parent.get("name", ""),
                "url": enrol_url,
                "button_text": _meta(parent, "lw_button_text") or "Inscrever",
                "start": own_start,
                "end": _resolve_end(parent, parent_attrs, own_start),
                "start_precision": own_precision,
                "format": attrs.get("Formato", [])[:1],
                "button_text_en": "",
            })

        courses.append(
            {
                "id": parent["id"],
                "slug": parent["slug"],
                "sku": parent.get("sku") or "",
                "name": parent.get("name", ""),
                "short_description": parent.get("short_description", ""),
                "description": parent.get("description", ""),
                "image": _image(parent),
                "en": _english(parent),
                "categories": [
                    category["name"] for category in parent.get("categories", [])
                ],
                "standard": (attrs.get("Norma / Regulamento") or [None])[0],
                "level": (attrs.get("Nível") or [None])[0],
                "duration": (attrs.get("Duração") or [None])[0],
                "language": (attrs.get("Língua") or [None])[0],
                "languages": attrs.get("Língua", []),
                "editions": sorted(
                    editions,
                    key=lambda item: (item.get("start") is None, item.get("start") or ""),
                ),
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


def get_course(slug: str) -> dict | None:
    """Curso publicado pelo slug (a partir do catálogo em cache)."""
    return next((course for course in get_catalog() if course["slug"] == slug), None)
