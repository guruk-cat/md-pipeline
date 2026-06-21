# Markdown Pipeline for Static Websites

## 1. About

This is a basic pipeline, written in Python, for converting a bunch of markdown files into html files while retaining their folder structures. Use it for generating static sites from a repository of writing and/or research material that uses Markdown.

It is deliberately minimal: small enough to fully own and maintain solo, with no theme or plugin ecosystem to track. It does not try to be MkDocs.

This repo (`md-site/`) is where the pipeline is developed. It is not where you use it. The pipeline lives in `src/` and gets copied into your own research repo as `.tools/`. A `dummy-repo/` is included here for local testing.

## 2. Repository layout

After setup, your research repo will look something like this:

```
repo-root/
    README.md           ← used as homepage content
    some-docs/          ← research content dirs live at repo root; this is flexible.
        *.md            ← research content
    some-other-docs/
        *.md
    assets/             ← images and other non-md files
    .tools/             ← pipeline code
        build.py
        requirements.txt
        template.html
        style.css
    .public/            ← build output
    .gitignore
```

The `.tools/` and `.public/` directories are dot-prefixed to keep them out of a markdown editor's file view.

The `.gitignore` must exclude `.public/`, such that the output of the pipeline is never committed. The host (e.g. Cloudflare Pages) runs the script and generates its own `.public/` fresh on every deploy. The `setup-tools.py` script adds this exclusion for you.

## 3. Usage
### 3.1. Set up the tool in your repo

First, you must copy the pipeline (`src/`) into your research repo as `.tools/`. Imagining that you have a `dummy-repo/` in use, run:

```sh
python setup-tools.py /path/to/dummy-repo
```

This will overwrite any existing `.tools/`, so re-running pushes the latest pipeline. It also ensures `.gitignore` excludes `.public/`.

### 3.2. Build

Run the build from your research repo root.

```sh
python .tools/build.py
```

Pass `--nav` to generate a sidebar navigation from the folder structure. Pass `--selfcheck` to run the pipeline's internal checks without building anything.

### 3.3. Serving locally

The site is served from `.public/`, which is the web root. You must serve from inside it so the root-absolute links resolve.

```sh
cd dummy-repo/.public && python3 -m http.server 8000
```

Then go to http://localhost:8000/

### 3.4. Deploy on Cloudflare Pages

Host the research repo on GitHub (private) and connect it to Cloudflare Pages via the standard "Connect to Git" flow. It will auto-build on every push to main.

Set the build command to `pip install -r .tools/requirements.txt && python .tools/build.py`, adding `--nav` if you want the sidebar. Set the output directory to `.public`, typed exactly; Cloudflare handles the dot prefix fine.

Lock the deployed site down with a Cloudflare Access policy. Note that the private repo and the unlisted site are two separate locks.

## 4. How the build works

Conversion uses the `markdown` library with the `meta`, `toc`, `footnotes`, `tables`, and `fenced_code` extensions. The `toc` extension gives headings IDs so that `#anchor` links resolve.

The root `README.md` becomes the homepage, `index.html`. Every other `.md` file becomes a matching `.html` file, mirroring the source folder structure.

Internal links are rewritten on the rendered HTML (the `href` attribute) rather than the raw markdown, so links inside code blocks are left alone and reference-style links and footnotes are covered. Links become root-absolute, like `/notes/methods.html`, so navigation works from any folder depth. A link that resolves to the root `README.md` maps to `/index.html`.

Page titles, used for the `<title>` tag and for nav link text, resolve in priority order: the frontmatter `title` field, then the first `# H1` heading, then the filename.

Footnotes stay isolated per page. The build resets the markdown parser before each file, since the `footnotes` extension would otherwise leak definitions from one file into the next.

Non-markdown files such as images are copied through to `.public/`, preserving their structure.

Every build is a full clean rebuild: `.public/` is deleted and regenerated from scratch, so renamed or deleted sources leave no orphan HTML behind. For this reason you should never put hand-authored files in `.public/`.

The pipeline never modifies your source files. All rewriting happens on in-memory HTML and is written only under `.public/`.

Dependencies are pinned to exact versions in `requirements.txt`, so the build container cannot silently pull an untested version of the markdown library.

## 5. Out of scope

There is no search, versioning, internationalization, or theming system. Nested folders in the generated nav render as flat labeled groups rather than an indented tree. Any of these can be added later if the need arises.
