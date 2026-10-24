#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Scott Anderson
# SPDX-License-Identifier: Apache-2.0

"""Draw review sheets comparing emoji fonts, for pull requests.

glyphs: a row per glyph that differs between two font sizes, with the
smaller size's 1-bit and color glyphs, then the larger size's, in the
layout of tools/test_image_review.py. A color glyph the same as its 1-bit
glyph says "Same as B&W".

changed: every glyph of a font, grouped by Unicode emoji group, optionally
only the color glyphs that differ from the 1-bit font, split into sheets
between groups to stay under a height.

Sheets are drawn at 1x and doubled, so GitHub can show them pixel for pixel
at half their width. Each FONT is the 1-bit .pbf; its color variant is the
~color.pbf next to it.

Usage:
    python emoji_review.py glyphs EMOJI_28.pbf EMOJI_36.pbf -o review/glyphs
    python emoji_review.py changed EMOJI_36.pbf emoji-test.txt \
        -o changed-36-color.png --color
"""

import argparse
import contextlib
import io
import math
import os
import sys
import tempfile

from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pbf_extract
import test_image_review as tir

COLUMNS = ("B&W", "Color")
SCALE = 2


def color_path(path):
    root, ext = os.path.splitext(path)
    return f"{root}~color{ext}"


def load(path, work):
    """({codepoint: glyph}, max_height, glyph directory) of a font."""
    out = os.path.join(work, str(len(os.listdir(work))))
    with contextlib.redirect_stdout(io.StringIO()):
        m = pbf_extract.extract_pbf(path, out)
    return {g["codepoint"]: g for g in m["glyphs"]}, m["max_height"], out


def glyph_image(font, cp):
    glyphs, _, d = font
    g = glyphs[cp]
    return (
        Image.open(os.path.join(d, g["file"])).convert("RGBA") if g["width"] else None
    )


def cell(font, cp):
    """The glyph in a box the font's height, on white."""
    glyphs, height, _ = font
    g = glyphs[cp]
    c = Image.new("RGBA", (height + 2, height + 2), "white")
    im = glyph_image(font, cp)
    if im:
        c.alpha_composite(
            im, (max(0, g["left_offset"]) + 1, max(0, g["top_offset"]) + 1)
        )
    return c


def is_color(font, cp):
    """Whether the glyph has any pixel that isn't gray."""
    im = glyph_image(font, cp)
    return bool(im) and any(
        a and not r == g == b for r, g, b, a in im.get_flattened_data()
    )


def trim(img):
    bbox = ImageChops.difference(img, Image.new("RGB", img.size, "white")).getbbox()
    return img.crop((0, 0, bbox[2] + 4, bbox[3] + 4)) if bbox else img


def doubled(img):
    return img.resize((img.width * SCALE, img.height * SCALE), Image.NEAREST)


def glyphs_cmd(args, work):
    small, large = (
        {c: load(p, work) for c, p in zip(COLUMNS, (path, color_path(path)))}
        for path in (args.small, args.large)
    )
    cps = sorted(large["B&W"][0])
    if args.codepoints:
        wanted = {int(c, 16) for c in args.codepoints.split(",")}
        cps = [cp for cp in cps if cp in wanted]
    rows = []
    for cp in cps:
        cells = {c: (cell(small[c], cp), cell(large[c], cp)) for c in COLUMNS}
        if args.codepoints or any(not tir.same_pixels(a, b) for a, b in cells.values()):
            rows.append((f"U+{cp:04X}", cells))

    titles = tuple(f"{f[COLUMNS[0]][1]} pt" for f in (small, large))
    strips = [
        tir.draw_sheet(
            rows[i : i + args.rows],
            list(COLUMNS),
            None,
            "",
            "",
            titles=titles,
            size_names=COLUMNS,
            label_w=64,
            header_h=40,
            split=12,
            placeholder_size=9,
            divider=False,
        )
        for i in range(0, len(rows), args.rows)
    ]
    os.makedirs(args.output, exist_ok=True)
    for n, i in enumerate(range(0, len(strips), args.strips), 1):
        group = strips[i : i + args.strips]
        w = max(s.width for s in group)
        sheet = Image.new(
            "RGB", (len(group) * (w + 10) - 10, max(s.height for s in group)), "white"
        )
        for k, s in enumerate(group):
            sheet.paste(s, (k * (w + 10), 0))
            if k:
                x = k * (w + 10) - 6
                sheet.paste((153, 153, 153), (x, 0, x + 2, sheet.height))
        sheet = doubled(trim(sheet))
        path = os.path.join(args.output, f"glyphs-{n:02}.png")
        sheet.save(path)
        print(f"{path}: {sheet.width}x{sheet.height}")


def emoji_groups(path):
    """{codepoint: (Unicode emoji group, order)} from emoji-test.txt."""
    out, group = {}, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("# group:"):
                group = line.split(":", 1)[1].strip()
            elif line[:1] not in ("#", "\n") and ";" in line:
                seq = [s for s in line.split(";")[0].split() if s != "FE0F"]
                if len(seq) == 1:
                    out.setdefault(int(seq[0], 16), (group, len(out)))
    return out


def changed_cmd(args, work):
    mono = load(args.font, work)
    font = load(color_path(args.font), work) if args.color else mono
    glyphs = {cp: g for cp, g in font[0].items() if g["width"]}
    if args.color:
        # Only glyphs with color the 1-bit font lacks
        glyphs = {cp: g for cp, g in glyphs.items() if is_color(font, cp)}
    order = emoji_groups(args.emoji_test)
    groups = []
    for cp in sorted(glyphs, key=lambda c: (order.get(c, (0, 1 << 30))[1], c)):
        name = order.get(cp, ("Other",))[0]
        if not groups or groups[-1][0] != name:
            groups.append((name, []))
        groups[-1][1].append(cp)

    h = font[1] + 4
    w = max(h, max(g["left_offset"] + g["width"] for g in glyphs.values()) + 2)
    label, head, ghead, cols = 10, 16, 14, args.cols
    cw, ch = w + 8, h + label

    # Pages of (group, its glyphs on the page), breaking between groups, or
    # between rows of a group too tall for a page of its own
    limit = args.max_height // SCALE
    pages, used = [[]], head
    for name, members in groups:
        rows = [members[i : i + cols] for i in range(0, len(members), cols)]
        if pages[-1] and used + ghead + len(rows) * ch > limit:
            pages.append([])
            used = head
        while rows:
            fit = max(1, (limit - used - ghead) // ch)
            part, rows = rows[:fit], rows[fit:]
            pages[-1].append((name, len(members), [cp for row in part for cp in row]))
            used += ghead + len(part) * ch
            if rows:
                pages.append([])
                used = head

    text = ImageFont.load_default()
    kind = "color" if args.color else "1-bit"
    root, ext = os.path.splitext(args.output)
    for n, page in enumerate(pages, 1):
        height = head + sum(
            ghead + math.ceil(len(cps) / cols) * ch for _, _, cps in page
        )
        s = Image.new("RGB", (cols * cw, height), "white")
        d = ImageDraw.Draw(s)
        title = f"{font[1]} pt {kind}: {len(glyphs)} emoji"
        if len(pages) > 1:
            title += f", {n} of {len(pages)}"
        d.text((4, 3), title, fill="black", font=text)
        y = head
        for name, total, cps in page:
            d.text((4, y + 1), f"{name} ({total})", fill="black", font=text)
            y += ghead
            for i, cp in enumerate(cps):
                x0, y0 = (i % cols) * cw, y + (i // cols) * ch
                bg = (228, 228, 228) if (i % cols + i // cols) % 2 else "white"
                d.rectangle([x0, y0, x0 + cw - 1, y0 + ch - 1], fill=bg)
                g = glyphs[cp]
                im = glyph_image(font, cp)
                s.paste(
                    im,
                    (
                        x0 + 4 + max(0, g["left_offset"]),
                        y0 + 2 + max(0, g["top_offset"]),
                    ),
                    im,
                )
                d.text((x0 + 2, y0 + h - 1), f"{cp:X}", fill=(90, 90, 90), font=text)
            y += math.ceil(len(cps) / cols) * ch
        s = doubled(s)
        path = args.output if len(pages) == 1 else f"{root}-{n}{ext}"
        s.save(path)
        print(f"{path}: {s.width}x{s.height}")


def main():
    parser = argparse.ArgumentParser(description="Draw emoji font review sheets")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("glyphs", help="Glyphs that differ between two font sizes")
    p.add_argument("small", help="Smaller 1-bit font, e.g. EMOJI_28.pbf")
    p.add_argument("large", help="Larger 1-bit font, e.g. EMOJI_36.pbf")
    p.add_argument("-o", "--output", required=True, help="Output directory")
    p.add_argument("--codepoints", help="Only these hex codepoints, comma separated")
    p.add_argument("--rows", type=int, default=30, help="Glyphs per strip")
    p.add_argument("--strips", type=int, default=3, help="Strips per sheet")
    p = sub.add_parser("changed", help="A font's glyphs by emoji group")
    p.add_argument("font", help="1-bit font, e.g. EMOJI_36.pbf")
    p.add_argument("emoji_test", help="Unicode emoji-test.txt")
    p.add_argument("-o", "--output", required=True, help="Output PNG")
    p.add_argument("--color", action="store_true", help="Color glyphs with color only")
    p.add_argument("--cols", type=int, default=12, help="Glyphs per row")
    p.add_argument(
        "--max-height",
        type=int,
        default=2000,
        help="Split into sheets at most this many pixels tall",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as work:
        (glyphs_cmd if args.cmd == "glyphs" else changed_cmd)(args, work)
    return 0


if __name__ == "__main__":
    sys.exit(main())
