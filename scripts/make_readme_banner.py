"""Write the animated README banner, docs/assets/blagden-hero.svg.

The core temperature curve is the ECTemp estimate for the synthetic 4-hour
trace used by the golden fixtures (no real run). The SVG animates with SMIL
only, because GitHub renders README images without scripts.

    uv run python scripts/make_readme_banner.py
"""

from __future__ import annotations

import math
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


def limb(
    x: float,
    y: float,
    upper: float,
    lower: float,
    swing: str,
    bend: str,
    delay: float,
    width: float,
    color: str,
) -> str:
    """One leg or arm: a segment that swings, with a second that bends at its end."""
    return f"""<g transform="translate({x} {y})">
  <g>
    <animateTransform attributeName="transform" type="rotate" values="{swing}"
      dur="0.6s" begin="{delay}s" repeatCount="indefinite"/>
    <line x1="0" y1="0" x2="0" y2="{upper}" stroke="{color}" stroke-width="{width}"
      stroke-linecap="round"/>
    <g transform="translate(0 {upper})">
      <g>
        <animateTransform attributeName="transform" type="rotate" values="{bend}"
          dur="0.6s" begin="{delay}s" repeatCount="indefinite"/>
        <line x1="0" y1="0" x2="0" y2="{lower}" stroke="{color}" stroke-width="{width}"
          stroke-linecap="round"/>
      </g>
    </g>
  </g>
</g>"""


def runner(x: float, y: float) -> str:
    """Draw a stick runner whose hip sits at (x, y)."""
    leg_swing, leg_bend = "-38;32;-38", "8;70;8"
    arm_swing, arm_bend = "40;-40;40", "-80;-60;-80"
    back = "#7a6a58"
    return f"""<g>
  <animateTransform attributeName="transform" type="translate" values="0 0;0 -5;0 0;0 -5;0 0"
    dur="0.6s" repeatCount="indefinite"/>
  {limb(x, y, 34, 32, leg_swing, leg_bend, -0.3, 7, back)}
  {limb(x + 9, y - 46, 22, 20, arm_swing, arm_bend, 0, 6, back)}
  <line x1="{x}" y1="{y}" x2="{x + 10}" y2="{y - 50}" stroke="{INK}" stroke-width="8"
    stroke-linecap="round"/>
  <circle cx="{x + 13}" cy="{y - 64}" r="10" fill="{INK}"/>
  {limb(x, y, 34, 32, leg_swing, leg_bend, 0, 7, INK)}
  {limb(x + 9, y - 46, 22, 20, arm_swing, arm_bend, -0.3, 6, INK)}
</g>"""


def skyline() -> str:
    """Two copies of a simple city silhouette that scroll left forever."""
    blocks = [
        (0, 40),
        (34, 70),
        (60, 52),
        (96, 96),
        (128, 60),
        (170, 120),
        (206, 74),
        (250, 54),
        (284, 104),
        (322, 66),
        (360, 88),
        (402, 48),
        (440, 112),
        (478, 70),
        (520, 58),
        (556, 92),
    ]
    rects = "".join(
        f'<rect x="{bx}" y="{340 - bh}" width="30" height="{bh}"/>' for bx, bh in blocks
    )
    tile = f'<g fill="#1b2433">{rects}</g>'
    return f"""<g>
  <animateTransform attributeName="transform" type="translate" values="0 0;-600 0"
    dur="16s" repeatCount="indefinite"/>
  <g>{tile}</g><g transform="translate(600 0)">{tile}</g><g transform="translate(1200 0)">{tile}</g>
</g>"""


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
  {runner(250, 272)}
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
