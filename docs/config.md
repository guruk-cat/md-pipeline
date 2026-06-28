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
