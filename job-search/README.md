# Job Search

Discovery and triage output for the LinkedIn job search. This directory is a
staging area: shortlisted postings are promoted into `applications/<id>/` when a
tailored resume is generated.

Canonical career facts remain under `career/`. Nothing in this directory is a
career source.

## Tooling

- **MCP server:** `satyalyadav/linkedin-mcp-server` @ `feature/724-unsave`
  (fork of `stickerdaniel/linkedin-mcp-server` v4.27.0) — adds the `save_job`
  tool, which upstream lacks.
- **Configured in:** `.opencode/opencode.json` (project-scoped, machine-local).
- **Auth:** reuses the local signed-in LinkedIn browser session; Chromium cache
  under `~/.linkedin-mcp/patchright-browsers`.

## Search criteria

| Dimension        | Value                                                                                          |
| ---------------- | ---------------------------------------------------------------------------------------------- |
| Role families    | backend/platform (Go, K8s, observability), Unreal/real-time rendering, staff/senior generalist |
| Work arrangement | remote (global), plus onsite with relocation to a first-world country                          |
| Experience level | `mid_senior`                                                                                   |
| Job type         | `full_time`                                                                                    |
| Date posted      | `past_month` on first run, `past_week` on later runs                                           |
| Sort             | `date`                                                                                         |

## Safety / rate limits

LinkedIn's User Agreement prohibits automated access. Keep runs small and
sequential, reuse the existing signed-in session from the normal home IP, never
send messages or connection requests, and do not run unattended.

## Files

- `2026-10-12-search.md` — first discovery run: ranked shortlist and status.

## Workflow

1. Run `search_jobs` across the keyword/location matrix.
2. Triage: `get_job_details` → `get_job_apply_url` (drop `applied`/`closed`).
3. Score fit against `career/` records.
4. `save_job` each shortlisted posting.
5. Record results in the dated report.
6. Promote shortlisted postings to `applications/<id>/` via
   `uv run career init-application` when resume tailoring begins.
