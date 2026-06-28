# How the Website Build Works

## 1. Build Process

Conversion uses the `markdown` library with the `meta`, `toc`, `footnotes`, `tables`, and `fenced_code` extensions. The `toc` extension gives headings IDs so that `#anchor` links resolve.

The root `README.md` becomes the homepage, `index.html`. Every other `.md` file becomes a matching `.html` file, mirroring the source folder structure.

Internal links are rewritten on the rendered HTML (the `href` attribute) rather than the raw markdown, so links inside code blocks are left alone and reference-style links and footnotes are covered. Links become root-absolute, like `/notes/methods.html`, so navigation works from any folder depth. A link that resolves to the root `README.md` maps to `/index.html`.

Page titles, used for the `<title>` tag and for nav link text, resolve in priority order: the frontmatter `title` field, then the first `# H1` heading, then the filename.

Footnotes stay isolated per page. The build resets the markdown parser before each file, since the `footnotes` extension would otherwise leak definitions from one file into the next.

Non-markdown files such as images are copied through to `.public/`, preserving their structure.

Every build is a full clean rebuild: `.public/` is deleted and regenerated from scratch, so renamed or deleted sources leave no orphan HTML behind. For this reason you should never put hand-authored files in `.public/`.

The pipeline never modifies your source files. All rewriting happens on in-memory HTML and is written only under `.public/`.

The template carries a `noindex, nofollow` meta tag, and `robots.txt` is copied to the output root on every build. Both ship with the pipeline in `.tools/`, so they stay versioned with the source rather than hand-maintained. 

## 2. Crawler Protection and Deployment
### 2.1. Background

The pipeline's intended usage target is a private research and notes repoistory, not a high-sensitivity target. The aim is not authentication as an end in itself but keeping bots and crawlers from scraping or indexing the content. Most of that threat (search engines and AI training crawlers like GPTBot, ClaudeBot, and Bytespider) respects `robots.txt` near-universally, so `robots.txt` plus a per-page `noindex` handles it. Adversarial scrapers ignore `robots.txt`, and that category is the only one that would need an auth wall, which the pipeline tool doesn't handle.

### 2.2. robots.txt

`robots.txt` lives in `src/` and is copied to the build output root on every build, so it stays versioned with the source rather than hand-maintained. It blocks all crawlers by default and, following Codeberg's approach, also disallows a list of known AI and search crawlers by name as a belt-and-suspenders layer over the wildcard.

### 2.3. noindex meta tag

The pipeline template at `src/template.html` carries `<meta name="robots" content="noindex, nofollow">`, so every generated page is marked no-index. Like `robots.txt`, this is part of the build rather than a separate system.
