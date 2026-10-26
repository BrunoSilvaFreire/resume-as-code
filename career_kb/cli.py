from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = PROJECT_ROOT / "schemas"
RECORD_DIRS = ("experience", "projects", "knowledge", "evidence")
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)(.*)\Z", re.DOTALL)
PROVENANCE_FIELDS = {"summary", "details", "bullet", "number", "reversed_number"}


class StringDatesSafeLoader(yaml.SafeLoader):
    """Keep ISO-looking dates as strings so schemas and RenderCV see the source value."""

    yaml_implicit_resolvers = {
        key: list(value) for key, value in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }


for first_character, resolvers in list(StringDatesSafeLoader.yaml_implicit_resolvers.items()):
    StringDatesSafeLoader.yaml_implicit_resolvers[first_character] = [
        resolver for resolver in resolvers if resolver[0] != "tag:yaml.org,2002:timestamp"
    ]


@dataclass(frozen=True)
class Record:
    path: Path
    metadata: dict[str, Any]
    body: str


def load_yaml(path: Path) -> Any:
    try:
        return yaml.load(path.read_text(encoding="utf-8"), Loader=StringDatesSafeLoader)
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"{path}: {exc}") from exc


def parse_record(path: Path) -> Record:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        raise ValueError(f"{path}: missing YAML frontmatter delimited by ---")
    try:
        metadata = yaml.load(match.group(1), Loader=StringDatesSafeLoader)
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid frontmatter: {exc}") from exc
    if not isinstance(metadata, dict):
        raise ValueError(f"{path}: frontmatter must be a mapping")
    return Record(path, metadata, match.group(2).strip())


def schema_errors(data: Any, name: str, source: Path) -> list[str]:
    schema = load_yaml(SCHEMAS / name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "<root>"
        errors.append(f"{source}: {location}: {error.message}")
    return errors


def record_paths(root: Path) -> Iterable[Path]:
    for directory in RECORD_DIRS:
        base = root / "career" / directory
        if base.exists():
            yield from sorted(
                path for path in base.rglob("*.md") if path.name.lower() != "readme.md"
            )


def load_records(root: Path) -> tuple[list[Record], list[str]]:
    records: list[Record] = []
    errors: list[str] = []
    for path in record_paths(root):
        try:
            record = parse_record(path)
            records.append(record)
            errors.extend(schema_errors(record.metadata, "record.schema.json", path))
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    return records, errors


def validate_knowledge(root: Path) -> tuple[list[Record], list[str]]:
    records, errors = load_records(root)
    by_id: dict[str, Record] = {}
    claims: dict[str, tuple[Record, dict[str, Any]]] = {}

    for record in records:
        record_id = record.metadata.get("id")
        if isinstance(record_id, str):
            if record_id in by_id:
                errors.append(
                    f"{record.path}: duplicate record id {record_id!r} also used by {by_id[record_id].path}"
                )
            else:
                by_id[record_id] = record
        for claim in record.metadata.get("claims", []) or []:
            if not isinstance(claim, dict) or not isinstance(claim.get("id"), str):
                continue
            claim_id = claim["id"]
            if claim_id in claims:
                errors.append(
                    f"{record.path}: duplicate global claim id {claim_id!r} also used by {claims[claim_id][0].path}"
                )
            else:
                claims[claim_id] = (record, claim)

    for record in records:
        for related in record.metadata.get("related_records", []) or []:
            if related not in by_id:
                errors.append(f"{record.path}: related record {related!r} does not exist")
        for claim in record.metadata.get("claims", []) or []:
            if not isinstance(claim, dict):
                continue
            for evidence_id in claim.get("evidence", []) or []:
                evidence = by_id.get(evidence_id)
                if evidence is None:
                    errors.append(
                        f"{record.path}: claim {claim.get('id')!r} references missing evidence {evidence_id!r}"
                    )
                elif evidence.metadata.get("type") != "evidence":
                    errors.append(
                        f"{record.path}: claim {claim.get('id')!r} evidence {evidence_id!r} is not an evidence record"
                    )

    profile = root / "career" / "profile" / "profile.yaml"
    if profile.exists():
        try:
            errors.extend(schema_errors(load_yaml(profile), "profile.schema.json", profile))
        except ValueError as exc:
            errors.append(str(exc))
    return records, errors


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9+#.]+", " ", value.casefold()).strip()


def write_index(root: Path, records: list[Record]) -> Path:
    target = root / "career" / "index.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    groups: dict[str, dict[str, list[Record]]] = {
        name: defaultdict(list)
        for name in ("company", "project", "technology", "domain", "competency")
    }
    for record in records:
        metadata = record.metadata
        for field in ("company", "project"):
            if metadata.get(field):
                groups[field][str(metadata[field])].append(record)
        for field, singular in (
            ("technologies", "technology"),
            ("domains", "domain"),
            ("competencies", "competency"),
        ):
            for value in metadata.get(field, []) or []:
                groups[singular][str(value)].append(record)

    lines = [
        "# Generated Career Index",
        "",
        "Generated references only. Canonical facts remain in the linked records.",
    ]
    labels = {
        "company": "Companies",
        "project": "Projects",
        "technology": "Technologies",
        "domain": "Domains",
        "competency": "Competencies",
    }
    for group, label in labels.items():
        lines.extend(["", f"## {label}", ""])
        if not groups[group]:
            lines.append("_None yet._")
            continue
        for value, matches in sorted(groups[group].items(), key=lambda item: item[0].casefold()):
            refs = []
            for record in sorted(
                matches, key=lambda item: str(item.metadata.get("title", "")).casefold()
            ):
                relative = record.path.relative_to(target.parent).as_posix()
                refs.append(f"[{record.metadata['title']}]({relative})")
            lines.append(f"- **{value}**: {', '.join(refs)}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def validate_requirements(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.exists():
        return None, [f"{path}: missing structured job analysis"]
    try:
        data = load_yaml(path)
    except ValueError as exc:
        return None, [str(exc)]
    return data, schema_errors(data, "requirements.schema.json", path)


def ranked_records(
    requirements: dict[str, Any], records: list[Record]
) -> list[tuple[int, Record, list[str]]]:
    wanted = {
        "technologies": {
            normalize(item)
            for item in requirements["technologies"]
            + requirements["required_skills"]
            + requirements["preferred_skills"]
        },
        "domains": {normalize(item) for item in requirements["domains"]},
        "competencies": {normalize(item) for item in requirements["competencies"]},
        "seniority_signals": {normalize(item) for item in requirements["seniority_signals"]},
        "tags": {normalize(item) for item in requirements["keywords"]},
    }
    weights = {
        "technologies": 5,
        "competencies": 4,
        "domains": 3,
        "seniority_signals": 2,
        "tags": 1,
    }
    ranked: list[tuple[int, Record, list[str]]] = []
    for record in records:
        score = 0
        matches: list[str] = []
        for field, weight in weights.items():
            values = {normalize(str(item)) for item in record.metadata.get(field, []) or []}
            overlap = sorted(values & wanted[field])
            if overlap:
                score += weight * len(overlap)
                matches.append(f"{field}: {', '.join(overlap)}")
        searchable = normalize(
            record.body
            + " "
            + " ".join(
                str(claim.get("statement", ""))
                for claim in record.metadata.get("claims", []) or []
                if isinstance(claim, dict)
            )
        )
        keyword_hits = sorted(
            term for term in wanted["tags"] if len(term) >= 3 and term in searchable
        )
        if keyword_hits:
            score += min(len(keyword_hits), 5)
            matches.append(f"text: {', '.join(keyword_hits[:5])}")
        if score:
            ranked.append((score, record, matches))
    return sorted(
        ranked, key=lambda item: (-item[0], str(item[1].metadata.get("title", "")).casefold())
    )


def write_retrieval_report(
    root: Path, app: Path, ranked: list[tuple[int, Record, list[str]]], limit: int
) -> Path:
    target = app / "retrieval-report.md"
    lines = [
        "# Retrieval Report",
        "",
        "> Deterministic first pass: exact normalized metadata matches plus a small text-keyword bonus. An agent must review semantic relevance and zero-score records before selecting claims.",
        "",
        "| Rank | Score | Record | Matched signals |",
        "| ---: | ---: | --- | --- |",
    ]
    for index, (score, record, matches) in enumerate(ranked[:limit], 1):
        relative = Path("..") / Path("..") / record.path.relative_to(root)
        lines.append(
            f"| {index} | {score} | [{record.metadata['title']}]({relative.as_posix()}) | {'; '.join(matches)} |"
        )
    if not ranked:
        lines.append("| - | 0 | No exact matches | Agent review of the full corpus is required. |")
    lines.extend(
        [
            "",
            "## Agent selection notes",
            "",
            "_Replace this line with why records/claims were selected or rejected._",
            "",
        ]
    )
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def iter_highlights(value: Any, path: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, str) and value.strip():
        yield path, value.strip()
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_highlights(item, f"{path}.{index}")


def resume_claims(resume: dict[str, Any]) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    cv = resume.get("cv")
    if not isinstance(cv, dict):
        return output
    if isinstance(cv.get("headline"), str) and cv["headline"].strip():
        output.append(("cv.headline", cv["headline"].strip()))
    sections = cv.get("sections")
    if not isinstance(sections, dict):
        return output
    for section_name, entries in sections.items():
        if not isinstance(entries, list):
            continue
        section_path = f"cv.sections.{section_name}"
        for index, entry in enumerate(entries):
            entry_path = f"{section_path}.{index}"
            if isinstance(entry, str) and entry.strip():
                output.append((entry_path, entry.strip()))
            elif isinstance(entry, dict):
                for field in PROVENANCE_FIELDS:
                    value = entry.get(field)
                    if isinstance(value, (str, list)):
                        output.extend(iter_highlights(value, f"{entry_path}.{field}"))
                if "highlights" in entry:
                    output.extend(iter_highlights(entry["highlights"], f"{entry_path}.highlights"))
    return output


def localized_equal(output: Any, source: Any) -> bool:
    if output is None or source is None:
        return output is source
    expected = str(source).strip()
    actual = str(output).strip()
    link = re.fullmatch(r"\[([^]]+)]\([^)]+\)", actual)
    if link:
        actual = link.group(1).strip()
    return actual in {expected, *(part.strip() for part in expected.split("|"))}


def dates_equal(output: Any, source: Any) -> bool:
    if source in (None, ""):
        return output in (None, "", "present")
    return str(output) == str(source)


def validate_structural_facts(
    root: Path, resume: dict[str, Any], records: list[Record]
) -> list[str]:
    errors: list[str] = []
    cv = resume.get("cv")
    if not isinstance(cv, dict):
        return ["resume.yaml: cv must be a mapping"]

    profile_path = root / "career" / "profile" / "profile.yaml"
    profile = load_yaml(profile_path) if profile_path.exists() else None
    if isinstance(profile, dict):
        profile_fields = {
            "name": "name",
            "location": "location",
            "email": "email",
            "phone": "phone",
            "website": "website",
        }
        for output_field, source_field in profile_fields.items():
            if output_field in cv and not localized_equal(
                cv[output_field], profile.get(source_field)
            ):
                errors.append(f"resume.yaml: cv.{output_field} is not supported by {profile_path}")

    sections = cv.get("sections")
    if not isinstance(sections, dict):
        return errors
    public_records = [record for record in records if record.metadata.get("visibility") == "public"]
    for section_name, entries in sections.items():
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            path = f"cv.sections.{section_name}.{index}"
            if "company" in entry and "position" in entry:
                matches = [
                    record
                    for record in public_records
                    if localized_equal(entry["company"], record.metadata.get("company"))
                    and localized_equal(entry["position"], record.metadata.get("role"))
                ]
                if not matches:
                    errors.append(
                        f"resume.yaml: {path} employer/role does not match a public career record"
                    )
                elif not any(
                    dates_equal(entry.get("start_date"), record.metadata.get("start_date"))
                    and dates_equal(entry.get("end_date"), record.metadata.get("end_date"))
                    for record in matches
                ):
                    errors.append(
                        f"resume.yaml: {path} dates do not match its public career record"
                    )
            elif "institution" in entry and isinstance(profile, dict):
                education = profile.get("education", []) or []
                matches = [
                    item
                    for item in education
                    if isinstance(item, dict)
                    and localized_equal(entry["institution"], item.get("institution"))
                    and localized_equal(entry.get("area"), item.get("area"))
                    and localized_equal(entry.get("degree"), item.get("degree"))
                ]
                if not matches:
                    errors.append(f"resume.yaml: {path} education does not match profile.yaml")
                elif not any(
                    dates_equal(entry.get("start_date"), item.get("start_date"))
                    and dates_equal(entry.get("end_date"), item.get("end_date"))
                    for item in matches
                ):
                    errors.append(f"resume.yaml: {path} education dates do not match profile.yaml")
            elif "name" in entry and "issuer" in entry and isinstance(profile, dict):
                certificates = profile.get("certificates", []) or []
                matches = [
                    item
                    for item in certificates
                    if isinstance(item, dict)
                    and localized_equal(entry["name"], item.get("name"))
                    and localized_equal(entry["issuer"], item.get("issuer"))
                ]
                if not matches:
                    errors.append(f"resume.yaml: {path} certificate does not match profile.yaml")
            elif "name" in entry:
                matches = [
                    record
                    for record in public_records
                    if record.metadata.get("type") in {"project", "initiative", "achievement"}
                    and (
                        localized_equal(entry["name"], record.metadata.get("project"))
                        or localized_equal(entry["name"], record.metadata.get("title"))
                    )
                ]
                if matches and not any(
                    dates_equal(entry.get("start_date"), record.metadata.get("start_date"))
                    and dates_equal(entry.get("end_date"), record.metadata.get("end_date"))
                    for record in matches
                ):
                    errors.append(
                        f"resume.yaml: {path} dates do not match its public project record"
                    )
                elif not matches:
                    errors.append(
                        f"resume.yaml: {path} named entry does not match a public career record"
                    )
    return errors


def validate_manifest(
    root: Path, app: Path, records: list[Record], resume: dict[str, Any]
) -> list[str]:
    manifest_path = app / "claim-manifest.yaml"
    if not manifest_path.exists():
        return [f"{manifest_path}: missing claim manifest"]
    try:
        manifest = load_yaml(manifest_path)
    except ValueError as exc:
        return [str(exc)]
    errors = schema_errors(manifest, "claim-manifest.schema.json", manifest_path)
    if errors or not isinstance(manifest, dict):
        return errors
    if manifest.get("application") != app.name:
        errors.append(f"{manifest_path}: application must match directory name {app.name!r}")

    claim_map: dict[tuple[str, str], tuple[Record, dict[str, Any]]] = {}
    for record in records:
        for claim in record.metadata.get("claims", []) or []:
            if isinstance(claim, dict):
                claim_map[(str(record.metadata.get("id")), str(claim.get("id")))] = (record, claim)

    manifest_by_path: dict[str, dict[str, Any]] = {}
    for item in manifest["claims"]:
        path = item["resume_path"]
        if path in manifest_by_path:
            errors.append(f"{manifest_path}: duplicate resume_path {path!r}")
        manifest_by_path[path] = item
        for source in item["sources"]:
            key = (source["record"], source["claim"])
            source_claim = claim_map.get(key)
            if source_claim is None:
                errors.append(
                    f"{manifest_path}: {path} references missing source {key[0]}#{key[1]}"
                )
                continue
            record, claim = source_claim
            if record.metadata.get("visibility") != "public" or claim.get("visibility") != "public":
                errors.append(f"{manifest_path}: {path} uses non-public source {key[0]}#{key[1]}")
            if claim.get("confidence") != "verified" and item["handling"] == "verified":
                errors.append(
                    f"{manifest_path}: {path} treats {claim.get('confidence')} source "
                    f"{key[0]}#{key[1]} as verified"
                )
            if (
                claim.get("exact_wording_required") or not claim.get("safe_to_paraphrase", True)
            ) and claim.get("statement") != item["output"]:
                errors.append(
                    f"{manifest_path}: {path} must preserve exact wording from {key[0]}#{key[1]}"
                )

    extracted = resume_claims(resume)
    for path, text in extracted:
        item = manifest_by_path.get(path)
        if item is None:
            errors.append(f"{manifest_path}: unsupported resume statement at {path}: {text!r}")
        elif item["output"] != text:
            errors.append(f"{manifest_path}: output for {path} does not exactly match resume.yaml")
    extracted_paths = {path for path, _ in extracted}
    for path in manifest_by_path:
        if path not in extracted_paths:
            errors.append(
                f"{manifest_path}: {path} does not point to a provenance-controlled statement in resume.yaml"
            )
    return errors


def validate_application(root: Path, app: Path, require_pdf: bool = False) -> list[str]:
    errors: list[str] = []
    application_path = app / "application.yaml"
    if not application_path.exists():
        errors.append(f"{application_path}: missing application metadata")
    else:
        try:
            application = load_yaml(application_path)
            if not isinstance(application, dict) or application.get("schema_version") != 1:
                errors.append(f"{application_path}: schema_version must be 1")
            elif application.get("id") != app.name:
                errors.append(f"{application_path}: id must match directory name {app.name!r}")
            else:
                variants = load_yaml(PROJECT_ROOT / "config" / "resume-variants.yaml")
                available = variants.get("variants", {}) if isinstance(variants, dict) else {}
                if application.get("variant") not in available:
                    errors.append(
                        f"{application_path}: unknown variant {application.get('variant')!r}"
                    )
        except ValueError as exc:
            errors.append(str(exc))
    if not (app / "job-description.md").exists():
        errors.append(f"{app / 'job-description.md'}: missing original job description")
    _, requirement_errors = validate_requirements(app / "requirements.yaml")
    errors.extend(requirement_errors)

    resume_path = app / "resume.yaml"
    resume: dict[str, Any] | None = None
    if not resume_path.exists():
        errors.append(f"{resume_path}: missing RenderCV YAML")
    else:
        try:
            loaded = load_yaml(resume_path)
            if not isinstance(loaded, dict):
                errors.append(f"{resume_path}: root must be a mapping")
            else:
                resume = loaded
        except ValueError as exc:
            errors.append(str(exc))
    records, knowledge_errors = validate_knowledge(root)
    errors.extend(knowledge_errors)
    if resume is not None:
        errors.extend(validate_structural_facts(root, resume, records))
        errors.extend(validate_manifest(root, app, records, resume))
    for required in ("retrieval-report.md", "review.md"):
        if not (app / required).exists():
            errors.append(f"{app / required}: missing application artifact")
    if require_pdf and not (app / "resume.pdf").exists():
        errors.append(f"{app / 'resume.pdf'}: missing rendered PDF")
    return errors


def rendercv_command() -> str:
    command = shutil.which("rendercv")
    if not command:
        raise RuntimeError(
            "rendercv is not installed; run this command through `uv run --extra render career ...`"
        )
    return command


def run_rendercv(resume: Path, pdf: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [rendercv_command(), "render", str(resume)]
    if pdf is None:
        command.extend(
            [
                "--dont-generate-pdf",
                "--dont-generate-typst",
                "--dont-generate-markdown",
                "--dont-generate-html",
                "--dont-generate-png",
            ]
        )
        return subprocess.run(command, text=True, capture_output=True, check=False)
    # RenderCV compiles the PDF from generated Typst. Point that required intermediate
    # at a temporary file so application directories retain only the requested PDF.
    with tempfile.TemporaryDirectory(prefix="career-rendercv-") as temporary:
        command.extend(
            [
                "--pdf-path",
                str(pdf.resolve()),
                "--typst-path",
                str(Path(temporary) / "resume.typ"),
                "--dont-generate-markdown",
                "--dont-generate-html",
                "--dont-generate-png",
            ]
        )
        return subprocess.run(command, text=True, capture_output=True, check=False)


def pdf_pages(path: Path) -> tuple[int | None, str | None]:
    if not shutil.which("pdfinfo"):
        return None, None
    result = subprocess.run(["pdfinfo", str(path)], text=True, capture_output=True, check=False)
    match = re.search(r"^Pages:\s+(\d+)$", result.stdout, re.MULTILINE)
    warning = result.stderr.strip() or None
    return (int(match.group(1)) if match else None), warning


def pdf_integrity(path: Path) -> str:
    if not shutil.which("gs"):
        return "not checked (Ghostscript unavailable)"
    result = subprocess.run(
        ["gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=nullpage", str(path)],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return f"failed: {(result.stdout + result.stderr).strip()}"
    return "pass"


def render_application(root: Path, app: Path) -> list[str]:
    errors = validate_application(root, app)
    if errors:
        return errors
    resume = app / "resume.yaml"
    validation = run_rendercv(resume)
    if validation.returncode:
        return [f"RenderCV validation failed:\n{validation.stdout}{validation.stderr}"]
    pdf = app / "resume.pdf"
    rendered = run_rendercv(resume, pdf)
    if rendered.returncode:
        return [f"RenderCV rendering failed:\n{rendered.stdout}{rendered.stderr}"]
    if not pdf.exists():
        return [
            f"RenderCV exited successfully but did not create the requested PDF: {pdf}\n{rendered.stdout}{rendered.stderr}"
        ]

    pages, pdfinfo_warning = pdf_pages(pdf)
    integrity = pdf_integrity(pdf)
    if integrity.startswith("failed"):
        errors.append(f"{pdf}: {integrity}")
    application = load_yaml(app / "application.yaml")
    maximum = application.get("max_pages", 2) if isinstance(application, dict) else 2
    if pages is not None and pages > maximum:
        errors.append(f"{pdf}: {pages} pages exceeds application max_pages={maximum}")

    extracted = app / "resume.txt"
    text_check = "pdftotext unavailable"
    if shutil.which("pdftotext"):
        extraction = subprocess.run(
            ["pdftotext", str(pdf), str(extracted)], text=True, capture_output=True, check=False
        )
        if extraction.returncode:
            text_check = f"pdftotext failed: {extraction.stderr.strip()}"
        else:
            text = extracted.read_text(encoding="utf-8", errors="replace")
            placeholders = sorted(
                token
                for token in ("TODO", "TBD", "Lorem ipsum")
                if token.casefold() in text.casefold()
            )
            text_check = (
                "pass"
                if not placeholders
                else f"failed; placeholders found: {', '.join(placeholders)}"
            )
            if placeholders:
                errors.append(
                    f"{pdf}: extracted text contains placeholders: {', '.join(placeholders)}"
                )

    version = subprocess.run(
        [rendercv_command(), "--version"], text=True, capture_output=True, check=False
    ).stdout.strip()
    report = [
        "# Render Validation",
        "",
        f"- RenderCV: `{version}`",
        "- Schema validation: pass",
        "- PDF rendering: pass",
        f"- Page count: {pages if pages is not None else 'not checked (pdfinfo unavailable)'}",
        f"- PDF integrity: {integrity}",
        f"- pdfinfo warning: {pdfinfo_warning or 'none'}",
        f"- Extracted-text placeholder check: {text_check}",
        "",
        "## Commands",
        "",
        "```bash",
        f"rendercv render {resume.name} --dont-generate-pdf --dont-generate-typst --dont-generate-markdown --dont-generate-html --dont-generate-png",
        f"uv run --extra render career render {app.relative_to(root).as_posix()}",
        "```",
        "",
    ]
    (app / "validation.md").write_text("\n".join(report), encoding="utf-8")
    return errors


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def create_record(path: Path, record_id: str, record_type: str, title: str) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "id": record_id,
        "type": record_type,
        "title": title,
        "technologies": [],
        "domains": [],
        "competencies": [],
        "seniority_signals": [],
        "tags": [],
        "visibility": "internal",
        "verification": "needs-confirmation",
        "related_records": [],
        "claims": [],
    }
    body = "\n".join(
        [
            "# Context",
            "",
            "",
            "# Problem",
            "",
            "",
            "# My contribution",
            "",
            "",
            "# Technical decisions and tradeoffs",
            "",
            "",
            "# Results and metrics",
            "",
            "",
            "# Alternative resume framings",
            "",
            "",
            "# Private notes",
            "",
        ]
    )
    path.write_text(
        f"---\n{yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).strip()}\n---\n\n{body}",
        encoding="utf-8",
    )


def init_application(root: Path, identifier: str, jd: Path, variant: str, max_pages: int) -> Path:
    if slug(identifier) != identifier:
        raise RuntimeError("application id must be lowercase kebab-case")
    variants_path = PROJECT_ROOT / "config" / "resume-variants.yaml"
    variants = load_yaml(variants_path)
    available = variants.get("variants", {}) if isinstance(variants, dict) else {}
    if variant not in available:
        raise RuntimeError(
            f"unknown variant {variant!r}; choose one of: {', '.join(sorted(available))}"
        )
    app = root / "applications" / identifier
    if app.exists():
        raise RuntimeError(f"refusing to overwrite existing application {app}")
    app.mkdir(parents=True)
    shutil.copyfile(jd, app / "job-description.md")
    metadata = {
        "schema_version": 1,
        "id": identifier,
        "created": date.today().isoformat(),
        "variant": variant,
        "max_pages": max_pages,
        "status": "draft",
    }
    (app / "application.yaml").write_text(
        yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8"
    )
    return app


def parse_legacy_date(value: Any) -> str | None:
    if value in (None, "", "Now", "Present"):
        return None
    text = str(value)
    for pattern in ("%b %d, %Y", "%b %Y", "%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            parsed = datetime.strptime(text, pattern)
            return parsed.strftime(
                "%Y-%m-%d" if "%d" in pattern else "%Y-%m" if "%m" in pattern else "%Y"
            )
        except ValueError:
            pass
    raise ValueError(
        f"unsupported legacy date {text!r}; convert it to YYYY, YYYY-MM, or YYYY-MM-DD"
    )


def migrate_legacy(source: Path, destination: Path) -> list[Path]:
    data = load_yaml(source)
    if not isinstance(data, dict) or not isinstance(data.get("timeline"), list):
        raise RuntimeError(f"{source}: expected a top-level timeline list")
    created: list[Path] = []
    for index, item in enumerate(data["timeline"], 1):
        if not isinstance(item, dict):
            raise RuntimeError(f"{source}: timeline item {index} is not a mapping")
        record_type = "role" if item.get("type") == "work" else "project"
        title = str(item.get("title") or f"Imported record {index}")
        record_id = slug(f"legacy-{record_type}-{title}")
        target = destination / f"{record_id}.md"
        if target.exists():
            raise RuntimeError(f"refusing to overwrite {target}")
        achievements = item.get("achievements", []) or []
        metadata: dict[str, Any] = {
            "id": record_id,
            "type": record_type,
            "title": title,
            "start_date": parse_legacy_date(item.get("startDate")),
            "end_date": parse_legacy_date(item.get("endDate")),
            "technologies": item.get("keywords", []) or [],
            "domains": [],
            "competencies": [],
            "seniority_signals": [],
            "tags": ["legacy-import"],
            "visibility": "internal",
            "verification": "user-supplied",
            "related_records": [],
            "claims": [
                {
                    "id": f"{record_id}-achievement-{claim_index}",
                    "statement": str(statement),
                    "visibility": "internal",
                    "confidence": "user-supplied",
                    "safe_to_paraphrase": True,
                    "evidence": [],
                }
                for claim_index, statement in enumerate(achievements, 1)
            ],
        }
        organization = item.get("company/institution")
        if organization:
            metadata["company"] = str(organization)
        metadata = {key: value for key, value in metadata.items() if value is not None}
        body = str(
            item.get("content")
            or "Imported from the legacy timeline. Expand this record before public use."
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"---\n{yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).strip()}\n---\n\n# Context\n\n{body.strip()}\n",
            encoding="utf-8",
        )
        created.append(target)
    return created


def print_result(errors: list[str], success: str) -> int:
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(success)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="career")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="workspace containing career/ and applications/",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "validate", help="validate career records, profile, IDs, claims, evidence, and references"
    )
    sub.add_parser("index", help="validate records and regenerate career/index.md")

    new_record = sub.add_parser("new-record", help="create a Markdown record scaffold")
    new_record.add_argument("path", type=Path)
    new_record.add_argument("--id", required=True)
    new_record.add_argument(
        "--type",
        required=True,
        choices=[
            "company",
            "role",
            "project",
            "initiative",
            "decision",
            "incident",
            "achievement",
            "knowledge",
            "evidence",
        ],
    )
    new_record.add_argument("--title", required=True)

    init = sub.add_parser(
        "init-application", help="create an application directory and preserve its JD"
    )
    init.add_argument("id")
    init.add_argument("--jd", required=True, type=Path)
    init.add_argument("--variant", default="staff-software-engineer")
    init.add_argument("--max-pages", type=int, default=2)

    retrieve = sub.add_parser("retrieve", help="rank records against requirements.yaml")
    retrieve.add_argument("application", type=Path)
    retrieve.add_argument("--limit", type=int, default=20)

    validate_app = sub.add_parser(
        "validate-application", help="validate application artifacts and claim provenance"
    )
    validate_app.add_argument("application", type=Path)
    validate_app.add_argument("--require-pdf", action="store_true")

    validate_resume = sub.add_parser("validate-resume", help="validate resume.yaml with RenderCV")
    validate_resume.add_argument("resume", type=Path)

    render = sub.add_parser(
        "render", help="validate an application and render its PDF with RenderCV"
    )
    render.add_argument("application", type=Path)

    migrate = sub.add_parser(
        "migrate-legacy", help="convert a legacy timeline YAML into Markdown records"
    )
    migrate.add_argument("source", type=Path)
    migrate.add_argument("--destination", type=Path, default=Path("career/experience/imported"))

    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "validate":
            records, errors = validate_knowledge(root)
            return print_result(errors, f"Validated {len(records)} career records.")
        if args.command == "index":
            records, errors = validate_knowledge(root)
            if errors:
                return print_result(errors, "")
            target = write_index(root, records)
            print(f"Wrote {target}")
            return 0
        if args.command == "new-record":
            path = args.path if args.path.is_absolute() else root / args.path
            create_record(path, args.id, args.type, args.title)
            print(f"Created {path}")
            return 0
        if args.command == "init-application":
            jd = args.jd if args.jd.is_absolute() else root / args.jd
            app = init_application(root, args.id, jd, args.variant, args.max_pages)
            print(f"Created {app}")
            return 0
        if args.command == "retrieve":
            app = args.application if args.application.is_absolute() else root / args.application
            requirements, req_errors = validate_requirements(app / "requirements.yaml")
            records, knowledge_errors = validate_knowledge(root)
            errors = req_errors + knowledge_errors
            if errors or requirements is None:
                return print_result(errors, "")
            target = write_retrieval_report(
                root, app, ranked_records(requirements, records), args.limit
            )
            print(f"Wrote {target}")
            return 0
        if args.command == "validate-application":
            app = args.application if args.application.is_absolute() else root / args.application
            return print_result(
                validate_application(root, app, args.require_pdf),
                f"Validated application {app.name}.",
            )
        if args.command == "validate-resume":
            resume = args.resume if args.resume.is_absolute() else root / args.resume
            result = run_rendercv(resume)
            if result.returncode:
                print(result.stdout + result.stderr, file=sys.stderr)
                return result.returncode
            print(f"RenderCV validated {resume}.")
            return 0
        if args.command == "render":
            app = args.application if args.application.is_absolute() else root / args.application
            return print_result(render_application(root, app), f"Rendered {app / 'resume.pdf'}")
        if args.command == "migrate-legacy":
            source = args.source if args.source.is_absolute() else root / args.source
            destination = (
                args.destination if args.destination.is_absolute() else root / args.destination
            )
            created = migrate_legacy(source, destination)
            print(
                f"Created {len(created)} records under {destination}; legacy source was preserved."
            )
            return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
