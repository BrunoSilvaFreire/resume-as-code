# Render Validation

- RenderCV: `RenderCV v2.8`
- Schema validation: pass
- PDF rendering: pass
- Page count: 1
- PDF integrity: pass
- pdfinfo warning: Syntax Error: Suspects object is wrong type (boolean)
- Extracted-text placeholder check: pass

## Commands

```bash
rendercv render resume.yaml --dont-generate-pdf --dont-generate-typst --dont-generate-markdown --dont-generate-html --dont-generate-png
uv run --extra render career render applications/2026-08-example-platform
```
