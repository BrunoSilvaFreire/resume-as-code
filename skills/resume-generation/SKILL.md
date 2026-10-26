---
name: resume-generation
description: Analyze a job description, retrieve public claims from the modular career knowledge base, and create an auditable RenderCV application directory and PDF.
---

# Resume Generation

Use this skill when the user supplies a job description and asks for a tailored resume, or asks to rebuild an existing application.

## Inputs

- The raw JD, or an existing `applications/<id>/job-description.md`.
- `career/profile/profile.yaml` when present.
- Every Markdown record under `career/experience/`, `career/projects/`, `career/knowledge/`, and `career/evidence/`.
- `config/resume-variants.yaml`.
- `schemas/requirements.schema.json` and `schemas/claim-manifest.schema.json`.
- `skills/rendercv/SKILL.md` for the current output contract.

Never use content from `*.example.yml` or `*.example.md` as candidate facts.

## Output

Create or complete one `applications/<id>/` directory containing the artifacts listed in `AGENTS.md`. Generated RenderCV YAML and PDFs are not canonical career sources.

## Workflow

1. **Initialize and preserve the JD.** If the application does not exist, run `uv run career init-application <id> --jd <path> --variant <variant>`. Never rewrite `job-description.md`.
2. **Validate the source corpus.** Run `uv run career validate`. Fix duplicate IDs, broken links, or invalid metadata before generation.
3. **Analyze the JD.** Write `requirements.yaml` matching `schemas/requirements.schema.json`. Separate direct requirements from `inferred_requirements`, and state the basis of every inference. Do not perform company research unless requested or needed to interpret the role.
4. **Run first-pass retrieval.** Run `uv run career retrieve applications/<id>`. Then read all potentially relevant records, including zero-score records whose body may use different terminology. Replace the placeholder selection notes with reasons for selecting and rejecting records.
5. **Select claims.** Prefer verified, public, relevant claims with strong scope or outcomes. A `needs-confirmation` claim may only be used conservatively and must remain marked in the manifest/open questions. Never use internal or private material.
6. **Draft the RenderCV document.** Generate `resume.yaml` in the official v2.8 schema. Apply the chosen variant's theme, section order, page budget, emphasis, and locale. Keep chronology accurate and content concise; usually no more than two highlighted projects.
7. **Build provenance while writing.** For every headline, summary, highlight, bullet, and skill-details statement tracked by the validator, add one `claim-manifest.yaml` item with its exact `cv.*` path and output. Sources must be existing `record#claim` pairs. `unsupported_additions` must always be empty.
8. **Review structure and truth.** Run `uv run career validate-application applications/<id>`. Fix every missing path, mismatch, non-public source, and uncertainty error.
9. **Validate and render with RenderCV.** Run `uv run --extra render career validate-resume .../resume.yaml`, then `uv run --extra render career render applications/<id>`.
10. **Review the output.** Read `resume.txt`, inspect the PDF/page count, check chronology, repetition, clipped/isolated headings, weak claims, placeholders, and JD alignment. Record the result and open questions in `review.md`. Re-run application validation with `--require-pdf`.

## Provenance rules

- `resume_path` and `output` must exactly match `resume.yaml`.
- `transformations` describe only what happened: `verbatim`, `condensed`, `combined`, `translated`, or `tailored`.
- Combined statements cite every contributing claim.
- Exact-wording claims must remain exact.
- Profile/contact and structural entry fields are copied from profile/record metadata; narrative statements are covered by the manifest.
- A missing fact is a gap, not permission to infer it.

## Rebuild an application

Re-read the JD and changed source records, regenerate `requirements.yaml` only if the JD interpretation changed, re-run retrieval, update `resume.yaml` and its manifest together, then repeat steps 8–10. Never hand-edit `resume.pdf`.
