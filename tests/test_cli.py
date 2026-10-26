from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from career_kb.cli import (
    PROJECT_ROOT,
    create_record,
    init_application,
    load_yaml,
    migrate_legacy,
    parse_record,
    render_application,
    run_rendercv,
    validate_application,
    validate_knowledge,
    validate_requirements,
)


class CareerCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        shutil.copytree(PROJECT_ROOT / "examples" / "demo" / "career", self.root / "career")
        shutil.copytree(
            PROJECT_ROOT / "examples" / "demo" / "applications", self.root / "applications"
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_demo_knowledge_and_application_are_valid(self) -> None:
        records, errors = validate_knowledge(self.root)
        self.assertEqual(3, len(records))
        self.assertEqual([], errors)
        self.assertEqual(
            [],
            validate_application(
                self.root, self.root / "applications" / "2026-08-example-platform"
            ),
        )

    def test_frontmatter_is_required(self) -> None:
        path = self.root / "career" / "projects" / "bad.md"
        path.write_text("# No frontmatter\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing YAML frontmatter"):
            parse_record(path)

    def test_duplicate_ids_and_broken_references_fail(self) -> None:
        source = self.root / "career" / "projects" / "queue-recovery.md"
        duplicate = self.root / "career" / "projects" / "duplicate.md"
        duplicate.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        _, errors = validate_knowledge(self.root)
        self.assertTrue(any("duplicate record id" in error for error in errors))

        duplicate.unlink()
        text = source.read_text(encoding="utf-8").replace("demo-platform-role", "missing-record", 1)
        source.write_text(text, encoding="utf-8")
        _, errors = validate_knowledge(self.root)
        self.assertTrue(any("does not exist" in error for error in errors))

    def test_invalid_visibility_and_missing_evidence_fail(self) -> None:
        path = self.root / "career" / "projects" / "queue-recovery.md"
        text = path.read_text(encoding="utf-8").replace(
            "visibility: public", "visibility: secret", 1
        )
        text = text.replace(
            "evidence:\n      - demo-public-release-report",
            "evidence:\n      - missing-evidence",
            1,
        )
        path.write_text(text, encoding="utf-8")
        _, errors = validate_knowledge(self.root)
        self.assertTrue(any("visibility" in error for error in errors))
        self.assertTrue(any("missing evidence" in error for error in errors))

    def test_unsupported_resume_statement_fails_provenance(self) -> None:
        app = self.root / "applications" / "2026-08-example-platform"
        resume = app / "resume.yaml"
        text = resume.read_text(encoding="utf-8").replace(
            "Platform engineer focused on reliable distributed systems, Kubernetes delivery, and practical technical leadership.",
            "Unsupported new summary.",
            1,
        )
        resume.write_text(text, encoding="utf-8")
        errors = validate_application(self.root, app)
        self.assertTrue(any("does not exactly match" in error for error in errors))

    def test_manifest_rejects_unsupported_additions_and_missing_claims(self) -> None:
        app = self.root / "applications" / "2026-08-example-platform"
        manifest_path = app / "claim-manifest.yaml"
        manifest = load_yaml(manifest_path)
        manifest["claims"][0]["unsupported_additions"] = ["invented scope"]
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        errors = validate_application(self.root, app)
        self.assertTrue(any("unsupported_additions" in error for error in errors))

        manifest["claims"][0]["unsupported_additions"] = []
        manifest["claims"].pop()
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        errors = validate_application(self.root, app)
        self.assertTrue(any("unsupported resume statement" in error for error in errors))

    def test_non_public_source_fails_provenance(self) -> None:
        path = self.root / "career" / "projects" / "queue-recovery.md"
        text = path.read_text(encoding="utf-8").replace(
            "visibility: public", "visibility: private", 1
        )
        path.write_text(text, encoding="utf-8")
        errors = validate_application(
            self.root, self.root / "applications" / "2026-08-example-platform"
        )
        self.assertTrue(any("uses non-public source" in error for error in errors))

    def test_invented_employer_and_dates_fail_structural_provenance(self) -> None:
        app = self.root / "applications" / "2026-08-example-platform"
        resume = app / "resume.yaml"
        text = resume.read_text(encoding="utf-8").replace("Example Systems", "Invented Corp", 1)
        resume.write_text(text, encoding="utf-8")
        errors = validate_application(self.root, app)
        self.assertTrue(any("employer/role does not match" in error for error in errors))

        text = text.replace("Invented Corp", "Example Systems", 1).replace(
            "start_date: 2022-01", "start_date: 2021-01", 1
        )
        resume.write_text(text, encoding="utf-8")
        errors = validate_application(self.root, app)
        self.assertTrue(any("dates do not match" in error for error in errors))

    def test_requirements_schema_rejects_missing_fields(self) -> None:
        path = self.root / "requirements.yaml"
        path.write_text("schema_version: 1\ncompany: Example\n", encoding="utf-8")
        _, errors = validate_requirements(path)
        self.assertTrue(any("required property" in error for error in errors))

    def test_record_and_application_scaffolds_refuse_overwrite(self) -> None:
        record = self.root / "career" / "experience" / "new-role.md"
        create_record(record, "new-role", "role", "New Role")
        self.assertEqual("new-role", parse_record(record).metadata["id"])
        with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
            create_record(record, "new-role", "role", "New Role")

        jd = self.root / "input-jd.md"
        jd.write_text("# Role\n", encoding="utf-8")
        app = init_application(self.root, "2026-08-new-role", jd, "staff-software-engineer", 2)
        self.assertEqual(
            jd.read_text(encoding="utf-8"), (app / "job-description.md").read_text(encoding="utf-8")
        )
        with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
            init_application(self.root, "2026-08-new-role", jd, "staff-software-engineer", 2)

    def test_legacy_migration_preserves_source_and_marks_import_internal(self) -> None:
        source = self.root / "legacy.yaml"
        source.write_text(
            yaml.safe_dump(
                {
                    "timeline": [
                        {
                            "title": "Engineer",
                            "type": "work",
                            "company/institution": "Example Co",
                            "startDate": "Jan 01, 2020",
                            "endDate": "Dec 31, 2021",
                            "content": "Maintained the platform.",
                            "achievements": ["Reduced recovery time."],
                            "keywords": ["Python"],
                        }
                    ]
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        created = migrate_legacy(source, self.root / "career" / "experience" / "imported")
        self.assertTrue(source.exists())
        metadata = parse_record(created[0]).metadata
        self.assertEqual("internal", metadata["visibility"])
        self.assertEqual("user-supplied", metadata["verification"])
        self.assertEqual("2020-01-01", metadata["start_date"])

    @unittest.skipUnless(
        shutil.which("rendercv"), "run with `uv run --extra render python -m unittest`"
    )
    def test_demo_resume_passes_rendercv_validation(self) -> None:
        result = run_rendercv(
            self.root / "applications" / "2026-08-example-platform" / "resume.yaml"
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    @unittest.skipUnless(
        shutil.which("rendercv"), "run with `uv run --extra render python -m unittest`"
    )
    def test_demo_application_renders_requested_pdf(self) -> None:
        app = self.root / "applications" / "2026-08-example-platform"
        self.assertEqual([], render_application(self.root, app))
        self.assertGreater((app / "resume.pdf").stat().st_size, 1_000)
        self.assertFalse((app / "rendercv_output").exists())


if __name__ == "__main__":
    unittest.main()
