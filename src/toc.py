#!/usr/bin/env python3
"""
Insert a table of contents into a markdown file, in place.

    python .tools/toc.py path/to/file.md

Inserts a TOC under the topmost H1 (or at the top, below YAML frontmatter, if
there is no H1), and rewrites it on re-run.

Anchors default to the website builder's scheme (Python-Markdown's `toc`
slugify) so the same links resolve on the built site; set slug_style="github"
in [toc-builder] for raw GitHub/editor viewing instead.
"""

import re
import tomllib
from pathlib import Path

from markdown.extensions.toc import slugify, unique

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG = SCRIPT_DIR / "config.toml"

TOC_OPEN = "<!-- toc -->"
TOC_CLOSE = "<!-- /toc -->"

FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
# ATX heading: 1-6 hashes, space, text, optional trailing hashes.
ATX_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def load_config():
    if not CONFIG.exists():
        return {}
    with CONFIG.open("rb") as f:
        return tomllib.load(f)


def github_slug(text):
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"\s+", "-", s)


def assign_ids(headings, slug_style):
    # Assign anchor ids over ALL headings in document order so collisions
    # dedupe exactly as the renderer sees them. Returns a parallel list of ids.
    ids = set()
    out = []
    for _level, text, _idx in headings:
        if slug_style == "github":
            base = github_slug(text)
            sid, i = base, 0
            while sid in ids or not sid:
                i += 1
                sid = f"{base}-{i}"
            ids.add(sid)
        else:
            sid = unique(slugify(text, "-"), ids)
        out.append(sid)
    return out


def parse_headings(lines):
    # ATX headings outside fenced code; skips a leading `---`...`---` frontmatter.
    # Returns ([(level, text, line_index)], content_start_index).
    start = 0
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                start = j + 1
                break
    headings = []
    fence = None
    for idx in range(start, len(lines)):
        line = lines[idx]
        m = FENCE_RE.match(line)
        if m:
            tok = m.group(1)[0]
            if fence is None:
                fence = tok
            elif tok == fence:
                fence = None
            continue
        if fence:
            continue
        h = ATX_RE.match(line)
        if h:
            headings.append((len(h.group(1)), h.group(2).strip(), idx))
    return headings, start


def strip_existing(lines):
    # Remove a previously generated block (markers inclusive) plus the single
    # blank line we pad it with on each side, so re-runs converge.
    out, i, n = [], 0, len(lines)
    while i < n:
        if lines[i].strip() == TOC_OPEN:
            if out and out[-1].strip() == "":
                out.pop()
            while i < n and lines[i].strip() != TOC_CLOSE:
                i += 1
            i += 1  # skip the close marker
            if i < n and lines[i].strip() == "":
                i += 1  # skip trailing pad
            continue
        out.append(lines[i])
        i += 1
    return out


def render_block(listed, title):
    if not listed:
        return []
    min_level = min(level for level, _, _ in listed)
    out = [TOC_OPEN, f"## {title}"]
    for level, text, sid in listed:
        indent = "  " * (level - min_level)
        out.append(f"{indent}- [{text}](#{sid})")
    out.append(TOC_CLOSE)
    return out


def build_toc(text, cfg):
    toc_cfg = cfg.get("toc-builder", {})
    max_depth = toc_cfg.get("max_depth", 6)
    slug_style = toc_cfg.get("slug_style", "site")
    title = toc_cfg.get("toc_title", "Table of Contents")

    had_final_nl = text.endswith("\n")
    lines = text.split("\n")
    if had_final_nl:
        lines = lines[:-1]

    lines = strip_existing(lines)
    headings, start = parse_headings(lines)

    result = lines
    if headings:
        sids = assign_ids(headings, slug_style)

        # Insert under the topmost H1; exclude that H1 from its own TOC.
        insert_idx, title_idx = start, None
        for level, _text, idx in headings:
            if level == 1:
                title_idx, insert_idx = idx, idx + 1
                break

        listed = [
            (level, htext, sid)
            for (level, htext, idx), sid in zip(headings, sids)
            if level <= max_depth and idx != title_idx
        ]
        block = render_block(listed, title)
        if block:
            lead = [] if insert_idx == 0 else [""]
            result = lines[:insert_idx] + lead + block + [""] + lines[insert_idx:]

    s = "\n".join(result)
    return s + "\n" if had_final_nl else s


def run(target):
    path = Path(target)
    if not path.is_file():
        raise SystemExit(f"not a file: {target}")
    text = path.read_text(encoding="utf-8")
    new = build_toc(text, load_config())
    if new == text:
        print(f"unchanged: {target}")
        return
    path.write_text(new, encoding="utf-8")
    print(f"toc -> {target}")


def selfcheck():
    doc = (
        "---\ntitle: t\n---\n\n"
        "# Title\n\n"
        "## 1. Introduction\ntext\n"
        "### 1.1. Some idea\n\n"
        "```\n# not a heading\n```\n\n"
        "## 2. Whoo\n"
    )
    out = build_toc(doc, {})
    assert "## Table of Contents" in out
    assert "- [1. Introduction](#1-introduction)" in out
    assert "  - [1.1. Some idea](#11-some-idea)" in out
    assert "- [2. Whoo](#2-whoo)" in out
    assert "[Title]" not in out                 # H1 excluded from its own TOC
    assert "not a heading]" not in out          # fenced `#` is not a heading
    assert out.index("Table of Contents") < out.index("## 1. Introduction")
    assert build_toc(out, {}) == out            # idempotent

    # max_depth caps which headings are listed (ids still assigned to all).
    shallow = build_toc(doc, {"toc-builder": {"max_depth": 2}})
    assert "Some idea" not in shallow.split(TOC_CLOSE)[0]

    # Duplicate headings: site uses `_1`, github uses `-1`.
    dup = "# T\n\n## Intro\n\n## Intro\n"
    site = build_toc(dup, {})
    gh = build_toc(dup, {"toc-builder": {"slug_style": "github"}})
    assert "(#intro)" in site and "(#intro_1)" in site
    assert "(#intro)" in gh and "(#intro-1)" in gh

    # No H1: insert at top, below frontmatter, no leading blank growth.
    nohdr = "## A\n\n## B\n"
    o1 = build_toc(nohdr, {})
    assert o1.startswith(TOC_OPEN)
    assert build_toc(o1, {}) == o1

    # custom title
    assert "## Contents" in build_toc(doc, {"toc-builder": {"toc_title": "Contents"}})
    print("selfcheck ok")


if __name__ == "__main__":
    import sys

    if "--selfcheck" in sys.argv:
        selfcheck()
    elif len(sys.argv) == 2:
        run(sys.argv[1])
    else:
        raise SystemExit("usage: toc.py path/to/file.md")
