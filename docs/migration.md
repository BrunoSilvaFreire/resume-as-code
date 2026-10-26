# Migration from Timeline YAML and the Former Builder

## What changed

The former architecture stored polished career events in `data/timeline/*.yml`, generated YAMLResume/fork-owned schema documents in `data/resumes/`, and rendered with a React/Puppeteer builder. The active architecture uses modular Markdown records in `career/`, disposable RenderCV documents in `applications/`, and RenderCV/Typst for validation and PDF output.

Legacy source files are not deleted by the migration command.

## Field mapping

| Legacy timeline field | New record location |
| --- | --- |
| `timeline[].title` | frontmatter `title` and generated stable `id` |
| `timeline[].type: work` | `type: role` |
| `timeline[].type: project` | `type: project` |
| `company/institution` | frontmatter `company` |
| `startDate`, `endDate` | ISO `start_date`, `end_date` |
| `keywords` | initial `technologies` list; manually split domains/competencies/tags |
| `achievements[]` | one imported claim per achievement |
| `content` | Markdown Context section |

Imports use `visibility: internal`, `verification: user-supplied`, and internal claims. That prevents legacy prose from becoming public resume content without review.

## Command

```bash
uv run career migrate-legacy data/timeline/old-file.yml \
  --destination career/experience/imported
```

The supported legacy input is a mapping with a top-level `timeline` list and the fields above. Unsupported dates fail with an explicit error; convert them to `YYYY`, `YYYY-MM`, `YYYY-MM-DD`, `Mon YYYY`, or `Mon DD, YYYY` and rerun.

## Review after import

1. Split the output by company, role, project, or major initiative where natural ownership requires it.
2. Replace generated IDs only before other records reference them.
3. Separate technologies, domains, competencies, seniority signals, and tags.
4. Remove inferred or inflated wording that is not present in the user's source.
5. Create evidence records and link them from claims.
6. Change claim visibility to `public` only after approval.
7. Run `uv run career validate` and `uv run career index`.

## Generated resumes

Do not migrate old generated YAML as canonical facts. Recover any useful factual statement into a reviewed career record, then generate a new application using RenderCV. Old PDFs can remain outside the active `applications/` tree as historical artifacts, but they are not reproducible outputs of this architecture.

