"""Render architecture diagrams from JSON specs to SVG and PNG.

Usage: python3 scripts/docs/render_diagrams.py [name ...]

Specs live in docs/architecture/diagrams/src/<name>.json; output goes to
docs/architecture/diagrams/<name>.svg (follows the reader's light or dark
mode, for embedding in Markdown) and <name>.png (light, for attaching to
Drive or Docs). PNG needs Google Chrome; without it only the SVG is written.

A spec is {"rows": [...]}, optionally with "title" and "subtitle". Each
row is one of:
  {"step": "Title", "text": "detail"}                   centred heading
  {"cards": [{"title", "text", "icon"?, "tone"?}]}      1-4 boxes side by side
  {"group": "LABEL", "tone"?, "rows": [...]}            dashed section of rows
Rows are joined by a down arrow; give a row "arrow": "label" to caption
the arrow above it, or "arrow": false to leave it out. A card takes its
group's tone unless it sets its own. Tones: blue, purple, green, orange,
grey.
"""
import html
import json
import subprocess  # nosec B404: fixed Chrome screenshot command only
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIAGRAMS = ROOT / "docs" / "architecture" / "diagrams"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

WIDTH = 960
PAD = 8
GAP = 12
ARROW = 40
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"

# Light colours first, dark second; GitHub's Primer palette.
TONES = {"blue": ("#0969da", "#4493f8"), "purple": ("#8250df", "#ab7df8"),
         "green": ("#1a7f37", "#3fb950"), "orange": ("#bc4c00", "#f0883e"),
         "grey": ("#59636e", "#9198a1")}
STYLE = """
.card{fill:#ffffff;stroke:#d1d9e0}
.group{fill:#f6f8fa;fill-opacity:.6;stroke:#d1d9e0;stroke-dasharray:5 4}
.t{fill:#1f2328;font-weight:600}
.x{fill:#59636e}
.m{fill:#59636e;font-weight:600;letter-spacing:1.6px}
.ln{stroke:#818b98;fill:none}
%LIGHT%
@media (prefers-color-scheme:dark){
.card{fill:#151b23;stroke:#3d444d}
.group{fill:#0d1117;fill-opacity:.6;stroke:#3d444d}
.t{fill:#f0f6fc}
.x{fill:#9198a1}
.m{fill:#9198a1}
.ln{stroke:#656c76}
%DARK%
}
"""

# Feather-style 24px icons, stroked.
ICONS = {
    "check": "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0zM8 12l3 3 5-6",
    "user": "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
    "database": "M12 8c5 0 9-1.3 9-3s-4-3-9-3-9 1.3-9 3 4 3 9 3zM21 12c0 1.7-4 3-9 3s-9-1.3-9-3M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5",
    "cloud": "M18 10h-1.3A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z",
    "lock": "M5 11h14v10H5zM8 11V7a4 4 0 0 1 8 0v4",
    "search": "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3",
    "sheet": "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h8",
    "clock": "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2",
    "cpu": "M4 4h16v16H4zM9 9h6v6H9zM9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3",
    "key": "M7.5 17.5a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9zM11.5 11.5L21 2M17 6l3 3M14.5 8.5l2.5 2.5",
    "box": "M21 16V8l-9-5-9 5v8l9 5 9-5zM3.3 7L12 12l8.7-5M12 22V12",
    "flow": "M6 3v12M18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 9a9 9 0 0 1-9 9",
    "loop": "M23 4v6h-6M1 20v-6h6M3.5 9a9 9 0 0 1 14.9-3.4L23 10M1 14l4.6 4.4A9 9 0 0 0 20.5 15",
    "shield": "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
    "git": "M6 3v12M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 9v3a3 3 0 0 1-3 3H6",
}


def tone_css():
    light, dark = [], []
    for name, (lc, dc) in TONES.items():
        light.append(f".s-{name}{{stroke:{lc}}}.f-{name}{{fill:{lc}}}")
        dark.append(f".s-{name}{{stroke:{dc}}}.f-{name}{{fill:{dc}}}")
    return STYLE.replace("%LIGHT%", "".join(light)).replace("%DARK%", "".join(dark))


def wrap(text, size, width):
    """Split text into lines that fit width, estimating glyph widths."""
    per_line = max(8, int(width / (size * 0.53)))
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > per_line:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + ([line] if line else [])


def text_block(lines, x, y, size, cls):
    return [f'<text x="{x:.1f}" y="{y + i * size * 1.45:.1f}" font-size="{size}" '
            f'class="{cls}" text-anchor="middle">{html.escape(line)}</text>'
            for i, line in enumerate(lines)]


def heading(title, text, cx, y, width, title_size, text_size):
    """Centred title and wrapped text from top y; returns (svg, height)."""
    out, h = [], 0
    if title:
        lines = wrap(title, title_size, width)
        out += text_block(lines, cx, y + title_size, title_size, "t")
        h += len(lines) * title_size * 1.45
    if text:
        lines = wrap(text, text_size, width)
        out += text_block(lines, cx, y + h + 4 + text_size, text_size, "x")
        h += 4 + len(lines) * text_size * 1.45
    return out, h


def icon(name, tone, cx, y):
    return (f'<g transform="translate({cx - 10:.1f},{y}) scale(0.84)" fill="none" '
            f'class="s-{tone}" stroke-width="1.9" stroke-linecap="round" '
            f'stroke-linejoin="round"><path d="{ICONS[name]}"/></g>')


def render_cards(cards, x, y, width, tone):
    cw = (width - GAP * (len(cards) - 1)) / len(cards)
    title_size, text_size = (15, 12.5) if len(cards) > 2 else (16, 13)
    laid, tallest = [], 0
    for i, card in enumerate(cards):
        cx = x + i * (cw + GAP) + cw / 2
        card_tone = card.get("tone", tone)
        top = 16 + (30 if card.get("icon") else 0)
        parts, h = heading(card["title"], card.get("text"), cx, y + top, cw - 28,
                           title_size, text_size)
        if card.get("icon"):
            parts.insert(0, icon(card["icon"], card_tone, cx, y + 16))
        laid.append((card_tone, parts))
        tallest = max(tallest, top + h + 16)
    out = []
    for i, (card_tone, parts) in enumerate(laid):
        left = x + i * (cw + GAP)
        out.append(f'<rect x="{left:.1f}" y="{y}" width="{cw:.1f}" height="{tallest:.1f}" '
                   f'rx="8" class="card"/>')
        out.append(f'<rect x="{left + 12:.1f}" y="{y}" width="{cw - 24:.1f}" height="2.5" '
                   f'rx="1.25" class="f-{card_tone}"/>')
        out += parts
    return out, tallest


def render_row(row, x, y, width, tone):
    """Return (svg parts, height) for one row placed at x, y."""
    if "group" in row:
        group_tone = row.get("tone", tone)
        inner, h = render_rows(row["rows"], x + 14, y + 34, width - 28, group_tone)
        label = (f'<text x="{x + 16}" y="{y + 22}" font-size="10.5" class="m f-{group_tone}">'
                 f'{html.escape(row["group"].upper())}</text>')
        box = (f'<rect x="{x}" y="{y}" width="{width}" height="{h + 48}" rx="12" '
               f'class="group"/>')
        return [box, label] + inner, h + 48
    if "step" in row:
        parts, h = heading(row["step"], row.get("text"), x + width / 2, y + 2,
                           width - 80, 18, 13.5)
        return parts, h + 6
    return render_cards(row["cards"], x, y, width, tone)


def arrow(cx, y, label):
    out = [f'<path d="M{cx} {y + 10}v18M{cx - 5} {y + 23}l5 5 5-5" class="ln" '
           f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>']
    if label:
        out.append(f'<text x="{cx + 14}" y="{y + 23}" font-size="11.5" class="x">'
                   f'{html.escape(label)}</text>')
    return out


def render_rows(rows, x, y, width, tone="grey"):
    out, top = [], y
    for i, row in enumerate(rows):
        if i and row.get("arrow", True) is not False:
            label = row.get("arrow") if isinstance(row.get("arrow"), str) else None
            out += arrow(x + width / 2, y, label)
            y += ARROW
        elif i:
            y += GAP
        parts, h = render_row(row, x, y, width, tone)
        out += parts
        y += h
    return out, y - top


def render_svg(spec):
    parts, y = [], PAD
    if spec.get("title"):
        head, h = heading(spec["title"], spec.get("subtitle"), WIDTH / 2, y,
                          WIDTH - 2 * PAD, 20, 13.5)
        parts += head
        y += h + 20
    body, h = render_rows(spec["rows"], PAD, y, WIDTH - 2 * PAD)
    parts += body
    height = int(y + h + PAD)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
            f'viewBox="0 0 {WIDTH} {height}" font-family="{FONT}">'
            f'<style>{tone_css()}</style>' + "".join(parts) + "</svg>\n"), height


def render_png(svg, png_path, height):
    """Screenshot a light-only copy of the SVG, whatever the system theme."""
    if not Path(CHROME).exists():
        print(f"  skipped PNG: Chrome not found at {CHROME}")
        return
    light = svg[:svg.index("@media")] + svg[svg.index("</style>"):]
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "light.svg").write_text(light)
        page = Path(tmp) / "page.html"
        page.write_text('<html><body style="margin:0;background:#fff">'
                        '<img src="light.svg"></body></html>')
        subprocess.run([CHROME, "--headless=new",  # nosec B603: fixed Chrome path and flags as an argument list, no shell "--hide-scrollbars",
                        "--force-device-scale-factor=2", "--allow-file-access-from-files",
                        f"--user-data-dir={tmp}/profile",
                        f"--window-size={WIDTH},{height}",
                        f"--screenshot={png_path}", page.as_uri()],
                       check=True, capture_output=True, timeout=60)


def main(names):
    sources = sorted((DIAGRAMS / "src").glob("*.json"))
    if names:
        sources = [s for s in sources if s.stem in names]
    for source in sources:
        svg, height = render_svg(json.loads(source.read_text()))
        svg_path = DIAGRAMS / f"{source.stem}.svg"
        svg_path.write_text(svg)
        render_png(svg, DIAGRAMS / f"{source.stem}.png", height)
        print(f"rendered {source.stem}")


if __name__ == "__main__":
    main(sys.argv[1:])
