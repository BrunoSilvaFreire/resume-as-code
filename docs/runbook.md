# Operating Runbook

## Add experience

```bash
uv run career new-record career/experience/<company>/<record>.md \
  --id <stable-id> --type <type> --title "<title>"
```

Fill frontmatter and the useful Markdown sections. Add evidence records first when a claim depends on them. Finish with:

```bash
uv run career validate
uv run career index
```

## Generate an application

```bash
uv run career init-application <YYYY-MM-company-role> \
  --jd <job-description-path> --variant <variant-id>
```

Ask the agent to follow `skills/resume-generation/SKILL.md`. After it writes `requirements.yaml`:

```bash
uv run career retrieve applications/<id>
```

The agent reviews all relevant records, completes retrieval notes, writes `resume.yaml`, `claim-manifest.yaml`, and `review.md`, then runs:

```bash
uv run career validate-application applications/<id>
uv run --extra render career validate-resume applications/<id>/resume.yaml
uv run --extra render career render applications/<id>
uv run career validate-application applications/<id> --require-pdf
```

## Rebuild an application

1. Validate the knowledge base.
2. Re-run deterministic retrieval.
3. Ask the agent to re-read changed records and the unchanged JD.
4. Update `resume.yaml` and `claim-manifest.yaml` together.
5. Repeat validation/render/review commands above.
6. Verify `resume.txt`, the page count in `validation.md`, and open questions in `review.md`.

## Validate only

```bash
uv run career validate
uv run career validate-application applications/<id>
uv run --extra render career validate-resume applications/<id>/resume.yaml
```

## End-to-end rehearsal

```bash
uv run career --root examples/demo validate
uv run career --root examples/demo index
uv run career --root examples/demo retrieve applications/2026-08-example-platform
uv run career --root examples/demo validate-application applications/2026-08-example-platform
uv run --extra render career --root examples/demo render applications/2026-08-example-platform
uv run career --root examples/demo validate-application applications/2026-08-example-platform --require-pdf
```

Inspect:

- `examples/demo/applications/2026-08-example-platform/resume.pdf`
- `examples/demo/applications/2026-08-example-platform/resume.txt`
- `examples/demo/applications/2026-08-example-platform/validation.md`
- `examples/demo/applications/2026-08-example-platform/claim-manifest.yaml`

