#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Scott Anderson
# SPDX-License-Identifier: Apache-2.0

"""Post a test image review on a pull request.

Updates the review comment, or the review block of the pull request
description, in place. Nothing is posted for a pull request that never
changed a reference image.
"""

import argparse
import json
import os
import re
import urllib.request

MARKER = "<!-- test-image-review -->"
START = "<!-- test-image-review:start -->"
END = "<!-- test-image-review:end -->"
BOT = "github-actions[bot]"


def api(method, path, body=None):
    req = urllib.request.Request(
        "https://api.github.com/" + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
        link = resp.headers.get("Link", "")
    nxt = re.search(r'<https://api\.github\.com/([^>]+)>; rel="next"', link)
    return (json.loads(data) if data else None), (nxt.group(1) if nxt else None)


def find_comment(repo, pr):
    path = f"repos/{repo}/issues/{pr}/comments?per_page=100"
    while path:
        comments, path = api("GET", path)
        for c in comments:
            if c["user"]["login"] == BOT and MARKER in (c["body"] or ""):
                return c["id"]
    return None


def post_comment(repo, pr, review, changed):
    cid = find_comment(repo, pr)
    if cid:
        api("PATCH", f"repos/{repo}/issues/comments/{cid}", {"body": review})
    elif changed:
        api("POST", f"repos/{repo}/issues/{pr}/comments", {"body": review})


def post_description(repo, pr, review, changed):
    body = api("GET", f"repos/{repo}/pulls/{pr}")[0]["body"] or ""
    block = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    new_block = f"{START}\n{review}\n{END}"
    if block.search(body):
        new = block.sub(lambda _: new_block, body, count=1)
    elif changed:
        new = body.rstrip() + "\n\n" + new_block
    else:
        return
    if new != body:
        api("PATCH", f"repos/{repo}/pulls/{pr}", {"body": new})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("review", help="Markdown review with image URLs filled in")
    p.add_argument("summary", help="summary.json from tools/test_image_review.py")
    p.add_argument("--repo", required=True)
    p.add_argument("--pr", type=int, required=True)
    p.add_argument("--mode", choices=["comment", "description"], default="comment")
    args = p.parse_args()

    with open(args.review) as f:
        review = f.read()
    with open(args.summary) as f:
        summary = json.load(f)
    changed = bool(summary["files"] or summary["skipped"])
    post = post_description if args.mode == "description" else post_comment
    post(args.repo, args.pr, review, changed)


if __name__ == "__main__":
    main()
