"""Edições da homepage: a data não pode depender só de um atributo visível."""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import wc_catalog as catalog

TODAY = dt.date(2026, 11, 16)


def attr(name, options, visible=True):
    return {"name": name, "options": options, "visible": visible}


def parent(pid, name, sku, children, **extra):
    product = {
        "id": pid,
        "name": name,
        "slug": sku.lower(),
        "status": "publish",
        "sku": sku,
        "menu_order": pid,
        "short_description": "<p>Formação certificada PECB.</p>",
        "description": "",
        "categories": [{"name": "Regulamentação UE"}],
        "attributes": [
            attr("Norma / Regulamento", ["DORA"]),
            attr("Nível", ["Lead Manager"]),
            attr("Duração", ["5 dias"]),
        ],
        "grouped_products": children,
    }
    product.update(extra)
    return product


def test_hidden_full_dates_are_kept():
    """O atributo pode existir no admin com 'visível na página' desligado."""
    courses = catalog.normalize(
        [parent(5415, "PECB DORA Lead Manager", "LW-PECB-DORA-LM", [5401])],
        [{
            "id": 5401,
            "status": "publish",
            "sku": "LW-PECB-DORA-LM-2026-12-07",
            "name": "DORA Lead Manager — 7–11 dez 2026 · online",
            "external_url": "https://example.test/dora",
            "attributes": [
                attr("Mês de início", ["2026-12"]),
                attr("Formato", ["Online em direto (Microsoft Teams)"]),
                attr("Data de início", ["2026-12-07"], visible=False),
                attr("Data de fim", ["2026-12-11"], visible=False),
            ],
        }],
        TODAY,
    )
    edition = courses[0]["editions"][0]
    assert edition["start"] == "2026-12-07"
    assert edition["end"] == "2026-12-11"
    assert edition["start_precision"] == "day"
    assert edition["format"] == ["Online em direto (Microsoft Teams)"]


def test_sku_and_name_when_only_month_attribute_is_visible():
    """Estado real de 16 nov 2026: DORA só publica 'Mês de início' = 2026-12."""
    courses = catalog.normalize(
        [parent(5415, "PECB DORA Lead Manager", "LW-PECB-DORA-LM", [5401])],
        [{
            "id": 5401,
            "status": "publish",
            "sku": "LW-PECB-DORA-LM-2026-12-07",
            "name": "DORA Lead Manager — 7–11 dez 2026 · online (Microsoft Teams)",
            "external_url": "https://example.test/dora",
            "attributes": [
                attr("Mês de início", ["2026-12"]),
                attr("Formato", ["Online em direto (Microsoft Teams)"]),
            ],
        }],
        TODAY,
    )
    edition = courses[0]["editions"][0]
    assert edition["start"] == "2026-12-07"
    assert edition["end"] == "2026-12-11"
    assert edition["start_precision"] == "day"


def test_acf_meta_dates():
    courses = catalog.normalize(
        [parent(1, "Curso", "LW-PECB-X", [2])],
        [{
            "id": 2,
            "status": "publish",
            "sku": "LW-PECB-X-EDICAO",
            "name": "Edição sem atributo",
            "meta_data": [
                {"key": "data_inicio", "value": "2026-12-07"},
                {"key": "data_fim", "value": "2026-12-11"},
            ],
            "attributes": [],
        }],
        TODAY,
    )
    edition = courses[0]["editions"][0]
    assert edition["start"] == "2026-12-07"
    assert edition["end"] == "2026-12-11"


def test_visible_nis2_date_still_wins():
    courses = catalog.normalize(
        [parent(5416, "PECB NIS 2", "LW-PECB-NIS2-LI", [5403])],
        [{
            "id": 5403,
            "status": "publish",
            "sku": "LW-PECB-NIS2-LI-2026-12-14",
            "name": "NIS 2 — 14–18 dez 2026",
            "attributes": [
                attr("Data de início", ["2026-12-14"]),
                attr("Data de fim", ["2026-12-18"]),
            ],
        }],
        TODAY,
    )
    edition = courses[0]["editions"][0]
    assert (edition["start"], edition["end"]) == ("2026-12-14", "2026-12-18")


def test_past_and_draft_editions_are_dropped():
    courses = catalog.normalize(
        [parent(5414, "PECB ISO/IEC 42001 Lead Auditor", "LW-PECB-42001-LA", [5399, 5300])],
        [
            {
                "id": 5399,
                "status": "draft",
                "sku": "LW-PECB-42001-LA-2026-11-16",
                "name": "16–20 nov 2026",
                "attributes": [attr("Data de início", ["2026-11-16"])],
            },
            {
                "id": 5300,
                "status": "publish",
                "sku": "LW-PECB-42001-LA-2026-11-02",
                "name": "edição passada",
                "attributes": [attr("Data de início", ["2026-11-02"])],
            },
        ],
        TODAY,
    )
    assert courses[0]["editions"] == []


def test_published_edition_without_any_date_is_kept():
    courses = catalog.normalize(
        [parent(9, "Curso sem data", "LW-PECB-NODATE", [8])],
        [{
            "id": 8,
            "status": "publish",
            "sku": "LW-PECB-NODATE-ED",
            "name": "Edição a agendar",
            "attributes": [attr("Formato", ["Online"])],
        }],
        TODAY,
    )
    edition = courses[0]["editions"][0]
    assert edition["start"] is None
    assert edition["format"] == ["Online"]


def test_month_only_future_is_kept_and_past_month_is_not():
    courses = catalog.normalize(
        [
            parent(1, "Futuro", "LW-PECB-FUT", [11]),
            parent(2, "Passado", "LW-PECB-PAS", [12]),
        ],
        [
            {
                "id": 11,
                "status": "publish",
                "sku": "LW-PECB-FUT-ED",
                "name": "só mês",
                "attributes": [attr("Mês de início", ["2026-12"])],
            },
            {
                "id": 12,
                "status": "publish",
                "sku": "LW-PECB-PAS-ED",
                "name": "mês passado",
                "attributes": [attr("Mês de início", ["2026-10"])],
            },
        ],
        TODAY,
    )
    by_sku = {course["sku"]: course for course in courses}
    assert by_sku["LW-PECB-FUT"]["editions"][0]["start_precision"] == "month"
    assert by_sku["LW-PECB-FUT"]["editions"][0]["start"] == "2026-12-01"
    assert by_sku["LW-PECB-PAS"]["editions"] == []


def test_session_label_range_month_and_missing():
    os.environ.setdefault("WP_API_URL", "")
    import app as homepage

    assert homepage._session_label(
        {"start": "2026-12-07", "end": "2026-12-11", "start_precision": "day"}, "pt"
    ) == "7–11 dez 2026"
    assert homepage._session_label(
        {"start": "2026-12-01", "start_precision": "month"}, "pt"
    ) == "dez 2026"
    assert homepage._session_label({"start": None}, "pt") == "Por confirmar"
    assert homepage._session_label({"start": None}, "en") == "To be confirmed"
