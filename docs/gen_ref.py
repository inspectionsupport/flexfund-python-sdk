"""Build the docs site's generated pages (run by mkdocs-gen-files).

* ``index.md`` is the README, with its repo-relative links rewritten for the site.
* ``changelog.md`` is CHANGELOG.md.
* ``reference/`` has one page per public module, found on disk, so a newly generated
  resource, model or enum shows up without touching this file.
"""

from pathlib import Path

import mkdocs_gen_files

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

readme = (ROOT / "README.md").read_text()
readme = readme.replace("](docs/scopes.md)", "](scopes.md)").replace(
    "](CHANGELOG.md)", "](changelog.md)"
)
with mkdocs_gen_files.open("index.md", "w") as f:
    f.write(readme)

with mkdocs_gen_files.open("changelog.md", "w") as f:
    f.write((ROOT / "CHANGELOG.md").read_text())

# (section, package or module path relative to src/flexfund); "" section = top level.
SECTIONS = {
    "Clients": ["client", "config", "errors", "fastapi"],
    "Auth": ["auth"],
    "Resources": ["resources"],
    "Models": ["models"],
    "Enums": ["enums"],
}

nav_lines = ["* [Overview](index.md)"]

for section, entries in SECTIONS.items():
    nav_lines.append(f"* {section}")
    for entry in entries:
        base = SRC / "flexfund" / entry
        if base.is_dir():
            files = sorted(p for p in base.glob("*.py") if p.name != "__init__.py")
            modules = [f"flexfund.{entry}.{p.stem}" for p in files]
        else:
            modules = [f"flexfund.{entry}"]
        for module in modules:
            doc_path = "reference/" + module.removeprefix("flexfund.").replace(".", "/") + ".md"
            with mkdocs_gen_files.open(doc_path, "w") as f:
                f.write(f"::: {module}\n")
            title = module.rsplit(".", 1)[-1]
            rel = doc_path.removeprefix("reference/")
            nav_lines.append(f"    * [{title}]({rel})")

# Package-level API (FlexFundClient, error classes, ...) first.
with mkdocs_gen_files.open("reference/index.md", "w") as f:
    f.write("# API reference\n\n::: flexfund\n    options:\n      show_submodules: false\n")
nav_lines.insert(1, "* [Package](index.md)")

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as f:
    f.write("\n".join(nav_lines) + "\n")
