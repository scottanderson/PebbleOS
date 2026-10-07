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
SIZE_RE = re.compile(r"^(.*?)(_extra_large|_large|_medium|_small)?$")
PLATFORM_RE = re.compile(r"^([a-z0-9]+)(.*)$")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_.~+-]+$")

ROWS_PER_SHEET = 30
# Tallest sheet worth showing in a comment, unless one row is taller
MAX_SHEET_H = 3000
GAP = 8
PAIR_GAP = 24
LABEL_W = 180
HEADER_H = 64
BEFORE_COLOR = "#c00000"
AFTER_COLOR = "#007000"


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
    return img.convert("RGB")


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


def same_pixels(a, b):
    return a.size == b.size and a.tobytes() == b.tobytes()


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def row_label(screen):
    """Show test_<suite>__<case>.png as the suite over the case."""
    stem = os.path.splitext(screen)[0]
    stem = stem.removeprefix("test_")
    suite, sep, case = stem.partition("__")
    return wrap(suite, 20) + "\n" + wrap(case, 20) if sep else wrap(stem, 20)


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
    f = font(16)
    w = draw.textlength(text, font=f)
    draw.text(((x0 + x1 - w) / 2, (y0 + y1) / 2 - 9), text, font=f, fill="#666666")


def draw_sheet(rows, sizes, title):
    """rows: [(label, {size: (before, after)})], images or None."""
    cell_w = max(
        img.width for _, cells in rows for pair in cells.values() for img in pair if img
    )
    cell_h = max(
        img.height
        for _, cells in rows
        for pair in cells.values()
        for img in pair
        if img
    )
    cell_h = max(cell_h, 40)
    pair_w = 2 * cell_w + GAP
    width = LABEL_W + len(sizes) * (pair_w + PAIR_GAP)
    height = HEADER_H + len(rows) * (cell_h + GAP)
    out = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(out)
    d.text((6, 6), title, font=font(18), fill="black")
    for i, size in enumerate(sizes):
        x = LABEL_W + i * (pair_w + PAIR_GAP)
        d.text((x, 6), dict(SIZES)[size], font=font(18), fill="black")
        d.text((x, 36), "Before", font=font(16), fill=BEFORE_COLOR)
        d.text((x + cell_w + GAP, 36), "After", font=font(16), fill=AFTER_COLOR)
        if i:
            sx = x - PAIR_GAP // 2
            d.line([(sx, 4), (sx, height)], fill="#888888", width=2)
    for r, (label, cells) in enumerate(rows):
        y = HEADER_H + r * (cell_h + GAP)
        d.multiline_text((6, y + 4), row_label(label), font=font(14), fill="black")
        for i, size in enumerate(sizes):
            if size not in cells:
                continue
            before, after = cells[size]
            x = LABEL_W + i * (pair_w + PAIR_GAP)
            bx = (x, y, x + cell_w - 1, y + cell_h - 1)
            ax = (x + cell_w + GAP, y, x + 2 * cell_w + GAP - 1, y + cell_h - 1)
            if before:
                out.paste(before, bx[:2])
            else:
                placeholder(d, bx, "New")
            if after is None:
                placeholder(d, ax, "Removed")
            elif before and same_pixels(before, after):
                placeholder(d, ax, "No change")
            else:
                out.paste(after, ax[:2])
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
        by_sizes.setdefault(tuple(s for s, _ in SIZES if s in row[1]), []).append(row)
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
        rows = []
        for screen in sorted(groups[platform]):
            cells = {}
            for name in sorted(old.keys() | new.keys()):
                p, s, size = split_name(name)
                if p != platform or s != screen or name in summary["skipped"]:
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
                    counts[kind] += 1
                    summary["files"].append({"name": name, "change": kind})
                cells[size] = (before, after)
            if any(
                b is None or a is None or not same_pixels(b, a)
                for b, a in cells.values()
            ):
                rows.append((screen, cells))
        if not rows:
            continue
        summary["platforms"][platform] = counts
        chunks = split_rows(rows, rows_per_sheet)
        for k, chunk in enumerate(chunks, 1):
            part = f" ({k}/{len(chunks)})" if len(chunks) > 1 else ""
            sheet = f"{platform}-{k}.png"
            # Only the sizes this sheet's rows have
            sizes = [s for s, _ in SIZES if any(s in cells for _, cells in chunk)]
            draw_sheet(chunk, sizes, platform + part).save(os.path.join(out_dir, sheet))
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
