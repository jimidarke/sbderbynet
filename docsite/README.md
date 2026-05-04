# SBDerbyNet Documentation Site

Source for the mkdocs-built static documentation site.

## Build

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdocs build --strict
```

Output goes to `../website/docs/site/` (served as static files by the PHP web app — see the **Documentation** button on the portal home page).

For local authoring:

```bash
mkdocs serve
```

opens an auto-reloading preview at http://127.0.0.1:8000.

## Editing

- One Markdown file per page under `docs/`.
- Nav order is set in `mkdocs.yml`.
- Image placeholders live in `docs/images/`. Search for `TODO screenshot` to find pages that need real captures.
