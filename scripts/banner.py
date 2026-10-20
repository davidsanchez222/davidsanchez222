"""Generate assets/banner.svg: a fastfetch-style terminal banner with an ASCII headshot.

Run from the repo root:  python3 scripts/banner.py [--photo path/to/photo.jpg]
To swap the headshot, replace assets/headshot.jpg (or pass --photo) and tune PORTRAIT below.
"""

import argparse
from pathlib import Path
from xml.sax.saxutils import escape

from portrait import braille

ROOT = Path(__file__).resolve().parent.parent
HEADSHOT = ROOT / "assets" / "headshot.jpg"
OUT = ROOT / "assets" / "banner.svg"

# catppuccin frappé
BASE = "#303446"
MANTLE = "#292c3c"
CRUST = "#232634"
SURFACE0 = "#414559"
SURFACE2 = "#626880"
OVERLAY1 = "#838ba7"
TEXT = "#c6d0f5"
SUBTEXT = "#a5adce"
RED = "#e78284"
PEACH = "#ef9f76"
YELLOW = "#e5c890"
GREEN = "#a6d189"
TEAL = "#81c8be"
SKY = "#99d1db"
BLUE = "#8caaee"
MAUVE = "#ca9ee6"
PINK = "#f4b8e4"

WIDTH, HEIGHT = 920, 490
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"

# portrait grid
COLS, ROWS = 64, 32
CELL_W, CELL_H = 5.4, 10.6
ART_X, ART_Y = 24, 96
# framing for the photo, passed to portrait.braille; see its docstring
PORTRAIT = dict(focus=(0.5, 0.45), zoom=1.0, head=(0.86, 1.0), contrast=1.6, edges=0.4)

# info panel
INFO_X, INFO_Y = 392, 116
INFO_LH = 22
VALUE_X = INFO_X + 90

PROMPT_Y = 66
USER, HOST = "david", "portfolio"

INFO = [
    ("name", "David Sanchez"),
    ("role", "aspiring inference engineer"),
    ("edu", "B.S. Computer Science @ UGA '26"),
    ("work", "project manager @ UPS Healthcare"),
    ("loc", "Atlanta, GA"),
    ("shell", "zsh · ghostty · neovim · neogit"),
    ("langs", "go rust zig python ts swift kotlin lua scala"),
    ("stack", "pytorch tf react bun node postgres docker aws"),
    ("tools", "raycast · karabiner · typst · zen"),
    ("building", "niimtui — label printing from the terminal"),
    ("web", "dsanch.com"),
]
KEY_COLORS = [MAUVE, PINK, RED, PEACH, YELLOW, GREEN, TEAL, SKY, BLUE, MAUVE, PINK]
SWATCHES = [SURFACE2, RED, GREEN, YELLOW, BLUE, PINK, TEAL, SUBTEXT]


def text(x, y, s, fill=TEXT, cls="", extra=""):
    c = f' class="{cls}"' if cls else ""
    return f'<text x="{x}" y="{y}" fill="{fill}"{c}{extra}>{escape(s)}</text>'


def prompt(y, cls=""):
    c = f' class="{cls}"' if cls else ""
    return (
        f'<text x="30" y="{y}"{c}>'
        f'<tspan fill="{GREEN}" font-weight="700">{USER}@{HOST}</tspan>'
        f'<tspan fill="{BLUE}"> ~</tspan>'
        f'<tspan fill="{MAUVE}"> ❯ </tspan></text>'
    )


def build(photo):
    art = braille(photo, COLS, ROWS, **PORTRAIT)
    out = []
    add = out.append

    cmd = "fastfetch --logo ~/headshot.jpg"
    cmd_x = 30 + 20 * 7.2  # after "david@portfolio ~ ❯ "
    cmd_w = len(cmd) * 7.2
    type_s = 1.4
    art_start = type_s + 0.3
    info_start = art_start + 0.4
    end_s = info_start + len(INFO) * 0.09 + 0.6

    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="{FONT}" font-size="12">'
    )
    add(
        f"""<style>
  text {{ white-space: pre; }}
  .in {{ animation: in .35s ease-out both; }}
  .type {{ animation: type {type_s}s steps({len(cmd) + 2}) .4s both; }}
  .blink {{ animation: blink 1s steps(1) infinite; }}
  .scan {{ animation: scan 6s linear {end_s}s infinite; }}
  @keyframes in {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes type {{ from {{ transform: translateX(-{cmd_w + 14:.1f}px); }} to {{ transform: none; }} }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}
  @keyframes scan {{ from {{ transform: translateY(0); }} to {{ transform: translateY({HEIGHT}px); }} }}
  @media (prefers-reduced-motion: reduce) {{ .in, .type, .blink, .scan {{ animation: none; }} .scan {{ display: none; }} }}
</style>"""
    )
    add(
        f"""<defs>
  <linearGradient id="art" x1="{ART_X}" y1="{ART_Y - 10}" x2="{ART_X + COLS * CELL_W}" y2="{ART_Y + ROWS * CELL_H}" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="{MAUVE}"/><stop offset=".5" stop-color="{BLUE}"/><stop offset="1" stop-color="{TEAL}"/>
  </linearGradient>
  <linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{BLUE}" stop-opacity="0"/><stop offset="1" stop-color="{BLUE}" stop-opacity=".06"/>
  </linearGradient>
  <pattern id="lines" width="4" height="3" patternUnits="userSpaceOnUse">
    <rect width="4" height="1" fill="{CRUST}" opacity=".35"/>
  </pattern>
  <clipPath id="win"><rect x="8" y="8" width="{WIDTH - 16}" height="{HEIGHT - 16}" rx="12"/></clipPath>
  <clipPath id="cmdline"><rect x="{cmd_x - 1}" y="{PROMPT_Y - 14}" width="{cmd_w + 12}" height="20"/></clipPath>
  <filter id="glow" x="-5%" y="-5%" width="110%" height="110%">
    <feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>"""
    )

    # window
    add(
        f'<rect x="8" y="10" width="{WIDTH - 16}" height="{HEIGHT - 16}" rx="12" fill="{CRUST}" opacity=".6"/>'
    )
    add(f'<g clip-path="url(#win)">')
    add(
        f'<rect x="8" y="8" width="{WIDTH - 16}" height="{HEIGHT - 16}" fill="{BASE}"/>'
    )
    add(f'<rect x="8" y="8" width="{WIDTH - 16}" height="30" fill="{MANTLE}"/>')
    for i, c in enumerate((RED, YELLOW, GREEN)):
        add(f'<circle cx="{28 + i * 20}" cy="23" r="6" fill="{c}"/>')
    add(
        text(
            WIDTH / 2,
            27,
            f"{USER}@{HOST}: ~ — ghostty",
            OVERLAY1,
            extra=' text-anchor="middle"',
        )
    )

    # typed command: a cover with the cursor on its edge slides right, out of the clip.
    # its resting position is already past the clip, so with animations off the command is just there.
    cover_x = cmd_x + cmd_w + 14
    add(prompt(PROMPT_Y))
    add(text(cmd_x, PROMPT_Y, cmd, TEXT))
    add(f'<g clip-path="url(#cmdline)"><g class="type">')
    add(
        f'<rect x="{cover_x - 1}" y="{PROMPT_Y - 14}" width="{cmd_w + 14}" height="20" fill="{BASE}"/>'
    )
    add(
        f'<rect x="{cover_x}" y="{PROMPT_Y - 11}" width="7" height="14" fill="{TEXT}"/>'
    )
    add("</g></g>")

    # portrait, rendered top to bottom like a slow print
    add(f'<g fill="url(#art)" filter="url(#glow)" font-size="10.5">')
    for i, row in enumerate(art):
        y = ART_Y + i * CELL_H
        delay = art_start + i * 0.035
        add(
            f'<text x="{ART_X}" y="{y:.1f}" class="in" style="animation-delay:{delay:.2f}s" '
            f'textLength="{COLS * CELL_W:.1f}" lengthAdjust="spacingAndGlyphs">{row}</text>'
        )
    add("</g>")

    # info panel
    def info_line(i, inner):
        delay = info_start + i * 0.09
        return f'<g class="in" style="animation-delay:{delay:.2f}s">{inner}</g>'

    y = INFO_Y
    head = (
        f'<text x="{INFO_X}" y="{y}" font-size="14" font-weight="700">'
        f'<tspan fill="{GREEN}">{USER}</tspan><tspan fill="{TEXT}">@</tspan>'
        f'<tspan fill="{BLUE}">{HOST}</tspan></text>'
    )
    add(info_line(0, head))
    y += 16
    add(info_line(0, text(INFO_X, y, "─" * 15, SURFACE2)))
    y += INFO_LH
    for i, ((k, v), kc) in enumerate(zip(INFO, KEY_COLORS)):
        inner = text(INFO_X, y, k, kc, extra=' font-weight="700"') + text(
            VALUE_X, y, v, TEXT
        )
        if k == "web":
            inner = f'<a href="https://dsanch.com">{inner}</a>'
        add(info_line(i + 1, inner))
        y += INFO_LH

    y += 2
    sw = "".join(
        f'<rect x="{INFO_X + i * 30}" y="{y - 12}" width="26" height="14" rx="2" fill="{c}"/>'
        for i, c in enumerate(SWATCHES)
    )
    add(info_line(len(INFO) + 1, sw))

    # trailing prompt with a blinking cursor
    py = HEIGHT - 34
    add(f'<g class="in" style="animation-delay:{end_s:.2f}s">')
    add(prompt(py))
    add(
        f'<rect class="blink" x="{30 + 20 * 7.2}" y="{py - 11}" width="7" height="14" fill="{TEXT}"/>'
    )
    add(
        text(
            WIDTH - 30,
            py,
            "# psst: try `man david` at dsanch.com",
            SURFACE2,
            extra=' text-anchor="end"',
        )
    )
    add("</g>")

    # crt dressing
    add(
        f'<rect x="8" y="38" width="{WIDTH - 16}" height="{HEIGHT - 46}" fill="url(#lines)" pointer-events="none"/>'
    )
    add(
        f'<rect class="scan" x="8" y="-60" width="{WIDTH - 16}" height="60" fill="url(#beam)" pointer-events="none"/>'
    )
    add("</g>")
    add(
        f'<rect x="8.5" y="8.5" width="{WIDTH - 17}" height="{HEIGHT - 17}" rx="12" fill="none" stroke="{SURFACE0}"/>'
    )
    add("</svg>")

    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--photo", type=Path, default=HEADSHOT, help="image to draw as the portrait"
    )
    build(parser.parse_args().photo)
