"""
festival_art_generator.py
--------------------------
Generates unique SVG vector art for each festival algorithmically.
Zero API cost — pure Python math, no external network calls beyond Supabase.

Each festival gets a visual style derived from:
  - accent_color → color palette (complementary/triadic harmony)
  - tags         → motif  (radial=EDM, shatter=rock, wave=folk/jazz, bloom=indie, blocks=hip-hop)
  - slug         → deterministic random seed (same slug = same art, always)

Run:
    python festival_art_generator.py                  # all festivals missing art
    python festival_art_generator.py --festival lollapalooza
    python festival_art_generator.py --force           # regenerate all
    python festival_art_generator.py --preview         # print SVG to stdout, no DB
    python festival_art_generator.py --output-dir /tmp # save .svg files
"""

import os
import math
import hashlib
import colorsys
import logging
import argparse
import time
import random as _stdlib_random
from pathlib import Path
from dotenv import load_dotenv

from supabase import create_client, Client
from rich.console import Console
from rich.progress import track

load_dotenv()
console = Console()
log = logging.getLogger(__name__)

W, H = 800, 500   # SVG canvas dimensions


# ── Colour helpers ────────────────────────────────────────────

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hsv_to_rgb(hue: float, sat: float, val: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, max(0.0, min(1.0, sat)), max(0.0, min(1.0, val)))
    return int(r * 255), int(g * 255), int(b * 255)


def _rgba(r: int, g: int, b: int, a: float) -> str:
    return f"rgba({r},{g},{b},{a:.3f})"


def _hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _build_palette(accent_hex: str, rng: _stdlib_random.Random) -> dict:
    """
    Derives a 5-colour palette from the accent colour.
    Uses HSV colour model for perceptually consistent derivations.
    """
    r, g, b = _hex_to_rgb(accent_hex)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

    # Ensure colours are vivid enough for dark backgrounds
    s = max(s, 0.55)
    v = max(v, 0.65)

    # Rich coloured background — vivid deep tone, never near-black
    bg  = _hsv_to_rgb(h, min(s * 0.90, 0.88), 0.40)

    # Gradient pair: complementary hue, slightly darker
    bg2 = _hsv_to_rgb((h + 0.55) % 1.0, min(s * 0.75, 0.80), 0.28)

    # Primary accent (normalised)
    p1 = _hsv_to_rgb(h, s, v)

    # Complementary (180° shift)
    p2 = _hsv_to_rgb((h + 0.5) % 1.0, s * 0.9, min(v + 0.1, 1.0))

    # Triadic — randomly left or right
    p3_h = (h + rng.choice([0.333, 0.667])) % 1.0
    p3 = _hsv_to_rgb(p3_h, s * 0.8, v * 0.95)

    # Near-white highlight (desaturated accent)
    hl = _hsv_to_rgb(h, s * 0.15, 1.0)

    return {"bg": bg, "bg2": bg2, "p1": p1, "p2": p2, "p3": p3, "hl": hl}


def _choose_motif(tags: list[str]) -> str:
    t = set(tags)
    if t & {"edm", "electronic"}:
        return "radial"
    if t & {"rock", "metal", "punk"}:
        return "shatter"
    if t & {"hip-hop", "r&b", "latin", "reggae"}:
        return "blocks"
    if t & {"folk", "jazz", "blues", "country", "classical"}:
        return "wave"
    if t & {"indie"}:
        return "bloom"
    return "prism"  # multi-genre / default


def _apply_season(palette: dict, tags: list[str]) -> dict:
    """Shifts palette HSV based on season + region tags to give contextual colour feel."""
    tag_set = set(tags)

    # Season: hue_delta, sat_delta, val_delta
    season_shifts: dict[str, tuple[float, float, float]] = {
        "spring":  (+0.02, +0.08, +0.05),   # fresh: pastel shift, slightly brighter
        "summer":  (-0.03, +0.06, +0.08),   # vivid: warmer, punchy
        "fall":    (-0.06, -0.08, -0.05),   # earthy: muted, amber
        "autumn":  (-0.06, -0.08, -0.05),
        "winter":  (+0.10, -0.12, -0.10),   # icy: cool, desaturated
    }

    # Region colour tint adjustments
    region_shifts: dict[str, tuple[float, float, float]] = {
        "southwest":        (-0.04, +0.05, +0.03),   # desert: warm orange-red
        "desert":           (-0.04, +0.05, +0.03),
        "southeast":        (-0.02, +0.04, +0.04),   # tropical: warm, bright
        "south":            (-0.02, +0.04, +0.04),
        "pacific-northwest": (+0.08, -0.05, -0.04),  # misty: cool blue-green
        "northwest":        (+0.08, -0.05, -0.04),
        "midwest":          ( 0.00, -0.03,  0.00),   # neutral: slightly desaturated
        "northeast":        (+0.03, -0.03, -0.02),   # crisp: slight cool shift
    }

    dh, ds, dv = 0.0, 0.0, 0.0
    for tag, shift in {**season_shifts, **region_shifts}.items():
        if tag in tag_set:
            dh += shift[0]; ds += shift[1]; dv += shift[2]

    if dh == ds == dv == 0.0:
        return palette

    def _shift(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        r, g, b = rgb
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        return _hsv_to_rgb(h + dh, s + ds, v + dv)

    # Shift all colour values including bg2
    return {k: _shift(val) if isinstance(val, tuple) else val for k, val in palette.items()}


def _setting_overlay(tags: list[str], palette: dict, rng: _stdlib_random.Random) -> str:
    """Returns an SVG <g> fragment with setting-specific decorative elements."""
    tag_set = set(tags)
    hl = palette["hl"]
    p2 = palette["p2"]
    p1 = palette["p1"]
    parts: list[str] = []

    # Beach / coastal — sinusoidal wave bands at the bottom
    if tag_set & {"beach", "coastal"}:
        for i in range(3):
            y_base = H * (0.82 + i * 0.06)
            amp   = rng.uniform(8, 18)
            freq  = rng.uniform(0.008, 0.014)
            phase = rng.uniform(0, math.pi * 2)
            op    = 0.18 - i * 0.04
            path_pts = " L ".join(
                f"{x:.0f} {y_base + amp * math.sin(freq * x + phase):.1f}"
                for x in range(0, W + 1, 6)
            )
            d = f"M {path_pts} L {W} {H} L 0 {H} Z"
            parts.append(f'<path d="{d}" fill="{_rgba(*p2, op)}"/>')

    # Mountain — layered ridge silhouettes at the bottom
    elif tag_set & {"mountain", "mountains"}:
        for layer, (y_min, y_max, op) in enumerate(
            [(0.48, 0.78, 0.11), (0.60, 0.88, 0.08)]
        ):
            pts = [(0, H)]
            x = 0
            while x <= W:
                pts.append((x, H * rng.uniform(y_min, y_max)))
                x += rng.uniform(35, 90)
            pts += [(W, H * rng.uniform(y_min, y_max)), (W, H)]
            parts.append(_polygon(pts, _rgba(*hl, op)))

    # Urban — building skyline silhouette at the bottom
    elif tag_set & {"urban", "city"}:
        x = 0.0
        while x < W:
            bw = rng.uniform(22, 60)
            bh = rng.uniform(40, 165)
            by = H - bh
            op = rng.uniform(0.09, 0.17)
            parts.append(
                f'<rect x="{x:.0f}" y="{by:.0f}" width="{bw:.0f}" height="{bh:.0f}" '
                f'fill="{_rgba(*hl, op)}"/>'
            )
            if bh > 80:
                for wy in range(int(by) + 8, int(H) - 8, 20):
                    wx = x + rng.uniform(4, bw - 10)
                    parts.append(
                        f'<rect x="{wx:.0f}" y="{wy}" width="4" height="6" '
                        f'fill="{_rgba(*hl, 0.28)}"/>'
                    )
            x += bw + rng.uniform(2, 12)

    # Star field — camping, outdoor, desert settings
    if tag_set & {"camping", "campground", "outdoor", "desert"}:
        for _ in range(rng.randint(30, 55)):
            sx  = rng.uniform(0, W)
            sy  = rng.uniform(0, H * 0.68)
            sr  = rng.uniform(0.5, 2.2)
            op  = rng.uniform(0.12, 0.42)
            parts.append(_circle(sx, sy, sr, _rgba(*hl, op)))
        # A few slightly larger sparkles
        for _ in range(rng.randint(4, 9)):
            sx = rng.uniform(0, W)
            sy = rng.uniform(0, H * 0.5)
            parts.append(_circle(sx, sy, rng.uniform(2, 3.5), _rgba(*p1, 0.30)))

    if not parts:
        return ""
    return "<g>" + "\n".join(parts) + "</g>"


# ── SVG building blocks ───────────────────────────────────────

def _linear_grad(gid: str, x1: float, y1: float, x2: float, y2: float,
                 stops: list[tuple[float, str]]) -> str:
    stop_els = "".join(
        f'<stop offset="{p*100:.0f}%" stop-color="{c}"/>'
        for p, c in stops
    )
    return (f'<linearGradient id="{gid}" x1="{x1:.3f}" y1="{y1:.3f}" '
            f'x2="{x2:.3f}" y2="{y2:.3f}" gradientUnits="userSpaceOnUse">'
            + stop_els + "</linearGradient>")


def _radial_grad(gid: str, cx: float, cy: float, r: float,
                 stops: list[tuple[float, str, float]]) -> str:
    stop_els = "".join(
        f'<stop offset="{p*100:.0f}%" stop-color="{c}" stop-opacity="{a:.3f}"/>'
        for p, c, a in stops
    )
    return (f'<radialGradient id="{gid}" cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
            f'gradientUnits="userSpaceOnUse">' + stop_els + "</radialGradient>")


def _polygon(pts: list[tuple[float, float]], fill: str) -> str:
    point_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<polygon points="{point_str}" fill="{fill}"/>'


def _circle(cx: float, cy: float, r: float, fill: str, stroke: str = "none",
            stroke_width: float = 1.0) -> str:
    s = f' stroke="{stroke}" stroke-width="{stroke_width:.1f}"' if stroke != "none" else ""
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"{s}/>'


def _ellipse(cx: float, cy: float, rx: float, ry: float, fill: str, rot: float = 0) -> str:
    t = f' transform="rotate({rot:.1f} {cx:.1f} {cy:.1f})"' if rot else ""
    return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}"{t}/>'


def _wrap_svg(*layers: str, defs: str = "") -> str:
    inner = "\n".join(layers)
    defs_block = f"<defs>{defs}</defs>\n" if defs else ""
    return (
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
        f'preserveAspectRatio="xMidYMid slice" '
        f'style="display:block;width:100%;height:100%">\n'
        + defs_block + inner + "\n</svg>"
    )


# ── Motif renderers ───────────────────────────────────────────

def _render_radial(pal: dict, rng: _stdlib_random.Random) -> str:
    """Radial light-burst with concentric rings. Best for EDM / electronic."""
    bg, bg2, p1, p2, p3, hl = pal["bg"], pal["bg2"], pal["p1"], pal["p2"], pal["p3"], pal["hl"]

    fx = rng.uniform(W * 0.30, W * 0.70)
    fy = rng.uniform(H * 0.30, H * 0.70)
    n_rays = rng.randint(18, 28)
    angle_offset = rng.uniform(0, math.pi)

    defs = _linear_grad("bgR", 0, 0, W, H, [(0.0, _hex(*bg)), (1.0, _hex(*bg2))])
    defs += _radial_grad("glowG", fx, fy, H * 0.85,
                         [(0.0, _hex(*p1), 0.60), (0.45, _hex(*p2), 0.18), (1.0, _hex(*bg), 0.0)])

    parts: list[str] = [
        f'<rect width="{W}" height="{H}" fill="url(#bgR)"/>',
        f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="{H*0.85:.0f}" fill="url(#glowG)"/>',
    ]

    # Rays — wider, more opaque on the coloured background
    ray_dist = math.hypot(W, H) * 1.1
    angle_step = 2 * math.pi / n_rays
    for i in range(n_rays):
        angle = angle_offset + i * angle_step
        half = rng.uniform(0.025, 0.065)
        x1 = fx + ray_dist * math.cos(angle - half)
        y1 = fy + ray_dist * math.sin(angle - half)
        x2 = fx + ray_dist * math.cos(angle + half)
        y2 = fy + ray_dist * math.sin(angle + half)
        color = p1 if i % 2 == 0 else p2
        op = rng.uniform(0.14, 0.32)
        parts.append(_polygon([(fx, fy), (x1, y1), (x2, y2)], _rgba(*color, op)))

    # Concentric rings — more visible on vivid background
    for i, radius in enumerate([65, 140, 230, 350, 490]):
        op = max(0.10, 0.42 - i * 0.06)
        color = hl if i % 3 == 0 else (p1 if i % 2 == 0 else p2)
        sw = max(0.8, 3.0 - i * 0.4)
        parts.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="{radius}" '
                     f'fill="none" stroke="{_rgba(*color, op)}" stroke-width="{sw:.1f}"/>')

    # Central bright core
    parts.append(_circle(fx, fy, 16, _rgba(*hl, 0.90)))
    parts.append(_circle(fx, fy, 6, "white"))

    return _wrap_svg(*parts, defs=defs)


def _render_shatter(pal: dict, rng: _stdlib_random.Random) -> str:
    """Angular shards / broken-glass geometry. Best for rock / metal / punk."""
    bg, bg2, p1, p2, p3, hl = pal["bg"], pal["bg2"], pal["p1"], pal["p2"], pal["p3"], pal["hl"]

    n_seeds = rng.randint(6, 10)
    seeds = [(rng.uniform(W * 0.05, W * 0.95), rng.uniform(H * 0.05, H * 0.95))
             for _ in range(n_seeds)]
    corners = [(0, 0), (W, 0), (W, H), (0, H)]
    mid_edges = [
        (rng.uniform(W*0.2, W*0.8), 0),
        (W, rng.uniform(H*0.2, H*0.8)),
        (rng.uniform(W*0.2, W*0.8), H),
        (0, rng.uniform(H*0.2, H*0.8)),
    ]
    all_pts = seeds + corners + mid_edges

    defs = _linear_grad("bgS", 0, H, W, 0, [(0.0, _hex(*bg)), (1.0, _hex(*bg2))])
    parts: list[str] = [f'<rect width="{W}" height="{H}" fill="url(#bgS)"/>']

    colors = [p1, p2, p3, p2, p1, hl, p3, p1, p2]
    for idx, (sx, sy) in enumerate(seeds):
        others = sorted(all_pts, key=lambda p: math.hypot(p[0]-sx, p[1]-sy))
        # 2 nearby triangles per seed for denser fill
        for k in range(1, min(4, len(others) - 1)):
            a, b = others[k], others[k + 1]
            color = colors[(idx * 2 + k) % len(colors)]
            op = rng.uniform(0.22, 0.52)
            parts.append(_polygon([(sx, sy), a, b], _rgba(*color, op)))

    # Bold diagonal lines for texture
    for _ in range(rng.randint(5, 9)):
        x1, y1 = rng.uniform(0, W), rng.uniform(0, H)
        x2, y2 = rng.uniform(0, W), rng.uniform(0, H)
        color = rng.choice([p1, p2, hl])
        op = rng.uniform(0.22, 0.50)
        sw = rng.uniform(0.6, 2.5)
        parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                     f'stroke="{_rgba(*color, op)}" stroke-width="{sw:.1f}"/>')

    # Bright accent cross-slash
    ex = rng.uniform(W * 0.25, W * 0.75)
    parts.append(f'<line x1="{ex:.0f}" y1="0" x2="{W-ex:.0f}" y2="{H}" '
                 f'stroke="{_rgba(*hl, 0.55)}" stroke-width="1.5"/>')

    return _wrap_svg(*parts, defs=defs)


def _render_wave(pal: dict, rng: _stdlib_random.Random) -> str:
    """Stacked sinusoidal bands. Best for folk / jazz / blues / country."""
    bg, bg2, p1, p2, p3, hl = pal["bg"], pal["bg2"], pal["p1"], pal["p2"], pal["p3"], pal["hl"]

    defs = _linear_grad("bgW", 0, 0, 0, H, [(0.0, _hex(*bg2)), (1.0, _hex(*bg))])
    parts: list[str] = [f'<rect width="{W}" height="{H}" fill="url(#bgW)"/>']

    n_bands = rng.randint(5, 8)
    band_colors = [p1, p2, p3, p2, hl, p1, p3, p2]

    for i in range(n_bands):
        base_y = H * (0.10 + i * 0.85 / n_bands)
        amp    = rng.uniform(H * 0.05, H * 0.14)
        freq   = rng.uniform(1.0, 2.5)
        phase  = rng.uniform(0, 2 * math.pi)
        n_pts  = 160

        top_pts = [
            (x * W / n_pts,
             base_y + amp * math.sin(freq * 2 * math.pi * x / n_pts + phase))
            for x in range(n_pts + 1)
        ]

        thickness = rng.uniform(H * 0.07, H * 0.22)
        bottom_y  = base_y + thickness

        d = f"M 0,{bottom_y:.1f} "
        d += f"L {top_pts[0][0]:.1f},{top_pts[0][1]:.1f} "
        for j in range(1, len(top_pts), 3):
            x, y = top_pts[j]
            d += f"L {x:.1f},{y:.1f} "
        d += f"L {W},{bottom_y:.1f} Z"

        color = band_colors[i % len(band_colors)]
        op = rng.uniform(0.18, 0.42)
        parts.append(f'<path d="{d}" fill="{_rgba(*color, op)}"/>')

        stroke_d = f"M {top_pts[0][0]:.1f},{top_pts[0][1]:.1f} "
        for j in range(1, len(top_pts), 2):
            stroke_d += f"L {top_pts[j][0]:.1f},{top_pts[j][1]:.1f} "
        sw = rng.uniform(1.0, 2.5)
        parts.append(f'<path d="{stroke_d}" fill="none" '
                     f'stroke="{_rgba(*color, min(op * 2.0, 0.70))}" stroke-width="{sw:.1f}"/>')

    return _wrap_svg(*parts, defs=defs)


def _render_blocks(pal: dict, rng: _stdlib_random.Random) -> str:
    """Bold diagonal stripes + rectangular block accents. Best for hip-hop / urban."""
    bg, bg2, p1, p2, p3, hl = pal["bg"], pal["bg2"], pal["p1"], pal["p2"], pal["p3"], pal["hl"]

    defs = _linear_grad("bgB", 0, 0, W, H, [(0.0, _hex(*bg2)), (1.0, _hex(*bg))])
    parts: list[str] = [f'<rect width="{W}" height="{H}" fill="url(#bgB)"/>']

    # Large bold diagonal stripes — more opaque on vivid background
    n_stripes = rng.randint(6, 10)
    stripe_spacing = (W + H) / n_stripes
    for i in range(-1, n_stripes + 1):
        off = i * stripe_spacing
        x1, y1 = off, 0
        x2, y2 = off + H, H
        w = rng.uniform(stripe_spacing * 0.10, stripe_spacing * 0.28)
        pts = [(x1, y1), (x1 + w, y1), (x2 + w, y2), (x2, y2)]
        color = p1 if i % 2 == 0 else p2
        op = rng.uniform(0.12, 0.28)
        parts.append(_polygon(pts, _rgba(*color, op)))

    # Accent rectangles — bolder
    n_rects = rng.randint(5, 8)
    for i in range(n_rects):
        rx = rng.uniform(W * 0.03, W * 0.82)
        ry = rng.uniform(H * 0.05, H * 0.72)
        rw = rng.uniform(W * 0.06, W * 0.22)
        rh = rng.uniform(H * 0.06, H * 0.40)
        color = rng.choice([p1, p2, p3, hl])
        op = rng.uniform(0.22, 0.48)
        rot = rng.uniform(-10, 10)
        cx, cy = rx + rw / 2, ry + rh / 2
        parts.append(
            f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" '
            f'fill="{_rgba(*color, op)}" transform="rotate({rot:.1f} {cx:.1f} {cy:.1f})"/>'
        )

    # Horizontal accent lines
    for _ in range(rng.randint(3, 6)):
        y = rng.uniform(H * 0.1, H * 0.9)
        x_off = rng.uniform(0, W * 0.25)
        parts.append(
            f'<line x1="{x_off:.0f}" y1="{y:.1f}" x2="{W - x_off:.0f}" y2="{y:.1f}" '
            f'stroke="{_rgba(*hl, 0.45)}" stroke-width="{rng.uniform(0.8, 2.0):.1f}"/>'
        )

    return _wrap_svg(*parts, defs=defs)


def _render_bloom(pal: dict, rng: _stdlib_random.Random) -> str:
    """Overlapping glowing circles. Best for indie / any genre."""
    bg, bg2, p1, p2, p3, hl = pal["bg"], pal["bg2"], pal["p1"], pal["p2"], pal["p3"], pal["hl"]

    n_orbs = rng.randint(7, 12)
    orb_colors = [p1, p2, p3, p2, p1, p3, hl, p1, p2, p3, p2, p1]

    defs = _linear_grad("bgBl", 0, 0, W, H, [(0.0, _hex(*bg)), (1.0, _hex(*bg2))])
    parts: list[str] = [f'<rect width="{W}" height="{H}" fill="url(#bgBl)"/>']

    for i in range(n_orbs):
        cx = rng.uniform(-W * 0.05, W * 1.05)
        cy = rng.uniform(-H * 0.05, H * 1.05)
        r  = rng.uniform(H * 0.18, H * 0.62)
        color = orb_colors[i % len(orb_colors)]
        op = rng.uniform(0.18, 0.42)
        parts.append(_circle(cx, cy, r, _rgba(*color, op)))
        inner_r = r * rng.uniform(0.30, 0.55)
        parts.append(_circle(cx, cy, inner_r, _rgba(*color, op * 0.6)))

    # Bright highlight dots
    for _ in range(rng.randint(15, 30)):
        dx = rng.uniform(0, W)
        dy = rng.uniform(0, H)
        dr = rng.uniform(1.5, 5)
        parts.append(_circle(dx, dy, dr, _rgba(*hl, rng.uniform(0.35, 0.75))))

    return _wrap_svg(*parts, defs=defs)


def _render_prism(pal: dict, rng: _stdlib_random.Random) -> str:
    """Overlapping ellipses — aurora / kaleidoscope effect. Multi-genre default."""
    bg, bg2, p1, p2, p3, hl = pal["bg"], pal["bg2"], pal["p1"], pal["p2"], pal["p3"], pal["hl"]

    defs = _linear_grad("bgPr", 0, 0, W, H, [(0.0, _hex(*bg)), (1.0, _hex(*bg2))])
    parts: list[str] = [f'<rect width="{W}" height="{H}" fill="url(#bgPr)"/>']

    ellipse_colors = [p1, p2, p3, p2, p1, hl, p3, p2, p1, p2]
    n_ellipses = rng.randint(7, 12)

    for i in range(n_ellipses):
        cx = rng.uniform(-W * 0.15, W * 1.15)
        cy = rng.uniform(-H * 0.15, H * 1.15)
        rx = rng.uniform(W * 0.25, W * 0.72)
        ry = rng.uniform(H * 0.20, H * 0.68)
        rot = rng.uniform(-65, 65)
        color = ellipse_colors[i % len(ellipse_colors)]
        op = rng.uniform(0.16, 0.36)
        parts.append(_ellipse(cx, cy, rx, ry, _rgba(*color, op), rot))

    # Glowing focal point
    cx, cy = W * rng.uniform(0.3, 0.7), H * rng.uniform(0.3, 0.7)
    parts.append(_circle(cx, cy, H * 0.38, _rgba(*p1, 0.12)))
    parts.append(_circle(cx, cy, H * 0.18, _rgba(*p1, 0.18)))
    parts.append(_circle(cx, cy, H * 0.07, _rgba(*hl, 0.35)))

    return _wrap_svg(*parts, defs=defs)


# ── Main generator ────────────────────────────────────────────

_MOTIF_RENDERERS = {
    "radial":  _render_radial,
    "shatter": _render_shatter,
    "wave":    _render_wave,
    "blocks":  _render_blocks,
    "bloom":   _render_bloom,
    "prism":   _render_prism,
}


def generate_festival_svg(festival: dict) -> str:
    """
    Entry point — returns a complete SVG string for a given festival dict.
    Deterministic: same festival slug always produces the same art.
    Palette is adjusted for season + region; setting overlay is composited on top.
    """
    slug   = festival.get("slug", "festival")
    accent = festival.get("accent_color") or "#FF4500"
    tags   = festival.get("tags") or []

    seed = int(hashlib.sha256(slug.encode()).hexdigest()[:8], 16)
    rng  = _stdlib_random.Random(seed)

    palette  = _build_palette(accent, rng)
    palette  = _apply_season(palette, tags)
    motif    = _choose_motif(tags)
    svg      = _MOTIF_RENDERERS[motif](palette, rng)
    overlay  = _setting_overlay(tags, palette, rng)

    if overlay:
        svg = svg.replace("</svg>", overlay + "\n</svg>")

    return svg


# ── Pipeline helpers ──────────────────────────────────────────

def get_supabase() -> Client:
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def process_festival(
    supabase: Client | None,
    festival: dict,
    force: bool,
    preview: bool,
    output_dir: Path | None,
) -> None:
    name = festival["name"]
    slug = festival["slug"]

    if not force and festival.get("vector_art"):
        console.log(f"[dim]{name}: already has art — skipping (--force to regenerate)")
        return

    svg = generate_festival_svg(festival)

    motif  = _choose_motif(festival.get("tags") or [])
    accent = festival.get("accent_color") or "?"
    console.log(f"[green]{name}  [dim]{motif} · {accent}")

    if preview:
        print(svg[:600] + "…\n")
        return

    if output_dir:
        path = output_dir / f"{slug}.svg"
        path.write_text(svg, encoding="utf-8")
        console.log(f"  [dim]Saved → {path}")
        return

    try:
        supabase.table("festivals").update({"vector_art": svg}).eq("id", festival["id"]).execute()
    except Exception as e:
        log.error(f"DB write failed for {name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Generate algorithmic SVG art for festivals (no API key needed)")
    parser.add_argument("--festival",    type=str,  help="Festival slug to process")
    parser.add_argument("--force",       action="store_true", help="Regenerate even if art already exists")
    parser.add_argument("--preview",     action="store_true", help="Print SVG to stdout, skip DB")
    parser.add_argument("--output-dir",  type=str,  help="Save .svg files to this directory instead of DB")
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    supabase = None if (args.preview or out_dir) else get_supabase()

    if args.festival:
        if supabase:
            result = supabase.table("festivals").select("*").eq("slug", args.festival).execute()
            festivals = result.data
        else:
            # Minimal stub for preview/output-dir mode without a DB connection
            festivals = [{"id": "", "slug": args.festival, "name": args.festival,
                          "accent_color": "#FF4500", "tags": []}]
    else:
        query = supabase.table("festivals").select("*").eq("is_active", True).order("name")
        if not args.force:
            query = query.is_("vector_art", "null")
        festivals = query.execute().data

    if not festivals:
        console.log("[yellow]No festivals to process.")
        return

    console.log(f"[bold]Festival Art Generator (algorithmic) — {len(festivals)} festivals")

    for festival in track(festivals, description="Generating..."):
        process_festival(supabase, festival, args.force, args.preview, out_dir)
        time.sleep(0.01)  # tiny yield so the progress bar renders

    console.log("[bold green]Done.")


if __name__ == "__main__":
    main()
