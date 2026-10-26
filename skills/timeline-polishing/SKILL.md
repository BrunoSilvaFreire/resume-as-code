---
name: timeline-polishing
description: Turn raw career notes into a detailed Markdown career record with validated frontmatter, claims, evidence links, and privacy boundaries.
---

# Timeline Polishing

Use this skill when the user provides raw employment, role, project, initiative, decision, incident, mentoring, or achievement notes and wants them captured in the career knowledge base.

## Workflow

1. Identify the natural canonical owner: company/role under `career/experience/`, independent project under `career/projects/`, reusable context under `career/knowledge/`, or supporting source under `career/evidence/`.
2. Search existing record IDs, titles, tags, and related records. Extend the canonical record when the fact already has an owner; do not create a technology-specific duplicate.
3. Scaffold when needed:

   ```bash
   uv run career new-record career/experience/company/initiative.md \
     --id company-initiative --type initiative --title "Initiative title"
   ```

4. Fill structured frontmatter using `schemas/record.schema.json`. Use ISO `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` dates. Omit or null an ongoing `end_date`.
5. Preserve detail in optional Markdown sections such as Context, Problem, My contribution, Technical decisions, Tradeoffs, Implementation, Results, Metrics, Collaboration, Leadership, Lessons learned, Alternative resume framings, and Private notes. Do not force empty sections.
6. Add stable claim objects only for statements that may be reused. Each claim states visibility, confidence, paraphrase safety, exact-wording requirements, and evidence record IDs.
7. Link related records instead of copying facts. Evidence IDs must point to records with `type: evidence`.
8. Run `uv run career validate` and `uv run career index`.

## Truth and privacy

- Preserve the user's wording and detail; polish clarity without adding facts.
- Do not infer technologies, metrics, business impact, team size, leadership, dates, or responsibilities.
- Use `needs-confirmation` for incomplete claims and write the gap in the body.
- Default a new record to `internal` until the user explicitly approves public use.
- Put sensitive context in a private record or Private notes, never in a public claim.
- Bilingual organization names may remain canonical as `English | 中文`; the resume agent selects one language.

## Legacy migration

For the old top-level `timeline:` YAML shape:

```bash
uv run career migrate-legacy data/timeline/old-file.yml \
  --destination career/experience/imported
```

The command preserves the source, marks imported records `internal` and `user-supplied`, and requires review before public use.
