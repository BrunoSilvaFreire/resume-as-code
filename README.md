# Resume as Code

A local, Git-tracked career knowledge base for repository-aware agents. Maintain detailed career evidence once in modular Markdown records; let an agent retrieve public claims for a job; produce a disposable, audited [RenderCV](https://rendercv.com/) YAML document and PDF.

RenderCV v2.8 owns final schema validation, typography, pagination, and PDF rendering. This repository does not contain a competing resume layout engine or require a hosted LLM API.

## Architecture

```text
career/ Markdown + profile YAML (canonical)
  -> requirements.yaml (JD analysis)
  -> deterministic metadata retrieval + agent semantic review
  -> resume.yaml + claim-manifest.yaml (application-specific)
  -> RenderCV Pydantic validation
  -> RenderCV/Typst PDF
  -> extracted-text, page-count, provenance, and quality review
```

The source model and output model are intentionally separate:

| Canonical career records | Disposable RenderCV application |
| --- | --- |
| Complete technical context and private boundaries | Concise claims for one role |
| Stable record and claim IDs | RenderCV `cv`/`design`/`locale`/`settings` |
| Evidence, confidence, alternate framings | Limited page count and deterministic layout |
| Reused across applications | Regenerated when facts or JD change |

## Repository structure

```text
career/                     personal canonical data (empty in the public starter)
  profile/profile.yaml      contact, education, certificates
  experience/               company, role, initiative, decision, incident records
  projects/                 independent/cross-role project records
  knowledge/                reusable context and references
  evidence/                 sources supporting claims
  index.md                  generated faceted links, never canonical facts
applications/<id>/          one complete job-application audit trail
config/resume-variants.yaml role-family presentation defaults
schemas/                    record, profile, JD-analysis, and manifest contracts
career_kb/                  small deterministic CLI
skills/                     portable agent workflows
examples/demo/              fictional end-to-end rehearsal corpus
docs/                       schema, migration, and operating runbook
job-search/                 LinkedIn discovery workflow and reusable platform research
  README.md                 search, triage, save, and promote workflow
  <date>-search.md          per-run shortlists (gitignored)
  <date>-external-platforms.md  non-LinkedIn boards, sponsors, and search strategies
.opencode/opencode.json     project-scoped MCP config (LinkedIn save_job fork)
```

Personal records under `career/`, individual `applications/<id>/` artifacts, and dated `job-search/*-search.md` runs are gitignored. The public starter ships only the scaffolding READMEs, the schema/CLI/skills, the reusable platform research, and the fictional `examples/demo/` corpus.

Legacy `data/` templates are retained for migration reference, but the modular `career/` and `applications/` trees are the active architecture.

## Installation

Prerequisites: Python 3.12+ and [uv](https://docs.astral.sh/uv/). Poppler's `pdfinfo` and `pdftotext` are optional but recommended for page-count and extracted-text review.

```bash
uv sync
uv run career --help

# RenderCV is an optional, independently pinned environment extra
uv run --extra render rendercv --version
```

The current pin is `rendercv[full]==2.8` in `pyproject.toml`. Generated YAML uses the versioned official schema URL:

```text
https://raw.githubusercontent.com/rendercv/rendercv/refs/tags/v2.8/schema.json
```

See the official [installation guide](https://docs.rendercv.com/user_guide/index.html), [YAML structure](https://docs.rendercv.com/user_guide/yaml_input_structure/), and [CLI reference](https://docs.rendercv.com/user_guide/cli_reference/).

## Agent setup

Codex, OpenCode, Cursor, and other `AGENTS.md`-aware tools work without installation. A fresh agent must read `AGENTS.md` and then the task-specific `skills/*/SKILL.md`.

Claude Code and other Skills-compatible agents can point their project skill directory at `skills/`. For deep RenderCV design work, optionally install RenderCV's official generated skill:

```bash
npx skills add rendercv/rendercv-skill
```

The core repository workflow does not require Node or `npx`.

## Job search

Discovery output is a staging area, not a career source: shortlisted postings are promoted into `applications/<id>/` only when resume tailoring starts.

- Workflow and criteria: [`job-search/README.md`](job-search/README.md)
- Non-LinkedIn boards, sponsoring employers, and search strategies: [`job-search/2026-10-12-external-platforms.md`](job-search/2026-10-12-external-platforms.md)

The LinkedIn path uses [`satyalyadav/linkedin-mcp-server`](https://github.com/satyalyadav/linkedin-mcp-server) at `feature/724-unsave`, which adds the `save_job` tool (absent upstream). The project-scoped MCP config lives in `.opencode/opencode.json`. To sign in once:

```bash
uvx --from "git+https://github.com/satyalyadav/linkedin-mcp-server@feature/724-unsave" \
  mcp-server-linkedin --login
```

Treat the integration as assisted browsing: keep runs small and sequential, reuse your own signed-in session from your normal network, never send messages or connection requests, and never run it unattended. Dated shortlists and saved-job ids stay gitignored.

## Add experience

```bash
uv run career new-record \
  career/experience/example-company/streaming-platform.md \
  --id example-streaming-platform \
  --type initiative \
  --title "Streaming platform"
```

Edit the Markdown body without compressing it into resume bullets. Put reusable factual statements in frontmatter `claims[]`; link evidence and related records by ID. Then:

```bash
uv run career validate
uv run career index
```

See [Record schema](docs/record-schema.md) for fields, optional body sections, confidence, visibility, and cross-reference rules.

## Generate a tailored resume

Give a repository-aware agent the JD and ask it to use `skills/resume-generation/SKILL.md`. The operational sequence is:

```bash
uv run career init-application 2026-08-company-role \
  --jd /path/to/job-description.md \
  --variant staff-software-engineer

# Agent writes requirements.yaml from the preserved JD
uv run career retrieve applications/2026-08-company-role

# Agent reviews the whole corpus, writes resume.yaml + claim-manifest.yaml + review.md
uv run career validate-application applications/2026-08-company-role
uv run --extra render career validate-resume applications/2026-08-company-role/resume.yaml
uv run --extra render career render applications/2026-08-company-role
uv run career validate-application applications/2026-08-company-role --require-pdf
```

`career retrieve` deliberately uses exact normalized metadata and a small text-keyword bonus. It creates a transparent ranked first pass, not a semantic oracle. The agent must inspect relevant zero-score records and document selection/rejection reasoning.

## Application artifacts

A completed directory contains:

| File | Purpose |
| --- | --- |
| `application.yaml` | ID, role-family variant, page budget, status |
| `job-description.md` | Untouched source JD |
| `requirements.yaml` | Structured responsibilities, skills, seniority, keywords, and grounded inferences |
| `retrieval-report.md` | Ranked records and agent selection notes |
| `claim-manifest.yaml` | Exact output paths mapped to canonical `record#claim` sources |
| `resume.yaml` | Disposable RenderCV v2.8 input |
| `resume.pdf` | RenderCV/Typst output |
| `resume.txt` | Extracted PDF text for review |
| `validation.md` | RenderCV version, commands, page count, placeholder check |
| `review.md` | Agent quality review and unresolved questions |

## Provenance and truthfulness

The validator first checks structural facts: profile/contact fields, employer, role, dates, projects, education, and certificates must match public records or `profile.yaml` (including one side of a canonical bilingual name). It then extracts the headline and narrative/skill statements from `resume.yaml`. Each must have an exact `resume_path` and `output` match in `claim-manifest.yaml`. Every manifest source must resolve to a public record and public claim. Non-public sources, missing claims, stale paths, non-empty `unsupported_additions`, and unacknowledged uncertainty fail validation.

This makes unsupported structure and text fail closed: structural fields are checked against record/profile metadata, while narrative statements are audited by the manifest.

## Rebuild an application

Ask the agent to rebuild `applications/<id>` using the resume-generation skill. It re-runs retrieval, updates `resume.yaml` and `claim-manifest.yaml` together, validates, renders, inspects `resume.txt`, and refreshes `review.md`. Never edit the PDF directly.

## Validate the knowledge base

```bash
uv run career validate
```

This checks frontmatter parsing, schema fields, stable/unique record and claim IDs, related-record links, evidence types, visibility/confidence values, profile structure, and missing evidence.

## Validate and render a generated resume

```bash
uv run career validate-application applications/<id>
uv run --extra render career validate-resume applications/<id>/resume.yaml
uv run --extra render career render applications/<id>
```

The first command checks repository contracts and provenance. The second invokes RenderCV's own Pydantic validation path with all outputs disabled. The third renders only the PDF through RenderCV.

## Resume variants

`config/resume-variants.yaml` includes defaults for staff software, backend/platform, game/rendering, data platform, and engineering leadership roles. Variants define theme, page budget, ordering, emphasis, summary style, project policy, and locale; they contain no career facts.

## Legacy migration

Existing `data/timeline/*.yml` files are preserved. Convert the old top-level `timeline:` shape one file at a time:

```bash
uv run career migrate-legacy data/timeline/Work_20200101-20211231_Engineer.yml \
  --destination career/experience/imported
uv run career validate
```

Imports default to `internal` and `user-supplied`; review their dates, split natural ownership boundaries, attach evidence, and explicitly approve public claims. See [Migration](docs/migration.md).

## End-to-end demo

The fictional demo is safe to inspect and reproduces the complete workflow:

```bash
uv run career --root examples/demo validate
uv run career --root examples/demo index
uv run career --root examples/demo retrieve applications/2026-08-example-platform
uv run career --root examples/demo validate-application applications/2026-08-example-platform
uv run --extra render career --root examples/demo render applications/2026-08-example-platform
uv run career --root examples/demo validate-application applications/2026-08-example-platform --require-pdf
```

The PDF is written to `examples/demo/applications/2026-08-example-platform/resume.pdf`.

## Tests

```bash
uv run python -m unittest discover -s tests -v
uv run --extra render python -m unittest discover -s tests -v
```

The second command includes the real RenderCV validation test.

## Troubleshooting

- `rendercv is not installed`: prefix the command with `uv run --extra render`.
- Manifest path mismatch: regenerate the exact dotted path after moving/reordering a section; do not merely change the output string.
- Non-public source error: create a separate approved public claim or keep the statement out of the resume.
- Missing evidence error: add an evidence record, correct its ID, or leave the claim unverified.
- Too many pages: shorten low-relevance content or use the variant budget; do not change the PDF outside RenderCV.
- Zero retrieval matches: metadata may use different language; search record bodies and review the full corpus before concluding there is no evidence.

For the copy-paste operating checklist, see [Runbook](docs/runbook.md).
