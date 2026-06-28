#!/usr/bin/env python3
"""
Convert a tree of markdown files into a static HTML site.

Runs from the repo root as `.tools/build.py`.
Reads `.md` files recursively, renders them, rewrites internal `.md` links to `.html`.
Wraps each in `template.html`, and writes the mirror tree under `.public/`.
Source files are never modified.
"""

import html as htmllib
import posixpath
import re
import shutil
import tomllib
from pathlib import Path

import markdown

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent          # repo root when deployed as .tools/build.py
OUTPUT = ROOT / ".public"
TEMPLATE = SCRIPT_DIR / "template.html"
STYLE = SCRIPT_DIR / "style.css"
ROBOTS = SCRIPT_DIR / "robots.txt"
CONFIG = SCRIPT_DIR / "config.toml"

EXTENSIONS = ["meta", "toc", "footnotes", "tables", "fenced_code"]

# Rewrite href="...md" / href="...md#anchor" on rendered HTML.
# Matching the href attribute (not raw markdown) skips code blocks and covers reference links automatically.
LINK_RE = re.compile(r"""(href=["'])([^"']*\.md)((?:#[^"']*)?["'])""")
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def make_md():
    return markdown.Markdown(extensions=EXTENSIONS)


def render(md, text):
    # reset() is mandatory: 
    # footnotes/meta state accumulates on the instance and would leak between files otherwise.
    md.reset()
    return md.convert(text)


def rewrite_links(body, page_rel):
    # Rewrite internal `.md` links to root-absolute `.html` URLs.
    # page_rel    : the page's path relative to the output root. 
    page_dir = page_rel.parent.as_posix()

    def repl(m):
        url = m.group(2)
        if re.match(r"[a-z][a-z0-9+.-]*://", url) or url.startswith("//"):
            return m.group(0)  # leave external links alone
        target = posixpath.normpath(posixpath.join(page_dir, url[:-3]))
        href = "/index.html" if target == "README" else "/" + target + ".html"
        return m.group(1) + href + m.group(3)

    return LINK_RE.sub(repl, body)


def pick_title(meta, body, stem, front=None):
    # front: config override for the homepage (README), wins over everything.
    if front:
        return front
    if meta.get("title"):
        return meta["title"][0]
    m = H1_RE.search(body)
    if m:
        return TAG_RE.sub("", m.group(1)).strip()
    return stem


def load_config():
    if not CONFIG.exists():
        return {}
    with CONFIG.open("rb") as f:
        return tomllib.load(f)


def build_footer(cfg):
    # Copyright footer HTML, or empty string if no [copyright] section is configured.

    c = cfg.get("copyright")
    if c is None:
        return ""
    missing = [k for k in ("author", "year", "tag") if not c.get(k)]
    if missing:
        raise SystemExit(f"[copyright] is missing required key(s): {', '.join(missing)}")
    year = htmllib.escape(str(c["year"]))
    author = htmllib.escape(str(c["author"]))
    # tag goes through markdown so it can carry a link (e.g. a license).
    # markdown.markdown wraps output in <p>; strip it since this is inline.
    tag = markdown.markdown(str(c["tag"])).removeprefix("<p>").removesuffix("</p>")
    return f"<footer>Copyright {year}, {author}. {tag}</footer>"


# Persist each folder's open/closed state across page loads.
# Keyed by folder path in localStorage.
NAV_FOLD_SCRIPT = """<script>
(function () {
  var KEY = "navfold";
  var state = JSON.parse(localStorage.getItem(KEY) || "{}");
  document.querySelectorAll(".sidebar details").forEach(function (d) {
    var id = d.dataset.path;
    if (id in state) d.open = state[id];
    d.addEventListener("toggle", function () {
      state[id] = d.open;
      localStorage.setItem(KEY, JSON.stringify(state));
    });
  });
})();
</script>"""


def build_nav(pages):
    # Sidebar HTML as a collapsible tree mirroring the folder structure.

    # tree node: {"files": [(title, out)], "dirs": {name: node}}
    tree = {"files": [], "dirs": {}}
    for out, title in pages:
        node = tree
        for part in out.parent.parts:  # () at root, ("notes",), ("notes","sub"), ...
            node = node["dirs"].setdefault(part, {"files": [], "dirs": {}})
        node["files"].append((title, out))

    def render_node(node, path):
        lines = []
        files = sorted(node["files"], key=lambda t: t[0].lower())
        if files:
            lines.append("<ul>")
            for title, out in files:
                href = "/" + out.as_posix()
                lines.append(f'<li><a href="{href}">{htmllib.escape(title)}</a></li>')
            lines.append("</ul>")
        for name in sorted(node["dirs"]):
            sub = f"{path}/{name}" if path else name
            lines.append(f'<details data-path="{htmllib.escape(sub)}">')
            lines.append(f"<summary>{htmllib.escape(name)}</summary>")
            lines.extend(render_node(node["dirs"][name], sub))
            lines.append("</details>")
        return lines

    out_lines = ['<nav class="sidebar">']
    out_lines.extend(render_node(tree, ""))
    out_lines.append("</nav>")
    out_lines.append(NAV_FOLD_SCRIPT)
    return "\n".join(out_lines)


def build():
    cfg = load_config()
    nav = cfg.get("site-layout", {}).get("nav", False)
    front = cfg.get("site-layout", {}).get("front")
    footer_html = build_footer(cfg)

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)

    template = TEMPLATE.read_text(encoding="utf-8")
    md = make_md()

    # Render every page and collect (output path, title) before writing
    rendered = []  # (out_path, title, body)
    for path in ROOT.rglob("*"):
        # Skip dot-dirs (.tools, .public, .git, ...)
        if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
            continue
        if path.is_dir():
            continue

        rel = path.relative_to(ROOT)
        if path.suffix == ".md":
            out = OUTPUT / rel.with_suffix(".html")
            is_readme = rel == Path("README.md")
            if is_readme:
                out = OUTPUT / "index.html"
            body = rewrite_links(
                render(md, path.read_text(encoding="utf-8")),
                out.relative_to(OUTPUT),
            )
            title = pick_title(md.Meta, body, path.stem, front if is_readme else None)
            rendered.append((out, title, body))
        else:
            # Non-md asset: copy through, preserving structure.
            asset_out = OUTPUT / rel
            asset_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, asset_out)

    nav_html = ""
    if nav:
        nav_html = build_nav([(out.relative_to(OUTPUT), title) for out, title, _ in rendered])

    # Write pages with the shared nav injected.
    for out, title, body in rendered:
        page = (
            template.replace("{{title}}", htmllib.escape(title))
            .replace("{{nav}}", nav_html)
            .replace("{{content}}", body)
            .replace("{{footer}}", footer_html)
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")

    shutil.copy2(STYLE, OUTPUT / "style.css")
    shutil.copy2(ROBOTS, OUTPUT / "robots.txt")
    print(f"built -> {OUTPUT}" + (" (with nav)" if nav else ""))


def selfcheck():
    md = make_md()
    render(md, "First[^1]\n\n[^1]: alpha")
    second = render(md, "Second[^2]\n\n[^2]: bravo")
    assert "alpha" not in second, "footnote leaked between files (reset broken)"
    assert "bravo" in second
    assert pick_title({"title": ["FM"]}, "<h1>H</h1>", "stem", front="Cfg") == "Cfg"
    assert pick_title({"title": ["FM"]}, "<h1>H</h1>", "stem") == "FM"
    assert rewrite_links('<a href="foo.md#x">', Path("index.html")) == '<a href="/foo.html#x">'
    assert rewrite_links('<a href="https://x.md">', Path("index.html")) == '<a href="https://x.md">'
    # ../README.md from a nested page resolves to the homepage (index.html).
    assert rewrite_links('<a href="../README.md">', Path("notes/intro.html")) == '<a href="/index.html">'
    # Sibling link from a nested page stays in its folder.
    assert rewrite_links('<a href="methods.md">', Path("notes/intro.html")) == '<a href="/notes/methods.html">'
    nav = build_nav([
        (Path("index.html"), "Home"),
        (Path("notes/a.html"), "Alpha"),
        (Path("notes/sub/b.html"), "Bravo"),
    ])
    assert '<a href="/notes/a.html">Alpha</a>' in nav
    assert "<summary>notes</summary>" in nav and 'href="/index.html"' in nav
    # Nesting is real: `sub` is a folder inside `notes`, not a flat `notes/sub` label.
    assert "<summary>sub</summary>" in nav and 'data-path="notes/sub"' in nav
    assert "<summary>notes/sub</summary>" not in nav
    assert build_footer({}) == ""
    assert build_footer({"copyright": {"year": 2026, "author": "John Doe", "tag": "CC BY 4.0"}}) == \
        "<footer>Copyright 2026, John Doe. CC BY 4.0</footer>"
    assert build_footer({"copyright": {"year": 2026, "author": "John Doe",
        "tag": "Licensed under [CC BY-NC 4.0](https://example.com)"}}) == \
        '<footer>Copyright 2026, John Doe. Licensed under <a href="https://example.com">CC BY-NC 4.0</a></footer>'
    try:
        build_footer({"copyright": {"author": "John Doe"}})
    except SystemExit:
        pass
    else:
        assert False, "missing copyright keys should fail the build"
    print("selfcheck ok")


if __name__ == "__main__":
    import sys

    if "--selfcheck" in sys.argv:
        selfcheck()
    else:
        build()
