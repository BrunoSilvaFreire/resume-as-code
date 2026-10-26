---
name: interview-preparation
description: Create an evidence-grounded interview guide from a completed application directory and its canonical source records.
---

# Interview Preparation

Use this skill after an application has a validated `requirements.yaml`, `resume.yaml`, and `claim-manifest.yaml`.

Read those files, the original `job-description.md`, every source record referenced by the manifest, and `review.md`. Write `interview-guide.md` in the same application directory.

Cover role/company understanding, likely technical and behavioral questions, evidence-backed answer outlines, system-design topics, resume claim defenses, gaps/open questions, and questions for the interviewer. Reference exact record and claim IDs. Never invent missing experience; label it as a preparation gap.

Validate the application before and after writing:

```bash
uv run career validate-application applications/<id> --require-pdf
```
