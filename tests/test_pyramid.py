"""The AI Act risk pyramid is four slices of one triangle."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as site

# Apex (250, 30), base y=390, half-width 240. Slope dx/dy = -2/3 on the left.
APEX = (250, 30)
BASE_Y = 390
HALF = 240

LABELS = {
    "/framework": [
        "Inibido",
        "Risco Inaceitável",
        "Risco Elevado",
        "Conformidade Obrigatória",
        "Risco Limitado",
        "Obrigações de Transparência",
        "Risco Mínimo",
        "Livre Utilização",
    ],
    "/en/framework": [
        "Prohibited",
        "Unacceptable Risk",
        "High Risk",
        "Mandatory Compliance",
        "Limited Risk",
        "Transparency Obligations",
        "Minimal Risk",
        "Free Use",
    ],
}


def _points(raw):
    nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", raw)]
    return list(zip(nums[0::2], nums[1::2]))


def _pyramid_polygons(html):
    svg = html.split('id="pyramid-svg"', 1)[1].split("</svg>", 1)[0]
    chunks = re.findall(
        r'id="(layer-[^"]+)"[^>]*>\s*<polygon points="([^"]+)" fill="([^"]+)"',
        svg,
    )
    assert len(chunks) == 4, chunks
    return [(layer, _points(points), fill) for layer, points, fill in chunks]


def _on_left_edge(x, y):
    expected = APEX[0] - HALF * (y - APEX[1]) / (BASE_Y - APEX[1])
    return abs(x - expected) < 0.05


def _on_right_edge(x, y):
    expected = APEX[0] + HALF * (y - APEX[1]) / (BASE_Y - APEX[1])
    return abs(x - expected) < 0.05


def test_layers_are_one_triangle_in_both_languages():
    client = site.app.test_client()
    for path, labels in LABELS.items():
        page = client.get(path)
        assert page.status_code == 200, path
        html = page.get_data(as_text=True)
        polygons = _pyramid_polygons(html)
        assert [fill for _, _, fill in polygons] == [
            "#1a9e8a",
            "#5B3F9E",
            "#C4408C",
            "#E05555",
        ]

        left_edges = []
        right_edges = []
        for layer, pts, _fill in polygons:
            assert all(_on_left_edge(x, y) or _on_right_edge(x, y) or (x, y) == APEX for x, y in pts), (
                path,
                layer,
                pts,
            )
            ys = sorted({y for _, y in pts})
            assert len(ys) in (1, 2) or (layer == "layer-unacceptable" and APEX in pts)
            for x, y in pts:
                if (x, y) == APEX:
                    continue
                if _on_left_edge(x, y):
                    left_edges.append((y, x))
                if _on_right_edge(x, y):
                    right_edges.append((y, x))

        # Uniform gap: each lower layer starts 6px below the one above.
        bands = []
        for layer, pts, _fill in polygons:
            ys = [y for _, y in pts]
            bands.append((min(ys), max(ys), layer))
        # Render order is bottom → top, so reverse to walk downward.
        bands_top_down = list(reversed(bands))
        gaps = [
            bands_top_down[i + 1][0] - bands_top_down[i][1]
            for i in range(len(bands_top_down) - 1)
        ]
        assert gaps == [6, 6, 6], (path, gaps)

        # Apex is the shared tip; the base is the full width of the triangle.
        assert APEX in polygons[-1][1]
        base = [p for p in polygons[0][1] if p[1] == BASE_Y]
        assert sorted(base) == [(10, BASE_Y), (490, BASE_Y)]

        for label in labels:
            assert label in html, (path, label)

        # Decorative arrows and the active-layer shadow stay in place.
        assert html.count('id="indicator-arrow-') == 3
        assert "drop-shadow" in html

        # Each layer is a button: the polygon and its labels are the hit target,
        # and the info panels share one grid cell so clicks cannot resize the row.
        assert html.count('class="pyramid-layer"') == 4
        assert html.count('role="button"') == 4
        assert html.count('tabindex="0"') == 4
        assert "grid-area: 1 / 1" in html
        assert "pointer-events: none" not in html
