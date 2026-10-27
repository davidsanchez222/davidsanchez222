"""Generate assets/banner.svg: the whole banner drawn as a terminal screen on one character grid.

Run from the repo root:  python3 scripts/banner.py [--photo path/to/photo.jpg]
To swap the headshot, replace assets/headshot.jpg (or pass --photo) and tune PORTRAIT below.
The photo is gitignored: rendering it caches the braille in assets/portrait.txt, which is committed,
so CI (and anyone without the photo) rebuilds from the cache.
The open source pane is read from the README's CONTRIB block; the nightly workflow regenerates it.
"""

import argparse
import math
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from portrait import braille

ROOT = Path(__file__).resolve().parent.parent
HEADSHOT = ROOT / "assets" / "headshot.jpg"
PORTRAIT_CACHE = ROOT / "assets" / "portrait.txt"
README = ROOT / "README.md"
OUT = ROOT / "assets" / "banner.svg"

# catppuccin frappé
BASE = "#303446"
CRUST = "#232634"
SURFACE0 = "#414559"
SURFACE1 = "#51576d"
SURFACE2 = "#626880"
OVERLAY1 = "#838ba7"
TEXT = "#c6d0f5"
SUBTEXT = "#a5adce"
RED = "#e78284"
MAROON = "#ea999c"
PEACH = "#ef9f76"
YELLOW = "#e5c890"
GREEN = "#a6d189"
TEAL = "#81c8be"
SKY = "#99d1db"
SAPPHIRE = "#85c1dc"
BLUE = "#8caaee"
LAVENDER = "#babbf1"
MAUVE = "#ca9ee6"
PINK = "#f4b8e4"
RAINBOW = [MAUVE, PINK, MAROON, PEACH, YELLOW, GREEN, TEAL, SKY, SAPPHIRE, BLUE, LAVENDER]

# the grid: every glyph lives in one of these cells
COLS, ROWS = 124, 36
CW, CH = 7.2, 14  # cell size in px
BASELINE = CH * 0.78
PAD = 14
WIDTH, HEIGHT = round(COLS * CW + PAD * 2), round(ROWS * CH + PAD * 2)
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
FONT_SIZE = 12.5

# framing for the photo, passed to portrait.braille; see its docstring
PORTRAIT = dict(focus=(0.46, 0.50), zoom=0.46, head=(0.8, 1.0), contrast=1.5, edges=0.3, flatten=0.3)
ART_COLS, ART_ROWS = 44, 22

USER, HOST = "david", "portfolio"
NAME = "DAVID SANCHEZ"
ABOUT = [
    (MAUVE, "swe"),
    (PINK, "B.S. Computer Science @ UGA '26"),
    (PEACH, "forward deployed engineer @ UPS Healthcare"),
    (YELLOW, "Atlanta, GA"),
    (GREEN, "dsanch.com"),
]
STACK = [
    ("langs", "go rust python swift"),
    ("ml", "pytorch tensorflow pandas langchain"),
    ("data", "postgres planetscale supabase"),
    ("ops", "docker terraform/opentofu tailscale nixos"),
    ("desk", "ghostty neovim neogit raycast karabiner typst zen"),
]
NOW = [
    ("building", SKY, "niimtui: niimbot label printing from a tui"),
    ("learning", MAUVE, "llm inference, end to end"),
]

# 5-row block font for the name; '#' is ink
GLYPHS = {
    "A": [".###.", "#...#", "#####", "#...#", "#...#"],
    "C": [".####", "#....", "#....", "#....", ".####"],
    "D": ["####.", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "####.", "#....", "#####"],
    "H": ["#...#", "#...#", "#####", "#...#", "#...#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#"],
    "S": [".####", "#....", ".###.", "....#", "####."],
    "V": ["#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "Z": ["#####", "...#.", "..#..", ".#...", "#####"],
    " ": ["..", "..", "..", "..", ".."],
}
NAME_FILL, ART_FILL = "url(#name)", "url(#art)"


class Grid:
    def __init__(self):
        self.ch = [[" "] * COLS for _ in range(ROWS)]
        self.fg = [[TEXT] * COLS for _ in range(ROWS)]
        self.bg = [[None] * COLS for _ in range(ROWS)]

    def put(self, r, c, s, fg=TEXT, bg=None):
        """Write s at (r, c) and return the column after it."""
        for i, ch in enumerate(s):
            if 0 <= c + i < COLS:
                self.ch[r][c + i] = ch
                self.fg[r][c + i] = fg
                if bg:
                    self.bg[r][c + i] = bg
        return c + len(s)

    def fill_bg(self, r, c0, c1, bg):
        for c in range(c0, c1):
            self.bg[r][c] = bg

    def box(self, r0, c0, r1, c1, title="", color=SURFACE2, title_color=TEXT):
        self.put(r0, c0, "╭" + "─" * (c1 - c0 - 1) + "╮", color)
        self.put(r1, c0, "╰" + "─" * (c1 - c0 - 1) + "╯", color)
        for r in range(r0 + 1, r1):
            self.put(r, c0, "│", color)
            self.put(r, c1, "│", color)
        if title:
            c = self.put(r0, c0 + 2, "┤ ", color)
            c = self.put(r0, c, title, title_color)
            self.put(r0, c, " ├", color)

    def runs(self, r):
        """Same-color runs of (col, text, fg) in row r; single spaces stay inside a run, wider gaps split it."""
        out = []
        c = 0
        while c < COLS:
            if self.ch[r][c] == " ":
                c += 1
                continue
            start, fg = c, self.fg[r][c]
            while c < COLS and self.fg[r][c] == fg:
                if self.ch[r][c] == " " and (c + 1 >= COLS or self.ch[r][c + 1] == " "):
                    break
                c += 1
            out.append((start, "".join(self.ch[r][start:c]).rstrip(), fg))
        return out

    def bg_runs(self, r):
        out = []
        c = 0
        while c < COLS:
            start, bg = c, self.bg[r][c]
            while c < COLS and self.bg[r][c] == bg:
                c += 1
            if bg:
                out.append((start, c - start, bg))
        return out


def contributions():
    """[repo, stars, merged, open] for each repo in the README's CONTRIB block."""
    block = re.search(r"<!--CONTRIB BEGIN-->(.*?)<!--CONTRIB END-->", README.read_text(), re.S).group(1)
    repos = []
    for line in block.splitlines():
        if m := re.match(r"#### \[(.+?)\]\(.*?\) !\[\]\(\./assets/star\.svg\)(\d+)", line):
            repos.append([m.group(1), int(m.group(2)), 0, 0])
        elif repos and "merged.svg" in line:
            repos[-1][2] += 1
        elif repos and "open.svg" in line:
            repos[-1][3] += 1
    return repos


def human(n):
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def bar(frac, width):
    # eighth blocks give the bar sub-cell precision
    full, part = divmod(round(frac * width * 8), 8)
    return ("█" * full + ("▏▎▍▌▋▊▉"[part - 1] if part else "")).ljust(width, "·")


def portrait_rows(photo):
    """Braille rows for the portrait: rendered from the photo if it's here, else read from the cache."""
    if photo.exists():
        rows = braille(photo, ART_COLS, ART_ROWS, **PORTRAIT)
        PORTRAIT_CACHE.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return rows
    if PORTRAIT_CACHE.exists():
        return PORTRAIT_CACHE.read_text(encoding="utf-8").splitlines()
    sys.exit(f"no photo at {photo} and no cached portrait at {PORTRAIT_CACHE}")


def draw(photo):
    """Lay out every cell. Returns the grid plus cells for the animated overlays."""
    g = Grid()
    g.box(0, 0, ROWS - 1, COLS - 1, color=SURFACE1)
    title = f" {USER}@{HOST}: ~ "
    g.put(0, (COLS - len(title)) // 2, title, OVERLAY1)
    for i, color in enumerate((RED, YELLOW, GREEN)):
        g.put(0, 3 + i * 2, "●", color)

    # big name with a ░ drop shadow
    col, ink = 2, []
    for letter in NAME:
        glyph = GLYPHS[letter]
        ink += [(2 + dr, col + dc) for dr, line in enumerate(glyph) for dc, px in enumerate(line) if px == "#"]
        col += len(glyph[0]) + 1
    for r, c in ink:
        g.put(r + 1, c + 1, "░", SURFACE1)
    for r, c in ink:
        g.put(r, c, "█", NAME_FILL)
    for i, (color, line) in enumerate(ABOUT):
        c = g.put(2 + i, col + 2, "▸ ", color)
        g.put(2 + i, c, line)

    # portrait pane
    top, left = 8, 2
    bottom, mid = top + ART_ROWS + 1, left + ART_COLS + 3
    g.box(top, left, bottom, mid, "~/headshot.jpg", title_color=MAUVE)
    for i, row in enumerate(portrait_rows(photo)):
        g.put(top + 1 + i, left + 2, row, ART_FILL)

    # stack pane
    rl, rr = mid + 2, COLS - 3
    g.box(top, rl, top + len(STACK) + 1, rr, "stack", title_color=PEACH)
    k = 0
    for i, (label, words) in enumerate(STACK):
        c = g.put(top + 1 + i, rl + 2, f"{label:<6}", OVERLAY1)
        for w in words.split():
            c = g.put(top + 1 + i, c, w, RAINBOW[k % len(RAINBOW)]) + 1
            k += 1

    # open source pane, from the README
    ot = top + len(STACK) + 2
    ob = bottom - len(NOW) - 2
    g.box(ot, rl, ob, rr, "open source", title_color=GREEN)
    repos = contributions()
    most = max(s for _, s, _, _ in repos)
    g.put(ot + 1, rl + 2, f"{'repo':<19}{'stars':>7}  {'log(★)':<22}merged  open", OVERLAY1)
    for i, (name, stars, merged, opened) in enumerate(repos[: ob - ot - 3]):
        r = ot + 2 + i
        g.put(r, rl + 2, name[:18])
        g.put(r, rl + 21, f"★{human(stars):>6}", YELLOW)
        g.put(r, rl + 30, bar(math.log10(stars) / math.log10(most), 20), RAINBOW[i % len(RAINBOW)])
        g.put(r, rl + 52, f"{merged:>4} ✓", GREEN if merged else SURFACE2)
        g.put(r, rl + 60, f"{opened:>3} ○", YELLOW if opened else SURFACE2)
    c = g.put(ob, rr - 46, "┤ ", SURFACE2)
    c = g.put(ob, c, f"{sum(r[2] for r in repos)} merged", GREEN)
    c = g.put(ob, c, " · ", SURFACE2)
    c = g.put(ob, c, f"{sum(r[3] for r in repos)} open", YELLOW)
    c = g.put(ob, c, " · ", SURFACE2)
    c = g.put(ob, c, f"{len(repos)} upstream repos")
    g.put(ob, c, " ├", SURFACE2)

    g.box(ob + 1, rl, bottom, rr, "now", title_color=SKY)
    for i, (label, color, line) in enumerate(NOW):
        c = g.put(ob + 2 + i, rl + 2, f"{label:<10}", color)
        g.put(ob + 2 + i, c, line)

    # prompt and tmux bar
    prompt_row, status_row = bottom + 2, ROWS - 2
    c = g.put(prompt_row, 2, f"{USER}@{HOST}", GREEN)
    c = g.put(prompt_row, c, " ~ ", BLUE)
    c = g.put(prompt_row, c, "❯ ", MAUVE)
    cursor = g.put(prompt_row, c, "open https://dsanch.com", TEXT) + 1
    g.fill_bg(status_row, 1, COLS - 1, SURFACE0)
    c = g.put(status_row, 1, f" [{HOST}] ", CRUST, GREEN)
    c = g.put(status_row, c, " 0:zsh ", SUBTEXT)
    c = g.put(status_row, c, " 1:banner* ", CRUST, MAUVE)
    g.put(status_row, c, " 2:nvim  3:lazygit ", SUBTEXT)
    right = f'"{USER}@{HOST}"  utf-8  {COLS}x{ROWS} '
    g.put(status_row, COLS - 6 - len(right), right, SUBTEXT)
    g.put(status_row, COLS - 5, "    ", CRUST, BLUE)
    return g, dict(name=(2, col - 1), cursor=(prompt_row, cursor), spinner=(status_row, COLS - 3))


def build(photo):
    g, at = draw(photo)

    def x(c):
        return PAD + c * CW

    def y(r):
        return PAD + r * CH + BASELINE

    def run(c, s, fg, ty=BASELINE):
        # each run is pinned to its column and stretched to its exact cell width, so a fallback
        # font with different glyph widths (braille, box drawing) can't knock the grid out of line
        fit = f' textLength="{len(s) * CW:.1f}" lengthAdjust="spacingAndGlyphs"' if len(s) > 1 else ""
        glow = ' filter="url(#glow)"' if fg == NAME_FILL else ""
        # braille dots are tiny at the grid's font size, so draw them bigger; textLength keeps the width
        size = f' font-size="{FONT_SIZE * 1.3:.1f}"' if fg == ART_FILL else ""
        return f'<text x="{x(c):.1f}" y="{ty:.1f}" fill="{fg}"{fit}{glow}{size}>{escape(s)}</text>'

    boot = 0.03  # seconds per row while the screen "draws in"
    out = []
    add = out.append
    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'font-family="{FONT}" font-size="{FONT_SIZE}" xml:space="preserve">'
    )
    add(f"""<style>
  text {{ white-space: pre; }}
  .row {{ animation: boot .12s steps(2) both; }}
  .glitch {{ opacity: 0; animation: glitch 7s steps(1) {ROWS * boot + 1:.2f}s infinite; }}
  .glitch.b {{ animation-name: glitch-b; }}
  .blink {{ animation: blink 1.06s steps(1) infinite; }}
  .spin {{ opacity: 0; animation: spin .6s steps(1) infinite; }}
  .spin:first-child {{ opacity: 1; }}
  .crt {{ animation: flicker 4s steps(1) infinite; }}
  @keyframes boot {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
  @keyframes glitch {{ 0%, 93%, 97% {{ opacity: 0; transform: none; }} 94% {{ opacity: .8; transform: translate(-3px, -1px); }} 95.5% {{ opacity: .6; transform: translate(4px, 1px); }} }}
  @keyframes glitch-b {{ 0%, 93%, 97% {{ opacity: 0; transform: none; }} 94% {{ opacity: .8; transform: translate(3px, 1px); }} 95.5% {{ opacity: .6; transform: translate(-4px, 0); }} }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}
  @keyframes spin {{ 0% {{ opacity: 1; }} 25%, 100% {{ opacity: 0; }} }}
  @keyframes flicker {{ 0%, 100% {{ opacity: .3; }} 48% {{ opacity: .2; }} 50% {{ opacity: .35; }} }}
  @media (prefers-reduced-motion: reduce) {{ .row, .glitch, .blink, .spin, .crt {{ animation: none; }} }}
</style>""")
    add(f"""<defs>
  <linearGradient id="name" x1="{x(at['name'][0])}" y1="0" x2="{x(at['name'][1])}" y2="0" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="{MAUVE}"/><stop offset=".35" stop-color="{PINK}"/><stop offset=".7" stop-color="{PEACH}"/><stop offset="1" stop-color="{YELLOW}"/>
  </linearGradient>
  <linearGradient id="art" x1="{x(4)}" y1="{y(9)}" x2="{x(48)}" y2="{y(30)}" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="{MAUVE}"/><stop offset=".5" stop-color="{BLUE}"/><stop offset="1" stop-color="{TEAL}"/>
  </linearGradient>
  <pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="{CRUST}"/></pattern>
  <radialGradient id="vignette" cx=".5" cy=".5" r=".75">
    <stop offset=".6" stop-color="{CRUST}" stop-opacity="0"/><stop offset="1" stop-color="{CRUST}" stop-opacity=".55"/>
  </radialGradient>
  <filter id="glow" x="-5%" y="-5%" width="110%" height="110%">
    <feGaussianBlur stdDeviation="1.6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>""")
    add(f'<rect width="{WIDTH}" height="{HEIGHT}" rx="14" fill="{BASE}"/>')

    # one group per row, offset to the row's top so the boot animation can reveal it as a unit
    for r in range(ROWS):
        parts = [f'<rect x="{x(c):.1f}" width="{n * CW:.1f}" height="{CH}" fill="{bg}"/>' for c, n, bg in g.bg_runs(r)]
        parts += [run(c, s, fg) for c, s, fg in g.runs(r)]
        if parts:
            add(f'<g class="row" style="animation-delay:{r * boot:.2f}s" transform="translate(0 {PAD + r * CH})">{"".join(parts)}</g>')

    # chromatic-aberration copies of the name that flash every few seconds
    for cls, color in (("glitch", RED), ("glitch b", TEAL)):
        name_runs = [(r, c, s) for r in range(2, 7) for c, s, fg in g.runs(r) if fg == NAME_FILL]
        add(f'<g class="{cls}">' + "".join(run(c, s, color, y(r)) for r, c, s in name_runs) + "</g>")

    cr, cc = at["cursor"]
    add(f'<text class="blink" x="{x(cc):.1f}" y="{y(cr):.1f}" fill="{TEXT}">█</text>')
    sr, sc = at["spinner"]
    frames = "".join(
        f'<text class="spin" style="animation-delay:{i * 0.15:.2f}s" x="{x(sc):.1f}" y="{y(sr):.1f}" fill="{CRUST}" font-weight="700">{escape(f)}</text>'
        for i, f in enumerate("|/-\\")
    )
    add(f"<g>{frames}</g>")

    add(f'<rect class="crt" width="{WIDTH}" height="{HEIGHT}" rx="14" fill="url(#scan)" opacity=".3" pointer-events="none"/>')
    add(f'<rect width="{WIDTH}" height="{HEIGHT}" rx="14" fill="url(#vignette)" pointer-events="none"/>')
    add("</svg>")

    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--photo", type=Path, default=HEADSHOT, help="image to draw as the portrait")
    build(parser.parse_args().photo)
