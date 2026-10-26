# Agents Guide — Resume as Code

This repository is a modular, agent-driven career knowledge base. Markdown/YAML under `career/` is canonical; job-specific files under `applications/` are disposable outputs. RenderCV v2.8 is the only resume schema validator and PDF renderer.

## Read the matching skill

| Task | Skill |
| --- | --- |
| Add or polish career facts | `skills/timeline-polishing/SKILL.md` |
| Analyze a JD and generate/rebuild an application | `skills/resume-generation/SKILL.md` |
| Work directly on RenderCV YAML or rendering | `skills/rendercv/SKILL.md` |
| Prepare for an interview from an application | `skills/interview-preparation/SKILL.md` |
| Discover and triage jobs | `job-search/README.md` |

Read the complete `SKILL.md` before acting. Never read or reuse candidate facts from files named `*.example.yml` or `*.example.md`; those are structural history only.

## Architectural boundary

- `career/`: canonical, detailed, long-lived facts and evidence.
- `career/index.md`: generated references only; never a second canonical description.
- `config/resume-variants.yaml`: presentation defaults and constraints, never career facts.
- `applications/<id>/`: original JD, analysis, retrieval, RenderCV YAML, provenance, PDF, and review.
- `job-search/`: disposable discovery staging. Dated shortlists and saved-job ids are personal and gitignored; never treat them as career facts.
- RenderCV owns resume validation, typography, pagination, and PDF output. Do not add HTML/Puppeteer/LaTeX resume renderers.

## Career records

Records are Markdown with YAML frontmatter validated by `schemas/record.schema.json`. Required fields are `id`, `type`, `title`, `visibility`, and `verification`. Claims intended for resumes belong in `claims[]` and have stable globally unique IDs.

Use links, `related_records`, tags, and the generated index to make facts discoverable. Maintain each accomplishment in one canonical record. A technology or competency index may point to it but must not restate it as another fact.

Visibility is strict:

- `public`: eligible for a generated resume.
- `internal`: repository context only; not eligible for a public resume.
- `private`: sensitive; never place in an application artifact.

Confidence is also strict. `needs-confirmation` must remain conservative or become an open question; never upgrade it silently.

For ongoing canonical records, omit `end_date` or set it to null. RenderCV outputs may use its native `end_date: present` value.

## Deterministic commands

```bash
# Install/check the lightweight repository tools
uv sync

# Create and edit a new record, then validate references and rebuild indexes
uv run career new-record career/experience/company/initiative.md \
  --id company-initiative --type initiative --title "Initiative title"
uv run career validate
uv run career index

# Create an application from a JD
uv run career init-application 2026-08-company-role \
  --jd /path/to/job-description.md --variant staff-software-engineer

# After writing requirements.yaml, run deterministic first-pass retrieval
uv run career retrieve applications/2026-08-company-role

# Audit structure/provenance, validate through RenderCV, and render the PDF
uv run career validate-application applications/2026-08-company-role
uv run --extra render career validate-resume applications/2026-08-company-role/resume.yaml
uv run --extra render career render applications/2026-08-company-role
uv run career validate-application applications/2026-08-company-role --require-pdf
```

`career retrieve` is only an exact metadata/keyword first pass. The agent must also review semantically relevant and zero-score records before selecting claims.

## Required application artifacts

Every completed `applications/<id>/` contains:

- `application.yaml`
- `job-description.md`
- `requirements.yaml`
- `retrieval-report.md`
- `claim-manifest.yaml`
- `resume.yaml`
- `resume.pdf`
- `resume.txt`
- `validation.md`
- `review.md`

Every provenance-controlled resume statement must have one `claim-manifest.yaml` entry with the exact RenderCV path, exact output text, one or more existing `record#claim` sources, declared transformations, and an empty `unsupported_additions` list. Employer, role, dates, projects, education, certificates, and contact fields are also checked directly against public record/profile metadata.

## Truthfulness rules

- Never invent employers, dates, roles, technologies, metrics, scope, leadership, team size, qualifications, or impact.
- Never infer a specific service merely because a broad cloud/platform appears elsewhere.
- Only public records and public claims may appear in `resume.yaml`.
- Preserve exact wording when `exact_wording_required: true` or `safe_to_paraphrase: false`.
- If evidence is incomplete, use conservative wording or record an open question.
- Validate the manifest after every resume edit; path changes and wording changes are intentional provenance changes.

## Rebuild flow

When canonical records change, do not edit the PDF. Re-run retrieval, regenerate the affected RenderCV YAML and manifest entries, validate the application, render through RenderCV, inspect `resume.txt` and the page count, then update `review.md`.

See `docs/runbook.md`, `docs/record-schema.md`, and `docs/migration.md` for the full operating reference.
