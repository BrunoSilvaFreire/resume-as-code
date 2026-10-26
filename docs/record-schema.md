# Career Record Schema

Career records are Markdown files with YAML frontmatter. The machine contract is `schemas/record.schema.json`; the body remains deliberately flexible so long-term source material is not forced into resume-bullet form.

## Minimal record

```markdown
---
id: company-service-reliability
type: initiative
title: Service reliability program
company: Company Name
role: Senior Software Engineer
start_date: 2024-01
technologies: [Go, PostgreSQL, Kubernetes]
domains: [platform engineering]
competencies: [reliability engineering, technical leadership]
seniority_signals: [cross-team architecture]
tags: [backend, incident response]
visibility: internal
verification: needs-confirmation
related_records: [company-platform-role]
claims:
  - id: company-recovery-time
    statement: Reduced median recovery time from the user-supplied baseline to the verified final value.
    visibility: internal
    confidence: needs-confirmation
    safe_to_paraphrase: true
    exact_wording_required: false
    evidence: []
---

# Context

Detailed source material goes here.
```

## Frontmatter fields

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Stable lowercase kebab-case record ID; globally unique |
| `type` | yes | `company`, `role`, `project`, `initiative`, `decision`, `incident`, `achievement`, `knowledge`, or `evidence` |
| `title` | yes | Human-readable title |
| `company`, `role`, `project` | no | Ownership and retrieval facets |
| `start_date`, `end_date` | no | `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`; omit/null ongoing end dates |
| `technologies`, `domains`, `competencies` | no | Exact retrieval facets |
| `seniority_signals`, `tags` | no | Leadership/scope and general retrieval facets |
| `visibility` | yes | `public`, `internal`, or `private` |
| `verification` | yes | `verified`, `user-supplied`, or `needs-confirmation` |
| `related_records` | no | Existing record IDs; references only |
| `claims` | no | Stable reusable statements with their own truth/privacy metadata |

Additional frontmatter is allowed so records can grow organically, but prefer documented fields when they fit.

## Claim fields

Claims require a globally unique `id`, factual `statement`, `visibility`, `confidence`, `safe_to_paraphrase`, and an `evidence` list. `confidence` accepts `verified`, `approximate`, `user-supplied`, or `needs-confirmation`.

Set `exact_wording_required: true` when legal, attribution, measurement, or public wording must remain unchanged. The provenance validator then requires the exact source statement to appear in the output.

Evidence list entries are record IDs, and those records must have `type: evidence`. An empty list is structurally valid but should not be upgraded to `verified` without a defensible source.

## Markdown body

Useful optional sections include Context, Problem, My contribution, Technical decisions, Tradeoffs, Implementation, Results, Metrics, Collaboration, Leadership, Lessons learned, Alternative resume framings, and Private notes. Use only the sections that add information.

## Cross-reference and canonical ownership

Choose one record as the canonical owner of an accomplishment. Other records use `related_records` or normal Markdown links. Run `uv run career index` to browse by company, project, technology, domain, and competency without copying descriptions.

## Validation

```bash
uv run career validate
uv run career index
```

