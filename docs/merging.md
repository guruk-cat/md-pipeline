# Merge Blobs: Algorithm Spec

## 0. Background

This was a feature in BlobTxt, a custom Markdown editor that I've been building. But as part of the app shrinking/refactor, it is being ported out of the app. It will become a dedicated Python-written tool, and below is the spec for building that tool.

## 1. What it does

Combine several markdown files ("blobs") into one new file, in a chosen order, rewriting their headings and footnotes so the result reads as one document:

1. concatenate selected blob bodies in order;
2. adjust heading levels (per-blob and merge-wide), strip manual heading numbers;
3. renumber footnotes into one continuous, blob-aware sequence, gathering all definitions at the foot;
4. optionally apply nested heading numbers (`1.`, `1.1.`, …) across the result.

Front matter is *not* read from the inputs. Only the blob bodies are merged. (BlobTxt no longer strips front matter; if the Python port wants to drop a YAML front-matter block from each input before merging, it must do so itself.)

## 2. Inputs

Per the original config model:

- **selected**: ordered list of input file paths. A file appears at most once.
- **per-blob config** (sparse; absent = all defaults), keyed by file:
  - `adjustBy: Int = 0` — shift this blob's headings by N levels. Positive promotes (toward H1), negative demotes (toward H6).
  - ~~`addHeading: Bool = false`, `addedHeadingText: String = ""`, `addedHeadingLevel: Int = 1`: for a blob with no headings of its own, synthesize one heading and prepend it (see 3.1).~~ No longer planned as part of the refactor.
- **merge-wide config**:
  - `adjustAllBy: Int = 0`: shift *every* heading by N levels, added on top of
    each blob's own `adjustBy`.
  - `renumber: Bool = false`: prepend nested numbers to headings (see 3.4).
  - `numberH1: Bool = false`: include H1 in the numbering hierarchy. Off means the numbering anchors at H2 (so the first H2 is `1.`).
- **output**: base file name (no extension); written as `<name>.md`, de-duplicated against the target dir, at the project root.

## 3. The transform

A heading is stored **number-free** internally: its level is the single source of truth, and a number is reapplied only by the renumbering pass (3.4). "Heading" means an ATX heading (`#`…`######`); see 3.5 for the exact parse.

Fenced code blocks (` ``` ` or `~~~`) are tracked throughout: a `#` inside a code fence is never a heading. A fence opens on a line whose trimmed text starts with the token and closes on the next line starting with the same token.

### 3.1. Pass 1: per blob

For each selected blob, in order:

1. Read its body. Compute `adjust = blob.adjustBy + wide.adjustAllBy`.
2. Walk the lines, tracking fences. For each ATX heading line, recompute its level as `clamp(level - adjust, 1, 6)` and re-emit as `("#" * level) + " " + headingText` where `headingText` is the cleaned text from the parse (3.5: closing `#`s and a leading manual number removed). Non-heading lines and fenced lines pass through verbatim.
3. Trim blank lines off the top and bottom of the result. Drop the blob entirely if nothing remains.

Collect the surviving blobs as `segments` (one string each).

### 3.2. Pass 1.5: footnotes

Run the footnote renumber (section 4) over `segments`. It returns rewritten prose segments and a list of formatted definition blocks. Join the prose segments with a blank line between them (`"\n\n"`).

### 3.3. Pass 2: whole-document headings

Walk the joined document, tracking fences. Collect every heading in order (for a preview/TOC), and, **if `renumber` is on**, prepend nested numbers:

- `base = numberH1 ? 1 : 2`. Headings with `level < base` are left unnumbered.
- For a heading at `level >= base`, its numbering `depth` is `level - base` (0-based). Advance the counters (3.4) and emit `("#" * level) + " " + number + " " + text`.

When `renumber` is off, headings are emitted unchanged from pass 1.

### 3.4. Nested numbering counters

State: a list of integers `counters`, initially empty. To number a heading at `depth` (0-based):

```
if depth < len(counters):
    counters[depth] += 1
    del counters[depth+1:]          # drop deeper levels
else:
    while len(counters) < depth: counters.append(1)   # skipped levels start at 1
    counters.append(1)
return ".".join(map(str, counters)) + "."             # e.g. "1." , "1.1."
```

So a jump from H2 to H4 (skipping H3) yields `1.` then `1.1.1.` with the intermediate level filled by 1. The trailing `.` is always present.

### 3.5. ATX heading parse

A line is a heading iff:

- up to **3** leading spaces, then
- a run of 1–6 `#`, then
- end-of-line **or** a space/tab.

The text is: everything after the `#` run, trimmed; then any **trailing run of `#`** removed (ATX closing sequence); then trimmed; then a **leading manual number** stripped (3.6). Level is the count of `#`.

### 3.6. Stripping a leading manual number

Given heading text, remove a leading number *and the whitespace after it*, returning the bare title. If the result wouldn't be followed by whitespace, the original text is returned unchanged (so `1stPlace` is left alone). Rules:

- Only fires if the first char is a digit.
- **Dotted form**: digit-run, then while the next char is `.` followed by another digit, consume `.`+digits (handles `1`, `1.1`, `2.3.1`). A trailing lone `.` (e.g. `1.`) is consumed as part of the number.
- **Simple terminator**: after the digits, a single `:` or `)` is consumed (handles `2:`, `1)`).
- Then there **must** be a space or tab; consume the run of them. Return the rest. If there's no whitespace, return the original unchanged.

Examples stripped: `1. Intro` → `Intro`, `1.1. A` → `A`, `2.3.1 B` → `B`,
`2: C` → `C`, `1) D` → `D`. Not stripped: `1stPlace`.

## 4. Footnote renumbering (blob-aware)

The point: each blob numbers its own references independently, so `[^1]` in blob A and `[^1]` in blob B are different notes. After merging, every reference gets a unique number, assigned in **document order of first reference across the whole merge**, and all definitions are gathered at the foot.

Regex shapes (mirror the JS command exactly):

- **reference**: `\[\^([^\]]+)\](?!\()` — `[^label]` not immediately followed by
  `(` (so a `[^x](link)` is not treated as a footnote ref).
- **definition line**: `^\[\^([^\]]+)\]:[ \t]?(.*)$` — `[^label]: text`.
- **continuation**: `^[ \t]+\S` — an indented, non-blank line.

Algorithm — `counter = 0`, `definitions = []`, process segments in order:

For each segment:

1. **Collect definitions** by scanning lines top-down. A definition line starts a block: its label, its first-line text (capture group 2), plus following **continuation** lines (each de-indented: leading spaces/tabs stripped). Record first-occurrence order of labels, a `label → [text lines]` map (a repeated label keeps its **last** definition), and the set of line indices that belong to any definition.
2. **Prose** = the segment's lines minus the definition-line indices, rejoined.
3. **Rewrite references** in the prose, left to right. For each `[^label]`:
   - if the label has a definition in this segment and hasn't been assigned yet: `counter += 1`, assign it, and append the formatted definition (4.1) to the global `definitions`;
   - if assigned, replace with `[^<number>]`;
   - if the label has **no definition** in this segment, leave the reference verbatim.
4. **Unreferenced definitions**: for labels defined but never referenced (in first-occurrence order), `counter += 1` and append their formatted definition anyway — nothing is silently dropped.
5. Trim blank top/bottom lines of the rewritten prose; drop the segment if empty.

Return the surviving prose segments and the `definitions` list.

### 4.1. Definition formatting

```
[^<number>]: <first line, trailing whitespace trimmed>
    <continuation 1>          # each continuation re-indented exactly 4 spaces
    <continuation 2>
```

## 5. Assembly

- `body = "\n".join(final lines)` from pass 2.
- If there are any footnote definitions: strip trailing whitespace from `body`, then append `"\n\n" + "\n".join(definitions) + "\n"`.
- Write to `<name>.md` at the project root, de-duplicating the name with a numeric suffix (`name-2.md`, …) if taken.

## 6. One check to port

A round-trip test worth keeping when you write the Python: two blobs that each use `[^1]`/`[^2]` with their own definitions, merged, must produce four distinct footnotes `[^1]`–`[^4]` numbered in reference order, with all four definitions at the foot. That single case exercises the blob-aware renumbering, the document-order assignment, and the definition gathering at once.
