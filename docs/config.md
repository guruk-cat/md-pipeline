# Configuration Dictionary

## 1. Usage

The setup script (`setup-tools.py`) includes a scaffoleded `config.toml` in the `.tools/` directory of the target repo. You can edit this, and the build script (`build.py`) will respect preferences.

## 2. Keys for the website builder

### 2.1. `[site-layout]` section

Used to configure layout options.

- `nav`: if true, generates a sidebar navigation from the folder structure. Defaults to false.

### 2.2. `[copyright]` section

A copyright footer is generated if section is present. When present, all three keys are required; a missing key fails the build.

- `author`
- `year`
- `tag`: something like "C.C. by 4.0" or "All rights reserved."

Output: "Copyright <year>, <author>. <tag>"

## 3. Keys for file merging

## 4. Keys for TOC building

### 4.1. `[toc-builder]` section

Options for the standalone TOC builder (`toc.py`), which inserts a table of contents into each `.md` file in place (under the topmost H1, or at the top below YAML frontmatter if there is no H1). Re-running rewrites the existing TOC rather than stacking a new one. This is separate from the website build.

- `max_depth`: deepest heading level to list. Defaults to 6.
- `slug_style`: anchor scheme. `"site"` (default) matches the slugs the website builder generates, so links work on the built site. `"github"` matches GitHub's raw `.md` rendering instead. They differ mainly on duplicate headings (`_1` vs `-1`).
- `toc_title`: heading text for the generated TOC. Defaults to "Table of Contents".
