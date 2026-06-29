#!/usr/bin/env python3
"""
Merge several markdown files into one, rewriting headings and footnotes.

    python .tools/merge.py a.md b.md c.md -o combined

Concatenates the file bodies in order, strips manual heading numbers, applies
per-file and merge-wide heading shifts, and renumbers footnotes into one
continuous sequence with all definitions gathered at the foot. Optionally
prepends nested heading numbers (--number).

Per-file heading shift is a `:±N` suffix on the path (`b.md:+1` promotes b's
headings one level toward H1, `c.md:-2` demotes two toward H6). Merge-wide
shift is --promote/--demote. The output is written to <name>.md in the current
directory, de-duplicated with a numeric suffix if the name is taken.
"""

import argparse
import re
from pathlib import Path

FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
ATX_RE = re.compile(r"^ {0,3}(#{1,6})(?=[ \t]|$)(.*)$")

REF_RE = re.compile(r"\[\^([^\]]+)\](?!\()")
DEF_RE = re.compile(r"^\[\^([^\]]+)\]:[ \t]?(.*)$")
CONT_RE = re.compile(r"^[ \t]+\S")

POS_RE = re.compile(r"^(.*):([+-]\d+)$")


def clamp(n, lo, hi):
    return max(lo, min(hi, n))


def strip_number(text):
    # Remove a leading manual heading number and the whitespace after it.
    # Returns the text unchanged unless a number is immediately followed by
    # whitespace, so "1stPlace" is left alone but "1. Intro" becomes "Intro".
    if not text or not text[0].isdigit():
        return text
    i, n = 0, len(text)
    while i < n and text[i].isdigit():
        i += 1
    while i + 1 < n and text[i] == "." and text[i + 1].isdigit():
        i += 1
        while i < n and text[i].isdigit():
            i += 1
    if i < n and text[i] == ".":
        i += 1
    elif i < n and text[i] in ":)":
        i += 1
    if i < n and text[i] in " \t":
        while i < n and text[i] in " \t":
            i += 1
        return text[i:]
    return text


def parse_heading(line):
    # Returns (level, cleaned_text) for an ATX heading, else None. Fence
    # tracking is the caller's job; this only decides the shape of one line.
    m = ATX_RE.match(line)
    if not m:
        return None
    level = len(m.group(1))
    text = m.group(2).strip()
    text = re.sub(r"#+$", "", text).strip()
    return level, strip_number(text)


def strip_frontmatter(text):
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                return "\n".join(lines[j + 1:])
    return text


def trim_blank(text):
    lines = text.split("\n")
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()
    return "\n".join(lines)


def adjust_segment(body, adjust):
    out, fence = [], None
    for line in body.split("\n"):
        fm = FENCE_RE.match(line)
        if fm:
            tok = fm.group(1)[0]
            fence = tok if fence is None else (None if tok == fence else fence)
            out.append(line)
            continue
        if fence:
            out.append(line)
            continue
        parsed = parse_heading(line)
        if parsed:
            level, text = parsed
            level = clamp(level - adjust, 1, 6)
            out.append("#" * level + " " + text)
        else:
            out.append(line)
    return trim_blank("\n".join(out))


def format_def(label, text_lines):
    out = [f"[^{label}]: {text_lines[0].rstrip()}"]
    for cont in text_lines[1:]:
        out.append("    " + cont)
    return "\n".join(out)


def renumber_footnotes(segments):
    # Blob-aware: each segment resolves references against its own definitions,
    # so identical labels in different segments are distinct notes. A reference
    # with no definition in its segment is stripped; a definition never
    # referenced is kept under a separate [^no-ref-N] label.
    counter = noref_counter = 0
    definitions = []
    out_segments = []
    for seg in segments:
        lines = seg.split("\n")
        defs, order, def_idx = {}, [], set()
        i, n = 0, len(lines)
        while i < n:
            m = DEF_RE.match(lines[i])
            if not m:
                i += 1
                continue
            label, text_lines = m.group(1), [m.group(2)]
            def_idx.add(i)
            j = i + 1
            while j < n and CONT_RE.match(lines[j]):
                text_lines.append(lines[j].lstrip(" \t"))
                def_idx.add(j)
                j += 1
            if label not in defs:
                order.append(label)
            defs[label] = text_lines
            i = j

        prose = "\n".join(lines[k] for k in range(n) if k not in def_idx)
        assigned = {}

        def repl(mo):
            nonlocal counter
            label = mo.group(1)
            if label not in defs:
                return ""
            if label not in assigned:
                counter += 1
                assigned[label] = counter
                definitions.append(format_def(counter, defs[label]))
            return f"[^{assigned[label]}]"

        prose = REF_RE.sub(repl, prose)

        for label in order:
            if label not in assigned:
                noref_counter += 1
                definitions.append(format_def(f"no-ref-{noref_counter}", defs[label]))

        prose = trim_blank(prose)
        if prose.strip():
            out_segments.append(prose)
    return out_segments, definitions


def advance_counters(counters, depth):
    if depth < len(counters):
        counters[depth] += 1
        del counters[depth + 1:]
    else:
        while len(counters) < depth:
            counters.append(1)
        counters.append(1)
    return ".".join(map(str, counters)) + "."


def number_headings(doc, renumber, number_h1):
    if not renumber:
        return doc
    base = 1 if number_h1 else 2
    out, fence, counters = [], None, []
    for line in doc.split("\n"):
        fm = FENCE_RE.match(line)
        if fm:
            tok = fm.group(1)[0]
            fence = tok if fence is None else (None if tok == fence else fence)
            out.append(line)
            continue
        if fence:
            out.append(line)
            continue
        parsed = parse_heading(line)
        if parsed and parsed[0] >= base:
            level, text = parsed
            num = advance_counters(counters, level - base)
            out.append("#" * level + " " + num + " " + text)
        else:
            out.append(line)
    return "\n".join(out)


def merge(files, adjust_all, renumber, number_h1):
    segments = []
    for path, adj in files:
        body = strip_frontmatter(Path(path).read_text(encoding="utf-8"))
        seg = adjust_segment(body, adj + adjust_all)
        if seg.strip():
            segments.append(seg)

    prose_segments, definitions = renumber_footnotes(segments)
    doc = number_headings("\n\n".join(prose_segments), renumber, number_h1)

    body = doc
    if definitions:
        body = body.rstrip() + "\n\n" + "\n".join(definitions) + "\n"
    if not body.endswith("\n"):
        body += "\n"
    return body


def parse_positional(token):
    m = POS_RE.match(token)
    if m:
        return m.group(1), int(m.group(2))
    return token, 0


def write_output(name, body):
    out = Path.cwd() / f"{name}.md"
    i = 2
    while out.exists():
        out = Path.cwd() / f"{name}-{i}.md"
        i += 1
    out.write_text(body, encoding="utf-8")
    return out


def run(argv):
    p = argparse.ArgumentParser(description="Merge markdown files into one.")
    p.add_argument("files", nargs="+", metavar="PATH[:±N]")
    p.add_argument("--promote", type=int, default=0, metavar="N")
    p.add_argument("--demote", type=int, default=0, metavar="N")
    p.add_argument("--number", action="store_true")
    p.add_argument("--number-h1", dest="number_h1", action="store_true")
    p.add_argument("-o", "--output", default="merged")
    args = p.parse_args(argv)

    files = [parse_positional(t) for t in args.files]
    for path, _ in files:
        if not Path(path).is_file():
            raise SystemExit(f"not a file: {path}")

    body = merge(
        files,
        adjust_all=args.promote - args.demote,
        renumber=args.number or args.number_h1,
        number_h1=args.number_h1,
    )
    out = write_output(args.output, body)
    print(f"merge -> {out}")


def selfcheck():
    # Round-trip: two blobs each using [^1]/[^2] must merge to four 
    # distinct footnotes in reference order, all defined at the foot.
    a = "Text A[^1] more[^2].\n\n[^1]: def a1\n[^2]: def a2"
    b = "Text B[^1] more[^2].\n\n[^1]: def b1\n[^2]: def b2"
    segs, defs = renumber_footnotes([adjust_segment(a, 0), adjust_segment(b, 0)])
    joined = "\n\n".join(segs)
    assert "Text A[^1] more[^2]." in joined
    assert "Text B[^3] more[^4]." in joined
    assert defs == [
        "[^1]: def a1", "[^2]: def a2", "[^3]: def b1", "[^4]: def b2",
    ]

    assert strip_number("1. Intro") == "Intro"
    assert strip_number("1.1. A") == "A"
    assert strip_number("2.3.1 B") == "B"
    assert strip_number("2: C") == "C"
    assert strip_number("1) D") == "D"
    assert strip_number("1stPlace") == "1stPlace"

    # Heading shift, manual-number strip, and fenced `#` left alone.
    seg = adjust_segment("## 2. Apples\n\n```\n# not a heading\n```\n", 1)
    assert seg.startswith("# Apples")
    assert "# not a heading" in seg

    # Nested numbering: H2 then H4 fills the skipped level with 1.
    doc = number_headings("## A\n\n#### B", renumber=True, number_h1=False)
    assert doc == "## 1. A\n\n#### 1.1.1. B"

    # numberH1 anchors the hierarchy at H1.
    doc = number_headings("# A\n\n## B", renumber=True, number_h1=True)
    assert doc == "# 1. A\n\n## 1.1. B"

    # Reference with no definition is stripped; orphan definition is relabeled.
    segs, defs = renumber_footnotes(["see[^x] here\n\n[^y]: orphan"])
    assert segs == ["see here"]
    assert defs == ["[^no-ref-1]: orphan"]

    print("selfcheck ok")


if __name__ == "__main__":
    import sys

    if "--selfcheck" in sys.argv:
        selfcheck()
    else:
        run(sys.argv[1:])
