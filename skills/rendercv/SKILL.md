---
name: rendercv
description: Create, validate, and render the repository's disposable resume YAML using the official RenderCV v2.8 contract and CLI.
---

# RenderCV Contract

RenderCV is the only final resume schema validator and PDF renderer in this repository. The repository pins `rendercv[full]==2.8` in `pyproject.toml`; update that pin and the schema URL together.

The canonical official schema URL is:

```text
https://raw.githubusercontent.com/rendercv/rendercv/refs/tags/v2.8/schema.json
```

## Required shape

- Top-level fields: `cv`, with optional `design`, `locale`, and `settings`.
- `cv.sections` maps arbitrary section titles to homogeneous entry lists.
- Experience entries use `company` and `position`.
- Education entries use `institution` and `area`.
- Project/normal entries use `name`.
- Skill/one-line entries use `label` and `details`.
- Narrative bullets use `highlights`.
- Dates use `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`; RenderCV accepts `end_date: present`.

Do not recreate these models locally. When uncertain, inspect the official schema or install the official generated agent skill from `rendercv/rendercv-skill`.

## Commands

```bash
# Pydantic/schema validation without generating output
uv run --extra render career validate-resume applications/<id>/resume.yaml

# Validate provenance, render only the PDF, extract text, and record validation
uv run --extra render career render applications/<id>
```

The underlying validation command disables every output format. PDF rendering requires RenderCV's Typst intermediate, so the wrapper writes that intermediate to a temporary directory, invokes `rendercv render` with an explicit PDF path, and retains only the PDF. Never route the primary workflow through browser printing, Puppeteer, wkhtmltopdf, or a custom layout engine.
