"""Write the animated README banner, docs/assets/blagden-hero.svg.

The core temperature curve is the ECTemp estimate for the synthetic 4-hour
trace used by the golden fixtures (no real run). The SVG animates with SMIL
only, because GitHub renders README images without scripts.

    uv run python scripts/make_readme_banner.py
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from blagden.physio.ectemp import estimate_core_temp
from make_golden import marathon_trace

OUT = Path(__file__).resolve().parent.parent / "docs" / "assets" / "blagden-hero.svg"

W, H = 1200, 420
DUR = 12.0  # seconds per loop
DRAW = 0.82  # share of the loop spent drawing the curve
FRAMES = 24  # readout steps

# Chart frame (right side).
CX0, CX1, CY0, CY1 = 650, 1150, 92, 300
T_MIN, T_MAX = 36.8, 39.8

NAVY, PANEL, INK, MUTED = "#0c1018", "#141a25", "#ece6dc", "#b4ada3"
COOL, WARM, HOT = "#8fb3dd", "#f0b35e", "#f2836f"
SERIF = "Newsreader, Georgia, 'Times New Roman', serif"
SANS = "Inter, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"


def cx(i: int, n: int) -> float:
    return CX0 + (CX1 - CX0) * i / (n - 1)


def cy(t: float) -> float:
    return CY1 - (CY1 - CY0) * (t - T_MIN) / (T_MAX - T_MIN)


def kt(*v: float) -> str:
    return ";".join(f"{x:.4f}" for x in v)


def stepped(texts: list[str], x: float, y: float, style: str) -> str:
    """Show one text per frame while the curve draws, then hold the last."""
    out = []
    n = len(texts)
    for i, s in enumerate(texts):
        a = DRAW * i / n
        b = DRAW * (i + 1) / n
        if i == n - 1:
            values, times = "0;1;0", kt(0, a, 1 - 1e-4)
        else:
            values, times = "0;1;0", kt(0, a, b)
        if i == 0:
            values, times = "1;0", kt(0, b)
        out.append(
            f'<text x="{x}" y="{y}" {style} opacity="{1 if i == 0 else 0}">{s}'
            f'<animate attributeName="opacity" values="{values}" keyTimes="{times}" '
            f'calcMode="discrete" dur="{DUR}s" repeatCount="indefinite"/></text>'
        )
    return "\n".join(out)


STRIDE = 0.64  # seconds per running stride
SKIN, SKIN_BACK = "#c08457", "#7d5537"
SINGLET, SINGLET_BACK = "#e0794f", "#9a4c30"
SHORTS = "#1d2a40"
SHOE, SHOE_BACK = "#ece6dc", "#8e8a83"


def anim_rotate(values: str, times: str, delay: float) -> str:
    return (
        f'<animateTransform attributeName="transform" type="rotate" values="{values}" '
        f'keyTimes="{times}" calcMode="spline" '
        f'keySplines="{";".join(["0.45 0 0.55 1"] * (len(times.split(";")) - 1))}" '
        f'dur="{STRIDE}s" begin="{delay}s" repeatCount="indefinite"/>'
    )


def segment(length: float, w0: float, w1: float, color: str) -> str:
    """Draw a tapered limb segment hanging down from the origin."""
    return (
        f'<path d="M{-w0 / 2:.1f} 0 L{w0 / 2:.1f} 0 L{w1 / 2:.1f} {length} '
        f'L{-w1 / 2:.1f} {length} Z" fill="{color}"/>'
        f'<circle r="{w0 / 2:.1f}" fill="{color}"/>'
        f'<circle cy="{length}" r="{w1 / 2:.1f}" fill="{color}"/>'
    )


def leg(x: float, y: float, delay: float, skin: str, shoe: str) -> str:
    """Draw a leg: thigh swings at the hip, shin folds back at the knee, shoe at the foot."""
    thigh = anim_rotate("-34;30;-34", "0;0.5;1", delay)
    shin = anim_rotate("6;12;100;24;6", "0;0.45;0.68;0.88;1", delay)
    return f"""<g transform="translate({x} {y})"><g>{thigh}
  <path d="M-9 -2 L9 -2 L8 16 L-8 16 Z" fill="{SHORTS}"/>
  {segment(40, 17, 12, skin)}
  <g transform="translate(0 40)"><g>{shin}
    {segment(38, 12, 8, skin)}
    <rect x="-6" y="34" width="20" height="8" rx="4" fill="{shoe}"/>
  </g></g>
</g></g>"""


def arm(x: float, y: float, delay: float, skin: str) -> str:
    """Draw an arm: upper arm swings at the shoulder, forearm held bent forward."""
    upper = anim_rotate("32;-36;32", "0;0.5;1", delay)
    fore = anim_rotate("-78;-100;-78", "0;0.5;1", delay)
    return f"""<g transform="translate({x} {y})"><g>{upper}
  {segment(26, 11, 9, skin)}
  <g transform="translate(0 26)"><g>{fore}
    {segment(24, 9, 7, skin)}
    <circle cy="25" r="5" fill="{skin}"/>
  </g></g>
</g></g>"""


def runner(x: float, y: float) -> str:
    """Draw a runner with body mass whose hip sits at (x, y), facing right."""
    half = -STRIDE / 2
    sx, sy = x + 9, y - 52  # shoulder
    torso = (
        f'<path d="M{x - 11} {y + 4} C{x - 14} {y - 20} {x - 6} {y - 50} {x + 3} {y - 58} '
        f'L{x + 19} {y - 56} C{x + 20} {y - 40} {x + 16} {y - 16} {x + 11} {y + 4} Z" '
        f'fill="{SINGLET}"/>'
    )
    trim = (
        f'<path d="M{x - 11} {y - 6} L{x + 12} {y - 6}" stroke="{SINGLET_BACK}" stroke-width="2"/>'
    )
    head = f"""<g transform="translate({x + 15} {y - 74})">
  <rect x="-5" y="6" width="10" height="10" rx="3" fill="{SKIN}"/>
  <ellipse cx="2" cy="0" rx="12" ry="13" fill="{SKIN}"/>
  <path d="M-11 -2 C-11 -14 4 -18 13 -8 L13 -4 C6 -6 -2 -6 -11 -2 Z" fill="#1a1410"/>
  <path d="M-12 -4 L14 -7" stroke="{WARM}" stroke-width="3" stroke-linecap="round"/>
</g>"""
    return f"""<g>
  <animateTransform attributeName="transform" type="translate"
    values="0 0;0 -6;0 0;0 -6;0 0" keyTimes="0;0.25;0.5;0.75;1"
    dur="{STRIDE}s" repeatCount="indefinite"/>
  <ellipse cx="{x + 2}" cy="342" rx="34" ry="4" fill="#000" opacity="0.35"/>
  <g transform="rotate(8 {x} {y})">
    {arm(sx, sy, 0, SKIN_BACK)}
    {leg(x, y, half, SKIN_BACK, SHOE_BACK)}
    {torso}{trim}
    <path d="M{x - 12} {y - 4} L{x + 12} {y - 4} L{x + 13} {y + 12} L{x - 13} {y + 12} Z"
      fill="{SHORTS}"/>
    {leg(x, y, 0, SKIN, SHOE)}
    {head}
    {arm(sx, sy, half, SKIN)}
  </g>
</g>"""


def building(
    rng: random.Random, x: float, w: float, h: float, base: float, fill: str, lit: float
) -> str:
    """Draw one building: a body with an optional setback, crown or spire, and windows."""
    top = base - h
    parts = [f'<rect x="{x:.0f}" y="{top:.0f}" width="{w:.0f}" height="{h:.0f}"/>']
    kind = rng.random()
    if kind < 0.3:  # setback tier
        tw = w * rng.uniform(0.5, 0.7)
        th = rng.uniform(12, 26)
        parts.append(
            f'<rect x="{x + (w - tw) / 2:.0f}" y="{top - th:.0f}" width="{tw:.0f}" '
            f'height="{th:.0f}"/>'
        )
        top -= th
    elif kind < 0.5:  # spire with antenna
        parts.append(
            f'<path d="M{x + w * 0.2:.0f} {top:.0f} L{x + w / 2:.0f} {top - 22:.0f} '
            f'L{x + w * 0.8:.0f} {top:.0f} Z"/>'
        )
        parts.append(f'<rect x="{x + w / 2 - 1:.0f}" y="{top - 40:.0f}" width="2" height="20"/>')
    elif kind < 0.65:  # slanted crown
        parts.append(
            f'<path d="M{x:.0f} {top:.0f} L{x + w:.0f} {top - 16:.0f} L{x + w:.0f} {top:.0f} Z"/>'
        )
    elif kind < 0.8:  # rooftop water tank and mast
        parts.append(
            f'<rect x="{x + w * 0.15:.0f}" y="{top - 8:.0f}" width="10" height="8"/>'
            f'<rect x="{x + w * 0.7:.0f}" y="{top - 18:.0f}" width="2" height="18"/>'
        )
    body = "".join(parts)
    windows = []
    if lit > 0:
        for wy in range(int(base - h + 8), int(base - 6), 9):
            for wx in range(int(x + 5), int(x + w - 6), 7):
                if rng.random() < lit:
                    op = rng.uniform(0.35, 0.85)
                    windows.append(
                        f'<rect x="{wx}" y="{wy}" width="3" height="4" '
                        f'fill="#f4c27a" opacity="{op:.2f}"/>'
                    )
    return f'<g fill="{fill}">{body}</g>' + "".join(windows)


def city_tile(seed: int, fill: str, hmin: float, hmax: float, lit: float) -> str:
    """One 600 px wide strip of buildings."""
    rng = random.Random(seed)
    out, x = [], 0.0
    while x < 600:
        w = min(rng.uniform(26, 58), 600 - x)
        if w < 10:
            break
        out.append(building(rng, x, w, rng.uniform(hmin, hmax), 340, fill, lit))
        x += w + rng.choice([0, 0, 2, 4])
    return "".join(out)


def palm(x: float, h: float) -> str:
    """Draw a palm tree silhouette rooted at ground level."""
    top_x, top_y = x + 10, 340 - h
    fronds = "".join(
        f'<path d="M{top_x} {top_y} q{dx * 0.5:.0f} {-18 + dy:.0f} {dx} {dy + 6:.0f}" '
        f'stroke="#0a0e15" stroke-width="5" fill="none" stroke-linecap="round"/>'
        for dx, dy in [(-40, 10), (-30, 22), (38, 12), (30, 24), (-10, 26), (14, -4), (-20, -2)]
    )
    trunk = (
        f'<path d="M{x} 340 C{x + 2} {340 - h / 2} {x + 8} {top_y + 20} {top_x} {top_y}" '
        f'stroke="#0a0e15" stroke-width="6" fill="none" stroke-linecap="round"/>'
    )
    return trunk + fronds


def scroller(content: str, dur: float) -> str:
    """Repeat a 600 px tile three times and scroll it left forever."""
    return f"""<g>
  <animateTransform attributeName="transform" type="translate" values="0 0;-600 0"
    dur="{dur}s" repeatCount="indefinite"/>
  <g>{content}</g><g transform="translate(600 0)">{content}</g>
  <g transform="translate(1200 0)">{content}</g>
</g>"""


def skyline() -> str:
    """Draw a far hazy skyline and a near lit skyline, scrolling at different speeds."""
    far = city_tile(3, "#222c42", 50, 140, 0.0)
    near = city_tile(11, "#141b28", 30, 105, 0.16)
    palms = palm(70, 92) + palm(330, 78) + palm(470, 100)
    return scroller(far, 40) + scroller(near, 18) + scroller(palms, 7)


def heartbeat() -> str:
    """Draw a pulse trace that scrolls under the runner."""
    seg = "l30 0 l6 -14 l6 26 l6 -40 l6 34 l6 -6 l30 0"
    path = "M0 382 " + " ".join([seg] * 16)
    return f"""<g clip-path="url(#left)">
  <path d="{path}" fill="none" stroke="{HOT}" stroke-width="2" stroke-opacity="0.85">
    <animateTransform attributeName="transform" type="translate" values="0 0;-90 0"
      dur="0.75s" repeatCount="indefinite"/>
  </path>
</g>"""


def chart(tc: list[float], hr: list[float | None]) -> str:
    n = len(tc)
    d = "M" + " L".join(f"{cx(i, n):.1f},{cy(t):.1f}" for i, t in enumerate(tc))
    grid = "".join(
        f'<line x1="{CX0}" x2="{CX1}" y1="{cy(t):.1f}" y2="{cy(t):.1f}" stroke="{INK}" '
        f'stroke-opacity="0.08"/>'
        f'<text x="{CX0 - 10}" y="{cy(t) + 4:.1f}" fill="{MUTED}" font-family="{SANS}" '
        f'font-size="12" text-anchor="end">{t:.1f}</text>'
        for t in (37.0, 37.5, 38.0, 38.5, 39.0, 39.5)
    )
    y39 = cy(39.0)
    idx = [min(n - 1, round((n - 1) * (k + 1) / FRAMES)) for k in range(FRAMES)]
    minutes = [f"{i + 1} min" for i in idx]
    temps = [f"{tc[i]:.2f} C" for i in idx]
    beats = []
    for i in idx:
        v = hr[i]
        j = i
        while v is None or (isinstance(v, float) and math.isnan(v)):
            j -= 1
            v = hr[j]
        beats.append(f"{v:.0f} bpm")
    label = f'font-family="{SANS}" font-size="13" fill="{MUTED}"'
    value = f'font-family="{SERIF}" font-size="30" fill="{INK}"'
    times = kt(0, DRAW, 1)
    return f"""<rect x="{CX0 - 46}" y="{CY0 - 50}" width="{CX1 - CX0 + 76}"
  height="{CY1 - CY0 + 150}" rx="18" fill="{PANEL}" stroke="#2b3240"/>
<text x="{CX0 - 22}" y="{CY0 - 22}" font-family="{SANS}" font-size="12" letter-spacing="2.4"
  fill="{WARM}" font-weight="600">ESTIMATED CORE TEMPERATURE · SYNTHETIC 4-HOUR RUN</text>
{grid}
<rect x="{CX0}" y="{CY0}" width="{CX1 - CX0}" height="{y39 - CY0:.1f}" fill="{HOT}"
  fill-opacity="0.07"/>
<line x1="{CX0}" x2="{CX1}" y1="{y39:.1f}" y2="{y39:.1f}" stroke="{HOT}" stroke-dasharray="6 5"/>
<text x="{CX1 - 4}" y="{y39 + 18:.1f}" text-anchor="end" font-family="{SANS}" font-size="12"
  fill="{MUTED}">Less sensitive above 39.0 C</text>
<path d="{d}" fill="none" stroke="url(#heat)" stroke-width="3.5" stroke-linecap="round"
  pathLength="1" stroke-dasharray="1" stroke-dashoffset="1">
  <animate attributeName="stroke-dashoffset" values="1;0;0" keyTimes="{times}" dur="{DUR}s"
    repeatCount="indefinite"/>
</path>
<circle r="6" fill="{HOT}" stroke="{NAVY}" stroke-width="2">
  <animateMotion path="{d}" keyPoints="0;1;1" keyTimes="{times}" calcMode="linear"
    dur="{DUR}s" repeatCount="indefinite"/>
</circle>
<text x="{CX0}" y="{CY1 + 46}" {label}>time</text>
<text x="{CX0 + 170}" y="{CY1 + 46}" {label}>heart rate</text>
<text x="{CX0 + 340}" y="{CY1 + 46}" {label}>core temperature</text>
{stepped(minutes, CX0, CY1 + 82, value)}
{stepped(beats, CX0 + 170, CY1 + 82, value)}
{stepped(temps, CX0 + 340, CY1 + 82, value)}"""


def build() -> str:
    hr = marathon_trace()
    est = estimate_core_temp(hr)
    tc = [float(t) for t in est.tc_c]
    hr_clean: list[float | None] = [None if math.isnan(h) else h for h in hr]
    sky = kt(0, DRAW, 1)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"
  width="{W}" height="{H}" role="img" aria-labelledby="t d">
<title id="t">Blagden: heat intelligence for runners in the tropics</title>
<desc id="d">A runner on a Manila race morning as the sun rises. Heart rate pulses below,
and an estimated core temperature curve climbs past 39.0 C over a synthetic 4-hour run.</desc>
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{NAVY}"/>
    <stop offset="1" stop-color="#16243a">
      <animate attributeName="stop-color" values="#16243a;#6b3a22;#6b3a22" keyTimes="{sky}"
        dur="{DUR}s" repeatCount="indefinite"/>
    </stop>
  </linearGradient>
  <linearGradient id="heat" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0" stop-color="{COOL}"/><stop offset="0.5" stop-color="{WARM}"/>
    <stop offset="1" stop-color="{HOT}"/>
  </linearGradient>
  <radialGradient id="glow"><stop offset="0" stop-color="{WARM}" stop-opacity="0.55"/>
    <stop offset="1" stop-color="{WARM}" stop-opacity="0"/></radialGradient>
  <clipPath id="left"><rect x="0" y="0" width="590" height="{H}"/></clipPath>
  <clipPath id="card"><rect width="{W}" height="{H}" rx="22"/></clipPath>
</defs>
<g clip-path="url(#card)">
<rect width="{W}" height="{H}" fill="url(#sky)"/>
<g clip-path="url(#left)">
  <g>
    <animateTransform attributeName="transform" type="translate" values="0 0;0 -210;0 -210"
      keyTimes="{sky}" dur="{DUR}s" repeatCount="indefinite"/>
    <circle cx="470" cy="360" r="110" fill="url(#glow)"/>
    <circle cx="470" cy="360" r="34" fill="{HOT}">
      <animate attributeName="fill" values="{HOT};{WARM};{WARM}" keyTimes="{sky}"
        dur="{DUR}s" repeatCount="indefinite"/>
    </circle>
  </g>
  {skyline()}
  <rect x="0" y="340" width="600" height="80" fill="{NAVY}"/>
  <line x1="0" x2="600" y1="341" y2="341" stroke="#3a4558" stroke-width="2"
    stroke-dasharray="40 30">
    <animate attributeName="stroke-dashoffset" values="0;70" dur="0.5s" repeatCount="indefinite"/>
  </line>
  {runner(250, 262)}
</g>
{heartbeat()}
<text x="48" y="78" font-family="{SERIF}" font-size="46" fill="{INK}">Blagden</text>
<text x="48" y="110" font-family="{SANS}" font-size="17" fill="{MUTED}">Heat intelligence for
  runners in the tropics.</text>
<text x="48" y="140" font-family="{SANS}" font-size="14" fill="{WARM}">Heart rate in. Core
  temperature, race-morning WBGT and a pace plan out.</text>
{chart(tc, hr_clean)}
</g>
</svg>
"""


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(OUT.parent.parent.parent)}")
