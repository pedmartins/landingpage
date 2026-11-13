"""Imagens 16:9 (1600x900) para os cursos PECB, na identidade ai-gov.network.
Zona segura central 900x900 (x 350–1250) para recortes quadrados do WooCommerce."""
import math, os, sys

NAVY, NAVY2, TEAL, TEALD, CREAM, MUTED, ORANGE = "#1a2d3d", "#223a4f", "#1a9e8a", "#0d6e5f", "#f5f3ee", "#5a6a78", "#D4844A"
CX, CY = 800, 420
S = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'

def g(x, y, s, body):
    return f'<g transform="translate({x},{y}) scale({s})">{body}</g>'

# ---------- objetos (coordenadas locais 0..400, centro 200,200) ----------
SHIELD = "M200 30 L335 82 V195 C335 290 275 345 200 375 C125 345 65 290 65 195 V82 Z"

def shield(fill=0.10):
    return (f'<path d="{SHIELD}" fill="{TEAL}" fill-opacity="{fill}"/>'
            f'<path d="{SHIELD}" {S} stroke="{TEAL}" stroke-width="7"/>')

def lock(cx=200, cy=215, c=CREAM):
    return (f'<path d="M{cx-32} {cy-20} V{cy-48} a32 32 0 0 1 64 0 V{cy-20}" {S} stroke="{c}" stroke-width="9"/>'
            f'<rect x="{cx-50}" y="{cy-20}" width="100" height="78" rx="10" fill="{c}"/>'
            f'<circle cx="{cx}" cy="{cy+12}" r="9" fill="{NAVY}"/><rect x="{cx-4}" y="{cy+14}" width="8" height="24" rx="3" fill="{NAVY}"/>')

def obj_27001():
    # escudo + cadeado + linhas de dados
    bits = "".join(f'<rect x="{95+i*22}" y="{300- (i%3)*0}" width="12" height="4" rx="2" fill="{TEAL}" opacity=".0"/>' for i in range(0))
    return shield() + lock()

def obj_27701():
    # impressão digital: arcos aninhados abertos em baixo, com comprimentos irregulares
    cx, cy = 200, 205
    lens = [(0, 18), (30, 10), (14, 40), (44, 22), (26, 52), (58, 34)]
    out = ""
    for i, (l1, l2) in enumerate(lens):
        rx, ry = 14 + i*15, 20 + i*19
        dash = ' stroke-dasharray="70 12"' if i in (2, 4) else ""
        out += (f'<path d="M{cx-rx} {cy+l1} V{cy} A{rx} {ry} 0 0 1 {cx+rx} {cy} V{cy+l2}" {S} '
                f'stroke="{CREAM}" stroke-width="7"{dash}/>')
    return shield() + out

def obj_22301():
    # ciclo de continuidade + pulso
    r = 135
    def arc(a0, a1):
        x0, y0 = 200 + r*math.cos(math.radians(a0)), 200 + r*math.sin(math.radians(a0))
        x1, y1 = 200 + r*math.cos(math.radians(a1)), 200 + r*math.sin(math.radians(a1))
        return f'<path d="M{x0:.1f} {y0:.1f} A{r} {r} 0 0 1 {x1:.1f} {y1:.1f}" {S} stroke="{TEAL}" stroke-width="9"/>'
    def head(a):
        x, y = 200 + r*math.cos(math.radians(a)), 200 + r*math.sin(math.radians(a))
        t = math.radians(a + 90)
        p = lambda d, o: (x + d*math.cos(t) + o*math.cos(t+math.pi/2), y + d*math.sin(t) + o*math.sin(t+math.pi/2))
        a1, a2, a3 = p(16, 0), p(-10, 16), p(-10, -16)
        return f'<path d="M{a1[0]:.1f} {a1[1]:.1f} L{a2[0]:.1f} {a2[1]:.1f} L{a3[0]:.1f} {a3[1]:.1f} Z" fill="{TEAL}"/>'
    pulse = f'<path d="M55 200 H140 L160 150 L185 260 L210 120 L232 230 L248 200 H345" {S} stroke="{CREAM}" stroke-width="8"/>'
    return (f'<circle cx="200" cy="200" r="{r}" fill="{TEAL}" fill-opacity=".08"/>' + arc(-60, 100) + head(100) + arc(120, 280) + head(280) + pulse)

def matrix(x0=95, y0=95, n=5, cell=42, gap=6):
    out = ""
    for i in range(n):
        for j in range(n):
            lvl = (i + (n-1-j)) / (2*(n-1))  # canto superior direito = risco alto
            col = ORANGE if lvl > .62 else (TEAL if lvl < .38 else CREAM)
            op = .9 if lvl > .62 else (.55 if lvl < .38 else .35)
            out += f'<rect x="{x0+i*(cell+gap)}" y="{y0+j*(cell+gap)}" width="{cell}" height="{cell}" rx="6" fill="{col}" fill-opacity="{op}"/>'
    return out

def obj_27005():
    return shield(.08) + matrix(120, 115, 4, 34, 6)

def obj_31000():
    rings = "".join(f'<circle cx="200" cy="200" r="{r}" {S} stroke="{TEAL}" stroke-width="{w}" opacity="{o}"/>' for r, w, o in [(150, 6, .5), (112, 7, .8), (74, 8, 1)])
    dots = ""
    for k in range(8):
        a = math.radians(k*45 - 90)
        dots += f'<circle cx="{200+150*math.cos(a):.1f}" cy="{200+150*math.sin(a):.1f}" r="10" fill="{CREAM}"/>'
    for k in range(5):
        a = math.radians(k*72 - 90)
        dots += f'<circle cx="{200+112*math.cos(a):.1f}" cy="{200+112*math.sin(a):.1f}" r="8" fill="{TEAL}"/>'
    core = f'<circle cx="200" cy="200" r="38" fill="{ORANGE}" fill-opacity=".9"/><path d="M182 202 l12 12 l24 -28" {S} stroke="{NAVY}" stroke-width="8"/>'
    return rings + dots + core

def obj_42001():
    chip = f'<rect x="85" y="85" width="230" height="230" rx="26" fill="{TEAL}" fill-opacity=".08" stroke="{TEAL}" stroke-width="7"/>'
    pins = ""
    for k in range(5):
        p = 115 + k*42.5
        pins += (f'<line x1="{p}" y1="50" x2="{p}" y2="85" {S} stroke="{TEAL}" stroke-width="6"/>'
                 f'<line x1="{p}" y1="315" x2="{p}" y2="350" {S} stroke="{TEAL}" stroke-width="6"/>'
                 f'<line x1="50" y1="{p}" x2="85" y2="{p}" {S} stroke="{TEAL}" stroke-width="6"/>'
                 f'<line x1="315" y1="{p}" x2="350" y2="{p}" {S} stroke="{TEAL}" stroke-width="6"/>')
    L = [[(130, y) for y in (140, 200, 260)], [(200, y) for y in (125, 175, 225, 275)], [(270, y) for y in (165, 235)]]
    edges = "".join(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="{CREAM}" stroke-width="2.5" opacity=".55"/>'
                    for l1, l2 in zip(L, L[1:]) for a in l1 for b in l2)
    nodes = "".join(f'<circle cx="{x}" cy="{y}" r="12" fill="{ORANGE if (x, y) == (270, 165) else CREAM}"/>' for l in L for x, y in l)
    return chip + pins + edges + nodes

def obj_dora():
    bank = (f'<path d="M80 150 L200 85 L320 150 Z" fill="{TEAL}" fill-opacity=".12" stroke="{TEAL}" stroke-width="7" stroke-linejoin="round"/>'
            + "".join(f'<rect x="{x}" y="165" width="26" height="120" rx="4" fill="{CREAM}" opacity=".9"/>' for x in (100, 157, 217, 274))
            + f'<rect x="75" y="292" width="250" height="18" rx="5" fill="{TEAL}"/><rect x="60" y="318" width="280" height="16" rx="5" fill="{TEALD}"/>')
    pulse = f'<path d="M95 255 H140 L152 232 L166 270 L180 240 L190 255 H305" {S} stroke="{ORANGE}" stroke-width="6" opacity="0"/>'
    ring = f'<circle cx="200" cy="215" r="175" {S} stroke="{TEAL}" stroke-width="3" stroke-dasharray="4 14" opacity=".7"/>'
    return ring + bank + pulse

def obj_nis2():
    pts = [(200, 200)] + [(200 + 140*math.cos(math.radians(a)), 200 + 140*math.sin(math.radians(a))) for a in range(-90, 270, 60)]
    edges = "".join(f'<line x1="{pts[0][0]}" y1="{pts[0][1]}" x2="{p[0]:.1f}" y2="{p[1]:.1f}" stroke="{TEAL}" stroke-width="4" opacity=".7"/>' for p in pts[1:])
    edges += "".join(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{TEAL}" stroke-width="3" stroke-dasharray="6 8" opacity=".6"/>' for a, b in zip(pts[1:], pts[2:] + pts[1:2]))
    icons = ['<path d="M-6 -16 L-14 4 H0 L-6 18 L14 -4 H0 Z" fill="{c}"/>',            # energia
             '<path d="M0 -17 C8 -5 13 2 13 7 a13 13 0 0 1 -26 0 C-13 2 -8 -5 0 -17 Z" fill="{c}"/>',  # água
             '<path d="M-16 8 H16 M-12 8 V-2 H12 V8 M-6 -2 V-12 H6 V-2" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/>',  # indústria/edifício
             '<path d="M-14 6 h28 M-10 6 l4 -14 h12 l4 14 M-9 12 a3 3 0 1 0 0.1 0 M9 12 a3 3 0 1 0 0.1 0" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/>',  # transporte
             '<path d="M0 -14 a14 14 0 1 1 -0.1 0 M-14 0 H14 M0 -14 C-7 -6 -7 6 0 14 M0 -14 C7 -6 7 6 0 14" fill="none" stroke="{c}" stroke-width="3.5"/>',  # digital
             '<path d="M-13 -4 H13 V14 H-13 Z M-7 -4 V-10 a7 7 0 0 1 14 0 V-4" fill="none" stroke="{c}" stroke-width="4"/><path d="M-4 5 h8" stroke="{c}" stroke-width="4"/>']  # saúde/serviços
    nodes = ""
    for p, ic in zip(pts[1:], icons):
        nodes += f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="34" fill="{NAVY2}" stroke="{TEAL}" stroke-width="5"/>'
        nodes += f'<g transform="translate({p[0]:.1f},{p[1]:.1f})">{ic.format(c=CREAM)}</g>'
    center = g(200 - 52, 200 - 52, .26, shield(.3)) + f'<circle cx="200" cy="200" r="0"/>'
    mini = f'<g transform="translate(200,205)"><path d="M-12 -2 v-10 a12 12 0 0 1 24 0 v10" {S} stroke="{CREAM}" stroke-width="5"/><rect x="-18" y="-3" width="36" height="28" rx="5" fill="{CREAM}"/></g>'
    return edges + nodes + center + mini

# ---------- nível (sobreposição laranja, coord. locais ~100x100) ----------
def gear():
    teeth = "".join(f'<rect x="-9" y="-50" width="18" height="20" rx="4" fill="{ORANGE}" transform="rotate({a})"/>' for a in range(0, 360, 45))
    return teeth + f'<circle r="36" fill="{ORANGE}"/><circle r="15" fill="{NAVY}"/>'

def magnifier():
    return (f'<circle cx="-8" cy="-8" r="34" fill="{NAVY}" stroke="{ORANGE}" stroke-width="11"/>'
            f'<path d="M-24 -8 l10 10 l20 -22" {S} stroke="{CREAM}" stroke-width="8"/>'
            f'<line x1="18" y1="18" x2="46" y2="46" {S} stroke="{ORANGE}" stroke-width="15"/>')

def gauge():
    return (f'<circle r="46" fill="{NAVY}" stroke="{ORANGE}" stroke-width="8"/>'
            f'<path d="M-30 12 A32 32 0 0 1 30 12" {S} stroke="{CREAM}" stroke-width="7" stroke-dasharray="14 7"/>'
            f'<line x1="0" y1="12" x2="22" y2="-20" {S} stroke="{ORANGE}" stroke-width="8"/><circle cy="12" r="8" fill="{ORANGE}"/>')

def compass():
    return (f'<circle r="46" fill="{NAVY}" stroke="{ORANGE}" stroke-width="8"/>'
            f'<path d="M0 -34 L12 0 L0 34 L-12 0 Z" fill="{CREAM}"/><path d="M0 -34 L12 0 L-12 0 Z" fill="{ORANGE}"/>'
            f'<circle r="5" fill="{NAVY}"/>')

LEVEL = {"Lead Implementer": gear, "Lead Auditor": magnifier, "Lead Risk Manager": gauge, "Lead Manager": compass}

COURSES = [  # sku, norma (tag), número (marca d'água), nível, objeto
    ("27001-LI", "ISO/IEC 27001", "27001", "Lead Implementer", obj_27001),
    ("27001-LA", "ISO/IEC 27001", "27001", "Lead Auditor", obj_27001),
    ("27701-LI", "ISO/IEC 27701", "27701", "Lead Implementer", obj_27701),
    ("27701-LA", "ISO/IEC 27701", "27701", "Lead Auditor", obj_27701),
    ("22301-LI", "ISO 22301", "22301", "Lead Implementer", obj_22301),
    ("22301-LA", "ISO 22301", "22301", "Lead Auditor", obj_22301),
    ("27005-LRM", "ISO/IEC 27005", "27005", "Lead Risk Manager", obj_27005),
    ("31000-LRM", "ISO 31000", "31000", "Lead Risk Manager", obj_31000),
    ("42001-LI", "ISO/IEC 42001", "42001", "Lead Implementer", obj_42001),
    ("42001-LA", "ISO/IEC 42001", "42001", "Lead Auditor", obj_42001),
    ("DORA-LM", "DORA", "DORA", "Lead Manager", obj_dora),
    ("NIS2-LI", "NIS 2", "NIS 2", "Lead Implementer", obj_nis2),
]

def background(seed, W, H, safe):
    import random
    rnd = random.Random(seed)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="1.6" fill="{CREAM}" opacity=".10"/>' for x in range(40, W, 40) for y in range(40, H, 40))
    net = ""
    zones = [(30, safe[0]-40, 40, H-40), (safe[1]+40, W-30, 40, H-40)] if W > H else [(30, W-30, 30, 200), (30, W-30, H-260, H-150)]
    for (xa, xb, ya, yb) in zones:
        pts = [(rnd.uniform(xa, xb), rnd.uniform(ya, yb)) for _ in range(10)]
        for i, a in enumerate(pts):
            for b in pts[i+1:]:
                if math.dist(a, b) < 280:
                    net += f'<line x1="{a[0]:.0f}" y1="{a[1]:.0f}" x2="{b[0]:.0f}" y2="{b[1]:.0f}" stroke="{TEAL}" stroke-width="1.5" opacity=".28"/>'
        net += "".join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.choice([3,4,6])}" fill="{rnd.choice([TEAL, TEAL, ORANGE])}" opacity=".6"/>' for x, y in pts)
    return (f'<defs><radialGradient id="glow" cx="50%" cy="50%" r="{40 if W>H else 55}%"><stop offset="0" stop-color="{TEAL}" stop-opacity=".30"/>'
            f'<stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient></defs>'
            f'<rect width="{W}" height="{H}" fill="{NAVY}"/>{dots}<rect width="{W}" height="{H}" fill="url(#glow)"/>{net}')

def motif(cx, cy, k, level, obj):
    out = f'<circle cx="{cx}" cy="{cy}" r="{255*k}" fill="{NAVY}" fill-opacity=".55" stroke="{TEAL}" stroke-opacity=".35" stroke-width="2"/>'
    out += g(cx - 220*k, cy - 220*k, 1.1*k, obj())
    out += f'<g transform="translate({cx+170*k},{cy+165*k}) scale({1.25*k})"><circle r="58" fill="{NAVY}"/>{LEVEL[level]()}</g>'
    return out

def label(x, y, tag, level, size, anchor="middle"):
    t = f"{tag}  ·  {level}".upper()
    lx = x if anchor == "middle" else x + 40
    return (f'<line x1="{lx-40}" y1="{y-50}" x2="{lx+40}" y2="{y-50}" stroke="{ORANGE}" stroke-width="4" stroke-linecap="round"/>'
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Barlow Condensed" font-weight="600" font-size="{size}" '
            f'letter-spacing="5" fill="{CREAM}">{t}</text>')

def svg_banner(sku, tag, num, level, obj):
    W, H = 2400, 800
    body = background(sku, W, H, (800, 1600))
    body += (f'<text x="120" y="{H/2+80}" font-family="Barlow Condensed" font-weight="700" font-size="260" '
             f'fill="none" stroke="{CREAM}" stroke-opacity=".08" stroke-width="2">{num}</text>')
    body += motif(1200, 400, 0.95, level, obj)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{body}</svg>'

def svg_square(sku, tag, num, level, obj):
    W, H = 1200, 1200
    body = background(sku, W, H, None)
    body += (f'<text x="{W-60}" y="150" text-anchor="end" font-family="Barlow Condensed" font-weight="700" font-size="150" '
             f'fill="none" stroke="{CREAM}" stroke-opacity=".08" stroke-width="2">{num}</text>')
    body += motif(600, 560, 1.4, level, obj)
    body += label(600, 1110, tag, level, 46)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{body}</svg>'

if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for c in COURSES:
        open(os.path.join(out, f"pecb-{c[0].lower()}-banner.svg"), "w").write(svg_banner(*c))
        open(os.path.join(out, f"pecb-{c[0].lower()}-quadrado.svg"), "w").write(svg_square(*c))
    print("ok", len(COURSES))
