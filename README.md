# Markdown Tools

## 1. About

This repo hosts a set of custom-built tools for managing Markdown files. Its primary purposes are as follows:

1. Convert a bunch of Markdown files into a static website.
2. Merge files that have numbered headings and/or footnotes.
3. Generate and append tables of contents.

This repo (`md-tools/`) is where the tools are developed; it is not intended as the place where you use it. The tools lives in `src/` and gets copied into your own repo as `.tools/` (see [section 2.2.](#22-set-up-the-tools-in-your-repo)). A `dummy-repo/` is included here for local testing.

## 2. General Usage
### 2.1. Set up the tools in your repo

Run:

```sh
python setup-tools.py /path/to/your-repo
```

This will overwrite any existing `.tools/`, so re-running pushes the latest pipeline. It also ensures `.gitignore` excludes `.public/`. The `config.toml` file, if present, will *not* be overwritten by the script.

### 2.2. Expected layout

After setup, your repo will look something like this:

```
repo-root/
    README.md           ← used as homepage content
    some-docs/
        *.md
        *.png           ← non-md assets okay
    some-other-docs/
        *.md
    .tools/             ← tools source
        build.py
        config.toml
        requirements.txt
        template.html
        style.css
        robots.txt
        ...
    .public/            ← build output, made by build.py
    .gitignore
```

The `.tools/` and `.public/` directories are dot-prefixed to keep them out of a markdown editor's file view. The `.gitignore` must exclude `.public/`, such that the output of the website pipeline is never committed. (The intended usage is that the script is run on the server-side, to generate its own `.public` output.) The `setup-tools.py` script adds this exclusion for you.

## 3. Website Pipeline
### 3.1. Build

Run from your repo root:

```sh
python .tools/build.py
```

Site preferences (sidebar nav, copyright footer) live in `.tools/config.toml`; see the [configuration docs](docs/config.md). Pass `--selfcheck` to run the pipeline's internal checks without building anything.

### 3.2. Serving locally

The site is served from `.public/`, which is the web root. You must serve from inside it so the root-absolute links resolve.

```sh
cd your-repo/.public && python3 -m http.server 8000
```

Then go to http://localhost:8000/

### 3.3. Deploy on a Romote Host (e.g., Netlify, Cloudflare, or your own server)

Set the build command to `pip install -r .tools/requirements.txt && python .tools/build.py`. Set the output directory to `.public`, typed exactly.

Dependencies are pinned to exact versions in `requirements.txt`, so the build container cannot silently pull an untested version of the markdown library.

### 3.4. How the build works

See the [relevant documentation](docs/web-build.md).

## 4. File Merger

## 5. TOC Generator
