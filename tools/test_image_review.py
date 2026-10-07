#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Scott Anderson
# SPDX-License-Identifier: Apache-2.0

"""Draw before/after sheets of the reference images two revisions change.

Reads the images from git only and runs no code from either revision, so it
is safe to run on untrusted pull requests. For each platform it writes one
or more sheets: a row per screen with any changed image, and a column pair
per content size, where unchanged sizes show "No change" for context. It also
writes a Markdown summary and a JSON manifest.
"""

import argparse
import io
import json
import os
import re
import subprocess
import sys
import warnings

from PIL import Image, ImageDraw, ImageFont

# Images come from untrusted pull requests, so refuse anything huge
Image.MAX_IMAGE_PIXELS = 4096 * 4096
warnings.simplefilter("error", Image.DecompressionBombWarning)

IMAGE_DIR = "tests/test_images"
RENDERABLE = (".png", ".apng")
MARKER = "<!-- test-image-review -->"

# Suffixes the per-size tests append to a case name
SIZES = [
    ("", "Default"),
    ("_small", "Small"),
    ("_medium", "Medium"),
    ("_large", "Large"),
    ("_extra_large", "Extra Large"),
]
SIZE_NAMES = ["Small", "Medium", "Large", "Extra Large"]
ALL_SIZES = "All sizes"
# Order of the columns on a sheet
COLUMNS = ["Default", ALL_SIZES, *SIZE_NAMES]
SIZE_RE = re.compile(r"^(.*?)(_extra_large|_large|_medium|_small)?$")
PLATFORM_RE = re.compile(r"^([a-z0-9]+)(.*)$")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_.~+-]+$")

# Screen size and default content size of each platform, to cut the screen grids
# of tests/fixtures/screen_grid.c back into screens
PLATFORMS = {
    "asterix": ((144, 168), "Medium"),
    "obelix": ((200, 228), "Large"),
    "gabbro": ((260, 260), "Large"),
}
GRID_PADDING = 5
MAX_GRID_ROWS = 8

ROWS_PER_SHEET = 30
# Tallest sheet worth showing in a comment, unless one row is taller
MAX_SHEET_H = 3000
GAP = 6
# Space between the before and after blocks, with a line down its middle
SPLIT = 20
LABEL_W = 130
HEADER_H = 60
FONT_DIR = "/usr/share/fonts/truetype/dejavu"
BEFORE_COLOR = "#c00000"
AFTER_COLOR = "#007000"
# Checkerboard drawn behind transparent pixels
CHECKER = 8
CHECKER_COLORS = (255, 204)


def git(*args, data=False):
    out = subprocess.run(["git", *args], check=True, capture_output=True)
    return out.stdout if data else out.stdout.decode().strip()


def list_images(rev):
    """Map each file under IMAGE_DIR at rev to its blob id."""
    out = git("ls-tree", "-r", rev, "--", IMAGE_DIR.rstrip("/") + "/")
    files = {}
    for line in out.splitlines():
        meta, path = line.split("\t", 1)
        files[os.path.basename(path)] = meta.split()[2]
    return files


def split_name(filename):
    """Split a reference image name into (platform, screen, size suffix)."""
    stem, ext = os.path.splitext(filename)
    name, sep, rest = stem.partition("~")
    variant = ""
    platform = "any"
    if sep:
        platform, variant = PLATFORM_RE.match(rest).groups()
    base, size = SIZE_RE.match(name).groups()
    return platform, base + (("~" + variant) if variant else "") + ext, size or ""


def load(blob):
    img = Image.open(io.BytesIO(git("cat-file", "blob", blob, data=True)))
    img.seek(0)
    return img.convert("RGBA")


def on_checkerboard(img):
    """img over a white and gray checkerboard, so transparent pixels stand out."""
    if img.getextrema()[3][0] == 255:
        return img.convert("RGB")
    w, h = img.size
    cols, rows = -(-w // CHECKER), -(-h // CHECKER)
    board = Image.new("L", (cols, rows))
    board.putdata(
        [CHECKER_COLORS[(x + y) % 2] for y in range(rows) for x in range(cols)]
    )
    board = board.resize((cols * CHECKER, rows * CHECKER), Image.NEAREST).crop(
        (0, 0, w, h)
    )
    return Image.alpha_composite(board.convert("RGBA"), img).convert("RGB")


def loadable(blob):
    """Whether a blob decodes as an image within the size limit."""
    try:
        load(blob)
        return True
    except (
        OSError,
        SyntaxError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        return False


def grid_shape(img, platform):
    """Columns and rows of a screen grid, or None if img isn't one."""
    if platform not in PLATFORMS:
        return None
    (w, h), _ = PLATFORMS[platform]
    for cols in range(1, len(SIZE_NAMES) + 1):
        pad_x = GRID_PADDING if cols > 1 else 0
        if img.width != pad_x + cols * (w + pad_x):
            continue
        for rows in range(1, MAX_GRID_ROWS + 1):
            pad_y = GRID_PADDING if rows > 1 else 0
            if img.height == pad_y + rows * (h + pad_y):
                return cols, rows
    return None


def grid_sizes(platform, cols):
    """Sizes of a grid's columns: the Text Size setting's range, or all of them.

    The setting offers up to one size above the platform's default. A grid
    with a single column has every size the same.
    """
    if cols == 1:
        return [ALL_SIZES]
    last = min(SIZE_NAMES.index(PLATFORMS[platform][1]) + 1, len(SIZE_NAMES) - 1)
    if cols > last + 1:
        last = len(SIZE_NAMES) - 1
    return SIZE_NAMES[last - cols + 1 : last + 1]


def shown_sizes(platform):
    """Columns worth showing: the default size and the sizes either side of it."""
    if platform not in PLATFORMS:
        return set(COLUMNS)
    i = SIZE_NAMES.index(PLATFORMS[platform][1])
    return {"Default", ALL_SIZES, *SIZE_NAMES[max(i - 1, 0) : i + 2]}


def screens(img, platform, column):
    """Rows of {column: screen} in img, cutting a screen grid into its screens."""
    shape = grid_shape(img, platform)
    if shape in (None, (1, 1)):
        return [{column: img}]
    cols, rows = shape
    (w, h), _ = PLATFORMS[platform]
    pad_x = GRID_PADDING if cols > 1 else 0
    pad_y = GRID_PADDING if rows > 1 else 0
    names = grid_sizes(platform, cols)
    out = []
    for r in range(rows):
        y = pad_y + r * (h + pad_y)
        row = {
            names[c]: img.crop(
                (pad_x + c * (w + pad_x), y, pad_x + c * (w + pad_x) + w, y + h)
            )
            for c in range(cols)
        }
        out.append(row)
    return out


def expand(cells, other):
    """Repeat a lone screen across the sizes of the other revision's row.

    A grid whose sizes all match is a single screen, so compare it with each
    size of a grid that has them.
    """
    if len(cells) != 1 or not other or not set(other) <= set(SIZE_NAMES):
        return cells
    (img,) = cells.values()
    return dict.fromkeys(other, img)


def same_pixels(a, b):
    return a.size == b.size and a.tobytes() == b.tobytes()


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    except OSError:
        return ImageFont.load_default(size=size)


def row_label(screen):
    """Show test_<suite>__<case>.png as the suite over the case."""
    stem = os.path.splitext(screen)[0]
    stem = stem.removeprefix("test_")
    suite, sep, case = stem.partition("__")
    return wrap(suite, 16) + "\n" + wrap(case, 16) if sep else wrap(stem, 16)


def wrap(text, width):
    lines = [""]
    for part in re.split(r"(?<=[_~.])", text):
        if lines[-1] and len(lines[-1]) + len(part) > width:
            lines.append("")
        lines[-1] += part
    return "\n".join(lines)


def placeholder(draw, box, text):
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill="#eeeeee", outline="#bbbbbb")
    lines = text.split("\n")
    for i, line in enumerate(lines):
        y = (y0 + y1) / 2 + (i - (len(lines) - 1) / 2) * 18
        draw.text(((x0 + x1) / 2, y), line, fill="#555555", font=font(14), anchor="mm")


def repeats(cells, side):
    """{size: earlier size} for each screen identical to an earlier size's."""
    out = {}
    seen = []
    for size in SIZE_NAMES:
        img = cells.get(size, (None, None))[side]
        if img is None:
            continue
        earlier = next((s for s, e in seen if same_pixels(e, img)), None)
        if earlier:
            out[size] = earlier
        else:
            seen.append((size, img))
    return out


def draw_sheet(rows, sizes, platform, base, head):
    """Draws the before screens of every size, then the after screens.

    rows: [(label, {size: (before, after)})], images or None. An after screen
    the same as its before screen says "No change", and a screen the same as
    an earlier size's on its side says which size it repeats.
    """
    imgs = [img for _, cells in rows for pair in cells.values() for img in pair if img]
    cell_w = max(img.width for img in imgs)
    cell_h = max(max(img.height for img in imgs), 40)
    block_w = len(sizes) * (cell_w + GAP)
    after_x = LABEL_W + block_w + SPLIT
    width = after_x + block_w
    height = HEADER_H + len(rows) * (cell_h + GAP)
    out = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(out)

    default = PLATFORMS.get(platform, (None, None))[1]
    for x, word, color, rev in (
        (LABEL_W, "BEFORE", BEFORE_COLOR, base),
        (after_x, "AFTER", AFTER_COLOR, head),
    ):
        d.text((x, 4), word, fill=color, font=font(15, bold=True))
        d.text(
            (x + d.textlength(word, font=font(15, bold=True)) + 6, 6),
            rev[:9],
            fill="#555555",
            font=font(11),
        )
        for i, size in enumerate(sizes):
            text = size + ("\n(default)" if size == default else "")
            d.multiline_text(
                (x + i * (cell_w + GAP), 24), text, fill="black", font=font(11)
            )
    line_x = LABEL_W + block_w + SPLIT // 2 - 2
    d.line((line_x, 0, line_x, height), fill="#999999", width=2)

    for r, (label, cells) in enumerate(rows):
        y = HEADER_H + r * (cell_h + GAP)
        d.multiline_text(
            (4, y + cell_h / 2),
            label,
            fill="black",
            font=font(12, bold=True),
            anchor="lm",
        )
        same_before, same_after = repeats(cells, 0), repeats(cells, 1)
        for i, size in enumerate(sizes):
            if size not in cells:
                continue
            before, after = cells[size]
            bx = LABEL_W + i * (cell_w + GAP)
            ax = after_x + i * (cell_w + GAP)
            if before is None:
                placeholder(d, (bx, y, bx + cell_w - 1, y + cell_h - 1), "New")
            elif size in same_before:
                text = "Same as\n" + same_before[size]
                placeholder(d, (bx, y, bx + cell_w - 1, y + cell_h - 1), text)
            else:
                out.paste(on_checkerboard(before), (bx, y))
            if after is None:
                placeholder(d, (ax, y, ax + cell_w - 1, y + cell_h - 1), "Removed")
            elif before and same_pixels(before, after):
                placeholder(d, (ax, y, ax + cell_w - 1, y + cell_h - 1), "No change")
            elif size in same_after:
                text = "Same as\n" + same_after[size]
                placeholder(d, (ax, y, ax + cell_w - 1, y + cell_h - 1), text)
            else:
                out.paste(on_checkerboard(after), (ax, y))
    return out


def row_height(cells):
    return max(img.height for pair in cells.values() for img in pair if img) + GAP


def split_rows(rows, rows_per_sheet):
    """Split rows into sheets that share their size columns and stay short.

    Rows with different sizes go on different sheets, so a wide grid doesn't
    widen every column of single screens.
    """
    by_sizes = {}
    for row in rows:
        by_sizes.setdefault(tuple(c for c in COLUMNS if c in row[1]), []).append(row)
    chunks = []
    for group in by_sizes.values():
        chunk, height = [], 0
        for row in group:
            h = row_height(row[1])
            if chunk and (len(chunk) == rows_per_sheet or height + h > MAX_SHEET_H):
                chunks.append(chunk)
                chunk, height = [], 0
            chunk.append(row)
            height += h
        chunks.append(chunk)
    return chunks


def review(base, head, out_dir, rows_per_sheet=ROWS_PER_SHEET):
    old = list_images(base)
    new = list_images(head)
    changed = sorted(n for n in old.keys() | new.keys() if old.get(n) != new.get(n))

    summary = {"base": base, "head": head, "platforms": {}, "files": [], "skipped": []}
    groups = {}
    for name in changed:
        blobs = [b[name] for b in (old, new) if name in b]
        if not name.endswith(RENDERABLE) or not all(loadable(b) for b in blobs):
            summary["skipped"].append(name)
            continue
        platform, screen, _ = split_name(name)
        groups.setdefault(platform, set()).add(screen)

    sheets = []
    for platform in sorted(groups):
        counts = {"changed": 0, "new": 0, "removed": 0}
        shown = shown_sizes(platform)
        rows = []
        for screen in sorted(groups[platform]):
            before_rows, after_rows, files = [], [], []
            for name in sorted(old.keys() | new.keys()):
                p, s, size = split_name(name)
                if p != platform or s != screen or name in summary["skipped"]:
                    continue
                column = dict(SIZES)[size]
                if column not in shown:
                    continue
                before = load(old[name]) if name in old else None
                after = load(new[name]) if name in new else None
                if name in changed:
                    if (
                        before is not None
                        and after is not None
                        and same_pixels(before, after)
                    ):
                        continue
                    kind = (
                        "new"
                        if before is None
                        else "removed"
                        if after is None
                        else "changed"
                    )
                    files.append({"name": name, "change": kind})
                for img, out in ((before, before_rows), (after, after_rows)):
                    if img is None:
                        continue
                    for r, cells in enumerate(screens(img, platform, column)):
                        if r == len(out):
                            out.append({})
                        out[r].update(cells)
            num_rows = max(len(before_rows), len(after_rows))
            shows_change = False
            for r in range(num_rows):
                b = before_rows[r] if r < len(before_rows) else {}
                a = after_rows[r] if r < len(after_rows) else {}
                b, a = expand(b, a), expand(a, b)
                cells = {c: (b.get(c), a.get(c)) for c in (b.keys() | a.keys()) & shown}
                if any(
                    bi is None or ai is None or not same_pixels(bi, ai)
                    for bi, ai in cells.values()
                ):
                    label = row_label(screen)
                    if num_rows > 1:
                        label += f"\nrow {r + 1} of {num_rows}"
                    rows.append((label, cells))
                    shows_change = True
            # Leave out files whose changes are all in hidden sizes
            if shows_change:
                for f in files:
                    counts[f["change"]] += 1
                summary["files"].extend(files)
        if not rows:
            continue
        summary["platforms"][platform] = counts
        chunks = split_rows(rows, rows_per_sheet)
        for k, chunk in enumerate(chunks, 1):
            part = f" ({k}/{len(chunks)})" if len(chunks) > 1 else ""
            sheet = f"{platform}-{k}.png"
            # Only the sizes this sheet's rows have
            sizes = [c for c in COLUMNS if any(c in cells for _, cells in chunk)]
            draw_sheet(chunk, sizes, platform, base, head).save(
                os.path.join(out_dir, sheet)
            )
            sheets.append(
                {"platform": platform, "title": platform + part, "file": sheet}
            )

    summary["sheets"] = sheets
    return summary


def code(name):
    return "`" + (name if SAFE_NAME_RE.match(name) else "(unusual file name)") + "`"


def markdown(summary, base_url="{base_url}"):
    lines = [MARKER, "### Reference image changes", ""]
    if not summary["files"] and not summary["skipped"]:
        lines.append("This pull request no longer changes any reference images.")
        return "\n".join(lines) + "\n"
    lines += [
        (
            f"Images in `{IMAGE_DIR}` at {summary['base'][:9]} (before) and "
            f"{summary['head'][:9]} (after). The Test workflow checks that they "
            "match what the code draws. Only screens with a change are shown."
        ),
        "",
        "| Platform | Changed | New | Removed |",
        "|---|---|---|---|",
    ]
    for platform, c in summary["platforms"].items():
        lines.append(f"| {platform} | {c['changed']} | {c['new']} | {c['removed']} |")
    for sheet in summary["sheets"]:
        lines += [
            "",
            f"**{sheet['title']}**",
            "",
            f"![{sheet['title']}]({base_url}/{sheet['file']})",
        ]
    if summary["files"]:
        lines += ["", f"<details><summary>{len(summary['files'])} files</summary>", ""]
        lines += [f"- {code(f['name'])}: {f['change']}" for f in summary["files"]]
        lines += ["", "</details>"]
    if summary["skipped"]:
        lines += ["", "Changed but not drawn:", ""]
        lines += [f"- {code(n)}" for n in summary["skipped"]]
    return "\n".join(lines) + "\n"


def main():
    global IMAGE_DIR
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("base", help="Base revision; the merge base with head is used")
    p.add_argument(
        "head", nargs="?", default="HEAD", help="Head revision (default: HEAD)"
    )
    p.add_argument("--out", default="image-review", help="Output directory")
    p.add_argument("--rows", type=int, default=ROWS_PER_SHEET, help="Rows per sheet")
    p.add_argument("--image-dir", default=IMAGE_DIR, help="Reference image directory")
    args = p.parse_args()
    IMAGE_DIR = args.image_dir

    base = git("merge-base", args.base, args.head)
    head = git("rev-parse", args.head)
    os.makedirs(args.out, exist_ok=True)
    summary = review(base, head, args.out, args.rows)
    with open(os.path.join(args.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    with open(os.path.join(args.out, "comment.md"), "w") as f:
        f.write(markdown(summary))
    for sheet in summary["sheets"]:
        print(os.path.join(args.out, sheet["file"]))
    if not summary["files"]:
        print("No reference image changes", file=sys.stderr)


if __name__ == "__main__":
    main()
