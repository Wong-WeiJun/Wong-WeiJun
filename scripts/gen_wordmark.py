#!/usr/bin/env python3
"""Render the profile wordmark and status ticker SVGs from assets/wordmark.txt.

Standard library only -- no dependency needed to run this, so it is not part
of the GitHub Actions workflow. Re-run it locally whenever wordmark.txt or
TICKER_MESSAGES changes:

    python3 scripts/gen_wordmark.py

wordmark.txt was produced once with:

    pip install pyfiglet
    python3 -c "import pyfiglet; print(pyfiglet.Figlet(font='ansi_shadow', \
width=300).renderText('WEI JUN WONG'))"

...with the blank leading/trailing rows trimmed. "ANSI Shadow" is one of the
fonts bundled with the open-source pyfiglet font pack.

Writes assets/wordmark-{dark,light}.svg and assets/ticker.svg.
"""

import math
import os
from xml.sax.saxutils import escape

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(REPO_ROOT, "assets")

DARK_PURPLE = "#CBA6F7"  # Catppuccin Mocha "Mauve" -- matches header.png / terminal.gif
LIGHT_PURPLE = (
    "#8839EF"  # Catppuccin Latte "Mauve" -- same family, tuned for light backgrounds
)

FONT_SIZE = 10.0
CHAR_WIDTH = 6.0
LINE_HEIGHT = 10.0
FONT_STACK = "ui-monospace,'DejaVu Sans Mono','Liberation Mono','Courier New',monospace"

TICKER_MESSAGES = [
    "2nd Year CS Student",
    "Cloud & Platform Engineering",
    "University of Wollongong",
    "Arch Linux (Omarchy) + Neovim (lazyvim)",
]

TICKER_WIDTH = 900
TICKER_HEIGHT = 46
TICKER_FONT_SIZE = 22.0
TICKER_ADVANCE = 13.2
TICKER_SEPARATOR = "  •  "
TICKER_INK = "#CDD6F4"  # Catppuccin Text
TICKER_GROUND = "#11111B"  # Catppuccin Crust
TICKER_EDGE = "#313244"  # Catppuccin Surface0
TICKER_MID = "#DDB6F2"  # lighter mauve, for the near-glow ring
TICKER_BLOOM = "#CBA6F7"  # Catppuccin Mauve
DOT_PITCH = 3.0
DOT_RADIUS = 0.8
FADE_WIDTH = 38

TYPE_SECONDS = 5.0
TYPE_REVEALED_PERCENT = 70.0
CURSOR_BLINK_SECONDS = 0.9


def read_art(name):
    with open(os.path.join(ASSETS, name), encoding="utf-8") as handle:
        text = handle.read()
    lines = text.replace("\r", "").split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and not lines[0].strip():
        lines.pop(0)
    return lines


BAR_THICKNESS = 1.2
BAR_X = (1.2, 3.6)
BAR_Y = (3.4, 5.4)
SEAM_OVERLAP = 0.1


def horizontal_bar(x, y, opens_right):
    if opens_right:
        return (x, y, CHAR_WIDTH - x, BAR_THICKNESS)
    return (0.0, y, x + BAR_THICKNESS, BAR_THICKNESS)


def vertical_bar(x, y, opens_down):
    if opens_down:
        return (x, y, BAR_THICKNESS, LINE_HEIGHT - y)
    return (x, 0.0, BAR_THICKNESS, y + BAR_THICKNESS)


def corner_bars(opens_right, opens_down):
    outer_x, inner_x = BAR_X if opens_right else BAR_X[::-1]
    outer_y, inner_y = BAR_Y if opens_down else BAR_Y[::-1]
    return [
        horizontal_bar(outer_x, outer_y, opens_right),
        horizontal_bar(inner_x, inner_y, opens_right),
        vertical_bar(outer_x, outer_y, opens_down),
        vertical_bar(inner_x, inner_y, opens_down),
    ]


GLYPH_BARS = {
    "═": [
        (0.0, BAR_Y[0], CHAR_WIDTH, BAR_THICKNESS),
        (0.0, BAR_Y[1], CHAR_WIDTH, BAR_THICKNESS),
    ],
    "║": [
        (BAR_X[0], 0.0, BAR_THICKNESS, LINE_HEIGHT),
        (BAR_X[1], 0.0, BAR_THICKNESS, LINE_HEIGHT),
    ],
    "╔": corner_bars(True, True),
    "╗": corner_bars(False, True),
    "╚": corner_bars(True, False),
    "╝": corner_bars(False, False),
}

BLOCK = "█"


def block_runs(line):
    """Merge each horizontal run of full blocks into one span, so abutting
    rectangles cannot show antialiased hairlines between them."""
    runs = []
    start = None
    for col, char in enumerate(line + " "):
        if char == BLOCK and start is None:
            start = col
        elif char != BLOCK and start is not None:
            runs.append((start, col - start))
            start = None
    return runs


def wordmark_rects(lines):
    rects = []
    for row, line in enumerate(lines):
        y = row * LINE_HEIGHT
        for start, length in block_runs(line):
            height = LINE_HEIGHT + (SEAM_OVERLAP if row < len(lines) - 1 else 0.0)
            rects.append((start * CHAR_WIDTH, y, length * CHAR_WIDTH, height))
        for col, char in enumerate(line):
            for bar_x, bar_y, bar_w, bar_h in GLYPH_BARS.get(char, ()):
                rects.append((col * CHAR_WIDTH + bar_x, y + bar_y, bar_w, bar_h))
    return rects


def wordmark_style(columns, width):
    """Type the wordmark out one character cell at a time.

    Both animations start from their resting state in @keyframes rather than
    in the rule, so a renderer that ignores CSS animation still shows the
    finished wordmark with no cursor instead of an empty box.
    """
    return (
        "<style>"
        ".w{animation:type %(seconds)gs steps(%(columns)d) infinite}"
        "@keyframes type{0%%{clip-path:inset(0 100%% 0 0)}%(revealed)g%%,100%%{clip-path:inset(0)}}"
        ".c{opacity:0;animation:move %(seconds)gs steps(%(columns)d) infinite,"
        "blink %(blink)gs step-end infinite}"
        "@keyframes move{0%%{transform:translateX(0)}%(revealed)g%%,100%%{transform:translateX(%(width)dpx)}}"
        "@keyframes blink{0%%,50%%{opacity:0.8}50.01%%,100%%{opacity:0}}"
        "@media(prefers-reduced-motion:reduce){.w{animation:none}.c{display:none}}"
        "</style>"
        % {
            "seconds": TYPE_SECONDS,
            "columns": columns,
            "revealed": TYPE_REVEALED_PERCENT,
            "blink": CURSOR_BLINK_SECONDS,
            "width": width,
        }
    )


def build_wordmark(lines, colour, title):
    """Draw the wordmark as rectangles rather than <text>.

    The art is built from U+2550-U+2588 box and block glyphs, which the
    monospace fonts in FONT_STACK do not contain. Rendered as text inside an
    <img>, browsers fall back to a proportional font and the art collapses,
    so the glyphs are emitted as vector geometry instead.
    """
    columns = max(len(line) for line in lines)
    width = math.ceil(columns * CHAR_WIDTH)
    height = math.ceil(len(lines) * LINE_HEIGHT)
    shapes = "".join(
        '<rect x="%g" y="%g" width="%g" height="%g"/>' % rect
        for rect in wordmark_rects(lines)
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
        'role="img" fill="%s"><title>%s</title>%s<g class="w">%s</g>'
        '<rect class="c" x="0" y="0" width="%g" height="%d"/></svg>'
        % (
            width,
            height,
            width,
            height,
            colour,
            escape(title),
            wordmark_style(columns, width),
            shapes,
            CHAR_WIDTH,
            height,
        )
    )


def build_ticker(messages, title):
    """An LED dot-matrix strip: text scrolls behind a punched dot-grid mask."""
    run = TICKER_SEPARATOR.join(messages) + TICKER_SEPARATOR
    run_width = len(run) * TICKER_ADVANCE
    copies = math.ceil(TICKER_WIDTH / run_width) + 1
    duration = max(20, round(len(run) * 0.34))
    baseline = TICKER_HEIGHT / 2.0 + TICKER_FONT_SIZE * 0.35

    runs = "".join(
        '<text x="%g" y="%g" textLength="%g" lengthAdjust="spacingAndGlyphs"'
        ' xml:space="preserve">%s</text>'
        % (index * run_width, baseline, run_width, escape(run))
        for index in range(copies)
    )

    style = (
        "<style>"
        ".t{animation:scroll %(duration)ds linear infinite}"
        "@keyframes scroll{from{transform:translateX(0)}to{transform:translateX(-%(distance)gpx)}}"
        "@media(prefers-reduced-motion:reduce){.t{animation:none}}"
        "</style>" % {"duration": duration, "distance": run_width}
    )

    defs = (
        "<defs>"
        '<pattern id="dots" width="%(pitch)g" height="%(pitch)g" patternUnits="userSpaceOnUse">'
        '<circle cx="%(half)g" cy="%(half)g" r="%(radius)g" fill="#fff"/></pattern>'
        '<mask id="grid"><rect width="%(width)d" height="%(height)d" fill="url(#dots)"/></mask>'
        '<filter id="glow" x="-10%%" y="-100%%" width="120%%" height="300%%">'
        '<feGaussianBlur in="SourceAlpha" stdDeviation="4" result="wide"/>'
        '<feFlood flood-color="%(bloom)s" flood-opacity="0.55"/>'
        '<feComposite in2="wide" operator="in" result="halo"/>'
        '<feGaussianBlur in="SourceAlpha" stdDeviation="1.4" result="near"/>'
        '<feFlood flood-color="%(mid)s" flood-opacity="0.85"/>'
        '<feComposite in2="near" operator="in" result="ring"/>'
        '<feMerge><feMergeNode in="halo"/><feMergeNode in="ring"/>'
        '<feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<linearGradient id="fade"><stop offset="0" stop-color="%(ground)s"/>'
        '<stop offset="1" stop-color="%(ground)s" stop-opacity="0"/></linearGradient>'
        "</defs>"
        % {
            "pitch": DOT_PITCH,
            "half": DOT_PITCH / 2.0,
            "radius": DOT_RADIUS,
            "width": TICKER_WIDTH,
            "height": TICKER_HEIGHT,
            "ground": TICKER_GROUND,
            "bloom": TICKER_BLOOM,
            "mid": TICKER_MID,
        }
    )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %(width)d %(height)d" '
        'width="%(width)d" height="%(height)d" role="img" font-family="%(font)s" '
        'font-size="%(size)g" letter-spacing="0.045em">'
        "<title>%(title)s</title>%(style)s%(defs)s"
        '<rect width="%(width)d" height="%(height)d" fill="%(ground)s"/>'
        '<g mask="url(#grid)">'
        '<rect width="%(width)d" height="%(height)d" fill="%(ink)s" opacity="0.075"/>'
        '<g class="t" filter="url(#glow)" fill="%(ink)s">%(runs)s</g>'
        "</g>"
        '<rect width="%(fade)d" height="%(height)d" fill="url(#fade)"/>'
        '<rect x="%(fade_x)d" width="%(fade)d" height="%(height)d" fill="url(#fade)" '
        'transform="rotate(180 %(mirror_x)g %(mirror_y)g)"/>'
        '<rect width="%(width)d" height="1" fill="%(edge)s"/>'
        '<rect y="%(bottom)d" width="%(width)d" height="1" fill="%(edge)s"/>'
        "</svg>"
        % {
            "width": TICKER_WIDTH,
            "height": TICKER_HEIGHT,
            "font": escape(FONT_STACK, {'"': "&quot;"}),
            "size": TICKER_FONT_SIZE,
            "title": escape(title),
            "style": style,
            "defs": defs,
            "ground": TICKER_GROUND,
            "ink": TICKER_INK,
            "edge": TICKER_EDGE,
            "runs": runs,
            "fade": FADE_WIDTH,
            "fade_x": TICKER_WIDTH - FADE_WIDTH,
            "mirror_x": TICKER_WIDTH - FADE_WIDTH / 2.0,
            "mirror_y": TICKER_HEIGHT / 2.0,
            "bottom": TICKER_HEIGHT - 1,
        }
    )


def write(name, content):
    path = os.path.join(ASSETS, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    print("%-22s %7d bytes" % (name, len(content.encode("utf-8"))))


def main():
    wordmark = read_art("wordmark.txt")
    ticker_title = " · ".join(TICKER_MESSAGES)

    write("wordmark-dark.svg", build_wordmark(wordmark, DARK_PURPLE, "WEI JUN WONG"))
    write("wordmark-light.svg", build_wordmark(wordmark, LIGHT_PURPLE, "WEI JUN WONG"))
    write("ticker.svg", build_ticker(TICKER_MESSAGES, ticker_title))


if __name__ == "__main__":
    main()
