#!/usr/bin/env python3
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0.

import json
import os
import shutil
import sys
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

import update_oink


class UpgradeTest(unittest.TestCase):
    def test_toolchain_failure_precedes_backup_and_lock_mutation(self):
        with patch.object(update_oink, "preflight"), \
             patch.object(update_oink, "check_toolchain", side_effect=ValueError("missing compiler")), \
             patch.object(update_oink, "prepare_work") as work, \
             patch.object(update_oink, "command") as command, \
             patch("sys.argv", ["update", "v1.3.1"]):
            with self.assertRaisesRegex(ValueError, "missing compiler"):
                update_oink.main()
            work.assert_not_called()
            command.assert_not_called()

    def test_target_hugo_and_go_requirements_fail_before_compilation(self):
        with tempfile.TemporaryDirectory() as directory:
            theme = Path(directory)
            (theme / "theme.toml").write_text('min_version = "0.170.0"\n')
            (theme / "go.mod").write_text('module example.test/theme\n\ngo 1.27.3\n')
            for hugo in ("hugo v0.168.0+extended", "hugo v0.169.0"):
                with patch.object(update_oink, "prior_release", return_value={"Dir": directory}), \
                     patch.object(update_oink, "tool_versions", return_value={"hugo": hugo, "go": "go1.27.3"}), \
                     patch.object(update_oink.subprocess, "run") as compile:
                    with self.assertRaisesRegex(ValueError, "Hugo >= 0.170.0"):
                        update_oink.check_toolchain(theme, "v1.4.0")
                    compile.assert_not_called()
            with patch.object(update_oink, "prior_release", return_value={"Dir": directory}), \
                 patch.object(update_oink, "tool_versions", return_value={"hugo": "hugo v0.170.0+extended", "go": "go1.27.2"}), \
                 patch.object(update_oink.subprocess, "run") as compile:
                with self.assertRaisesRegex(ValueError, "Go >= 1.27.3"):
                    update_oink.check_toolchain(theme, "v1.4.0")
                compile.assert_not_called()

    @unittest.skipUnless(shutil.which(os.environ.get("HUGO_BIN", "hugo")), "Hugo is required")
    def test_real_hugo_native_css_smoke_never_invokes_sass(self):
        if update_oink.version_tuple(update_oink.tool_output([os.environ.get("HUGO_BIN", "hugo"), "version"])) < (0, 169, 0):
            self.skipTest("Hugo >= 0.169.0 is required")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "theme.toml").write_text('min_version = "0.169.0"\n')
            (root / "go.mod").write_text('module example.test/theme\n\ngo 1.27.3\n')
            marker = root / "sass-invoked"
            shim = root / "sass"
            shim.write_text(f"#!{sys.executable}\nfrom pathlib import Path\n"
                            f"Path({str(marker)!r}).touch()\nraise SystemExit(17)\n")
            shim.chmod(0o755)
            with patch.object(update_oink, "prior_release", return_value={"Dir": directory}), \
                 patch.dict(os.environ, {"PATH": str(root) + os.pathsep + os.environ["PATH"]}):
                versions = update_oink.check_toolchain(root, "v1.4.0")
            self.assertNotIn("sass", versions)
            self.assertFalse(marker.exists(), "CSS builds must not call an external compiler")

    def test_work_directory_preserves_before_captures_and_first_lock_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root, work = Path(directory) / "source", Path(directory) / "upgrade"
            root.mkdir()
            for name in ("go.mod", "go.sum", "oink-overrides.json"):
                (root / name).write_text("original " + name)
            (work / "before").mkdir(parents=True)
            capture = work / "before/home.png"
            capture.write_bytes(b"baseline capture")
            baseline = root / "oink-overrides.json"
            for name in ("before-site", "notes", "tools", "logs"):
                (work / name).mkdir()
                (work / name / "keep.txt").write_text("helper asset")
            resolved = update_oink.prepare_work(root, baseline, work, False, "v1.3.1")
            (root / "go.mod").write_text("upgraded lock")
            (work / "toolchain.json").write_text("existing runner output")
            self.assertEqual(update_oink.prepare_work(root, baseline, work, True, "v1.3.1"), resolved)
            self.assertEqual((work / "before/go.mod").read_text(), "original go.mod")
            self.assertEqual(capture.read_bytes(), b"baseline capture")
            with self.assertRaisesRegex(ValueError, "requires --resume"):
                update_oink.prepare_work(root, baseline, work, False, "v1.3.1")
            with self.assertRaisesRegex(ValueError, "another target"):
                update_oink.prepare_work(root, baseline, work, True, "v1.4.0")
            with self.assertRaisesRegex(ValueError, "another target or checkout"):
                update_oink.prepare_work(root / "other", baseline, work, True, "v1.3.1")
            (work / "before/go.sum").unlink()
            with self.assertRaisesRegex(ValueError, "incomplete"):
                update_oink.prepare_work(root, baseline, work, True, "v1.3.1")
            self.assertEqual((work / "before/go.mod").read_text(), "original go.mod")

    def test_work_directory_rejects_repository_and_preserves_existing_reserved_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            baseline = root / "oink-overrides.json"
            for name in ("go.mod", "go.sum", "oink-overrides.json"):
                (root / name).write_text("original " + name)
            internal = root / "notes"
            internal.mkdir()
            internal_file = internal / "toolchain.json"
            internal_file.write_text("user settings")
            for forbidden in (internal, root, root.parent):
                with self.subTest(forbidden=forbidden), self.assertRaisesRegex(ValueError, "outside the repository"):
                    update_oink.prepare_work(root, baseline, forbidden, False, "v1.3.1")
            self.assertEqual(internal_file.read_text(), "user settings")
            self.assertFalse((internal / "before").exists())
            for reserved in ("toolchain.json", "resolved.json", "build-plan.json", "strict", "artifacts", "site", "ai",
                             "ai-disabled", "hugo-cache", "version-cache", "after", "validation-snapshot.json", "ai.json", "ai-disabled.json"):
                work = Path(directory) / ("external-" + reserved)
                work.mkdir()
                existing = work / reserved
                existing.write_text("user file")
                for resume in (False, True):
                    with self.subTest(reserved=reserved, resume=resume), self.assertRaisesRegex(ValueError, "reserved runner outputs"):
                        update_oink.prepare_work(root, baseline, work, resume, "v1.3.1")
                    self.assertEqual(existing.read_text(), "user file")
                    self.assertFalse((work / "before").exists())
                    self.assertFalse((work / "review.json").exists())

    def test_fresh_resume_records_that_backup_can_already_pin_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root, work = Path(directory) / "source", Path(directory) / "upgrade"
            root.mkdir()
            for name in ("go.mod", "go.sum", "oink-overrides.json"):
                (root / name).write_text("already upgraded")
            update_oink.prepare_work(root, root / "oink-overrides.json", work, True, "v1.3.1")
            self.assertTrue(json.loads((work / "review.json").read_text())["startedFromResume"])

    def test_work_directory_rejects_symlinks_and_enclosing_checkouts_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, other, link = base / "source", base / "other", base / "link"
            root.mkdir()
            other.mkdir()
            (other / ".git").mkdir()
            link.symlink_to(base / "unrelated")
            for work, message in ((other / "evidence", "outside every Git checkout"),
                                  (link / "evidence", "symbolic link")):
                with self.assertRaisesRegex(ValueError, message):
                    update_oink.prepare_work(root, root / "baseline.json", work, False, "v1.6.0")
                self.assertFalse(work.exists())

    def test_report_atomic_replacement_does_not_follow_predictable_temporary_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory) / "work"
            work.mkdir()
            victim = Path(directory) / "unrelated.txt"
            victim.write_text("preserve unrelated data")
            (work / "review.json.tmp").symlink_to(victim)
            (work / "report.md").symlink_to(victim)
            update_oink.write_report(work, {"status": "prepared", "to": "v1.6.0"})
            self.assertEqual(victim.read_text(), "preserve unrelated data")
            self.assertEqual(json.loads((work / "review.json").read_text())["status"], "prepared")
            self.assertFalse((work / "review.json").is_symlink())
            self.assertFalse((work / "report.md").is_symlink())
            self.assertEqual(list(work.glob(".oink-report-*")), [])

    def test_work_directory_rejects_linked_writable_children_on_start_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "source"
            root.mkdir()
            for name in ("go.mod", "go.sum", "baseline.json"):
                (root / name).write_text("original " + name)
            victim = base / "unrelated.txt"
            victim.write_text("preserve unrelated data")
            for index, name in enumerate(("before", "logs/001.log", "before-browser/metrics.json", "review.json",
                                           "report.md", "toolchain.json", "before-source", "strict/output.html")):
                for resume in (False, True):
                    with self.subTest(path=name, resume=resume):
                        work = base / f"work-{index}-{resume}"
                        work.mkdir()
                        if resume:
                            update_oink.prepare_work(root, root / "baseline.json", work, False, "v1.6.0")
                        linked = work / name
                        if linked.is_dir():
                            shutil.rmtree(linked)
                        elif linked.exists():
                            linked.unlink()
                        linked.parent.mkdir(parents=True, exist_ok=True)
                        linked.symlink_to(victim)
                        with self.assertRaisesRegex(ValueError, "symbolic link"):
                            update_oink.prepare_work(root, root / "baseline.json", work, resume, "v1.6.0")
                        self.assertEqual(victim.read_text(), "preserve unrelated data")
                        self.assertTrue(linked.is_symlink())

    def test_check_baseline_rejects_upgrade_options_without_toolchain_or_lock_changes(self):
        with patch.object(update_oink, "download_locked") as download, \
             patch.object(update_oink, "check_toolchain") as tools, \
             patch("sys.argv", ["update", "--check-baseline", "--work-dir", "artifacts"]):
            with self.assertRaises(SystemExit):
                update_oink.main()
            tools.assert_not_called()
            download.assert_not_called()

    def test_invalid_version_stops_before_commands(self):
        with patch.object(update_oink.subprocess, "check_output") as command:
            with self.assertRaises(ValueError):
                update_oink.preflight(Path("."), "latest", False)
            command.assert_not_called()

    def test_dirty_tree_requires_explicit_resume(self):
        with patch.object(update_oink.subprocess, "check_output", return_value=" M file"):
            with self.assertRaisesRegex(ValueError, "not clean"):
                update_oink.preflight(Path("."), "v1.1.0", False)
        with patch.object(update_oink, "locked_version", return_value="v1.1.0"):
            update_oink.preflight(Path("."), "v1.1.0", True)
            with self.assertRaises(ValueError):
                update_oink.preflight(Path("."), "v1.2.0", True)

    def test_locale_override_uses_upstream_canonical_case(self):
        with tempfile.TemporaryDirectory() as d:
            root, upstream = Path(d) / "site", Path(d) / "theme"
            (root / "i18n").mkdir(parents=True)
            (upstream / "i18n").mkdir(parents=True)
            (root / "i18n/zh-CN.yaml").write_text("local translation")
            (upstream / "i18n/zh-cn.yaml").write_text("upstream translation")
            files = update_oink.snapshot(root, upstream)
            self.assertIn("i18n/zh-cn.yaml", files)
            self.assertNotIn("i18n/zh-CN.yaml", files)
            self.assertIsNotNone(files["i18n/zh-cn.yaml"])

    def test_review_catches_added_changed_deleted_files(self):
        self.assertEqual(update_oink.changes({"old": "a", "changed": "b", "stable": "c"},
                                            {"new": "d", "changed": "e", "stable": "c"}),
                         ["changed", "new", "old"])
        self.assertEqual(update_oink.changes({"a": "b"}, {"a": "b"}), [])

    def test_resume_after_baseline_failure_requires_original_locks(self):
        with tempfile.TemporaryDirectory() as directory:
            root, work = Path(directory) / "source", Path(directory) / "upgrade"
            root.mkdir()
            for name in ("go.mod", "go.sum", "baseline.json"):
                (root / name).write_text("original")
            update_oink.prepare_work(root, root / "baseline.json", work, False, "v1.6.0")
            with patch.object(update_oink, "locked_version", return_value="v1.5.1"):
                update_oink.preflight(root, "v1.6.0", True, work)
                (root / "go.sum").write_text("unrelated update")
                with self.assertRaisesRegex(ValueError, "unchanged original locks"):
                    update_oink.preflight(root, "v1.6.0", True, work)

    def test_measured_asset_bytes_include_split_search_without_other_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixtures = {"main.css": "body{}", "core.js": "void 0;", "offline-search-index.en.abc.json": "[1]",
                        "offline-search-body.cn.abc.json": "[2,3]", "other.json": "not search", "index.html": "<html>"}
            for name, content in fixtures.items():
                (root / name).write_text(content)
            metrics = update_oink.site_metrics(root, 1.25)
            self.assertEqual(metrics["bytes"], {"css": 6, "js": 7, "search": 8})
            self.assertEqual(metrics["htmlPages"], 1)
            self.assertNotIn("other.json", metrics["files"])
            self.assertEqual(metrics["buildSeconds"], 1.25)

    def test_failed_step_keeps_log_and_status(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / "review.json").write_text("{}")
            with patch.object(update_oink, "ACTIVE_WORK", work):
                with self.assertRaises(subprocess.CalledProcessError):
                    update_oink.run([sys.executable, "-c", "print('failure evidence'); raise SystemExit(7)"])
            step = json.loads((work / "review.json").read_text())["steps"][0]
            self.assertEqual(step["status"], "failed")
            self.assertIn("failure evidence", Path(step["log"]).read_text())
            self.assertGreaterEqual(step["seconds"], 0)

    def test_report_only_attributes_version_outcomes_to_the_builder(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            source_test = {"command": [sys.executable, "-m", "unittest", "discover"],
                           "log": "source-tests.log", "status": "passed", "seconds": 1.5,
                           "versions": {"fixture": "cache"}}
            builder = {"command": [sys.executable, "/repo/scripts/build_versions.py", "--workers", "2"],
                       "log": "versions.log", "status": "passed", "versions": {"latest": "built", "1.7": "cache"}}
            direct = {"command": ["scripts/build_versions.py"], "versions": {"1.5": "built"}}
            argument = {"command": [sys.executable, "-m", "build_versions.py"], "versions": {"argument": "cache"}}
            # Loading a pre-existing report must remove old false attribution,
            # while retaining the original commands, logs and statuses.
            (work / "review.json").write_text(json.dumps({"steps": [source_test, builder, direct, argument]}))
            update_oink.update_report(work, status="validating")
            steps = json.loads((work / "review.json").read_text())["steps"]
            self.assertEqual(steps[0], {key: value for key, value in source_test.items() if key != "versions"})
            self.assertEqual(steps[1:3], [builder, direct])
            self.assertEqual(steps[3], {"command": argument["command"]})
            rendered = (work / "report.md").read_text()
            self.assertNotIn("fixture: cache", rendered)
            self.assertNotIn("argument: cache", rendered)
            self.assertIn("latest: built, 1.7: cache", rendered)
            self.assertIn("1.5: built", rendered)

    def test_css_selectors_and_native_fields_are_watched_without_local_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            root, upstream = Path(directory) / "site", Path(directory) / "theme"
            root.mkdir()
            for name in ("assets/css/td/search.css", "layouts/_shortcodes/field.html"):
                target = upstream / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("original")
            previous = update_oink.snapshot(root, upstream)
            (upstream / "assets/css/td/search.css").write_text("new selectors")
            (upstream / "layouts/_shortcodes/field.html").unlink()
            self.assertEqual(update_oink.describe_changes(previous, update_oink.snapshot(root, upstream)),
                             ["changed: assets/css/td/search.css", "removed: layouts/_shortcodes/field.html"])

    def test_failed_validation_keeps_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "source"
            root.mkdir()
            (root / "go.mod").write_text("before mod")
            (root / "go.sum").write_text("before sum")
            baseline = root / "baseline.json"
            original = json.dumps({"version": "v1.0.0", "files": {"a": "old"}})
            baseline.write_text(original)
            with patch.object(update_oink, "ROOT", root), patch.object(update_oink, "check_toolchain", return_value={}), patch.object(update_oink, "verify_hugo_graph", return_value="verified"), \
                 patch.object(update_oink, "prior_release", return_value={"Dir": str(root / "prior")}), \
                 patch.object(update_oink, "BASELINE", baseline), patch.object(update_oink, "preflight"), patch.object(update_oink, "prune_checksums"), \
                 patch.object(update_oink, "locked_version", return_value="v1.1.0"), \
                 patch.object(update_oink, "download_locked", return_value={"Dir": d}), \
                 patch.object(update_oink, "snapshot", return_value={"a": "new"}), \
                 patch.object(update_oink.tempfile, "mkdtemp", return_value=str(root.parent / "artifacts")), \
                 patch.object(update_oink, "capture_before"), \
                 patch.object(update_oink, "validate", side_effect=ValueError("test failed")), \
                 patch("sys.argv", ["update", "v1.1.0", "--resume", "--accept-reviewed"]):
                with self.assertRaisesRegex(ValueError, "test failed"):
                    update_oink.main()
            self.assertEqual(baseline.read_text(), original)
            report = json.loads((root.parent / "artifacts/review.json").read_text())
            self.assertEqual(report["priorModuleDir"], str(root / "prior"))
            self.assertEqual(report["targetModuleDir"], d)
            self.assertEqual(report["changes"], [{"path": "a", "kind": "changed",
                                                 "reason": "local override or watched upstream interface"}])
            self.assertIn("not a list of required local edits", report["reviewMeaning"])
            self.assertIn("v1.1.0 --resume --accept-reviewed", report["resumeCommand"])
            (root / "go.mod").write_text("changed")
            (root / "go.sum").write_text("changed")
            subprocess.run(report["recoveryCommand"], shell=True, check=True)
            self.assertEqual((root / "go.mod").read_text(), "before mod")
            self.assertEqual((root / "go.sum").read_text(), "before sum")

    def test_quick_cannot_accept_baseline_and_full_retry_runs_every_gate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "source"
            root.mkdir()
            (root / "go.mod").write_text("before mod")
            (root / "go.sum").write_text("before sum")
            baseline = root / "baseline.json"
            original = json.dumps({"version": "v1.1.0", "files": {"a": "same"}})
            baseline.write_text(original)
            with patch.object(update_oink, "ROOT", root), patch.object(update_oink, "check_toolchain", return_value={}), patch.object(update_oink, "verify_hugo_graph", return_value="verified"), \
                 patch.object(update_oink, "prior_release", return_value={"Dir": str(root / "prior")}), \
                 patch.object(update_oink, "BASELINE", baseline), patch.object(update_oink, "preflight"), patch.object(update_oink, "prune_checksums"), \
                 patch.object(update_oink, "locked_version", return_value="v1.1.0"), \
                 patch.object(update_oink, "command") as command, \
                 patch.object(update_oink, "download_locked", return_value={"Dir": d}), \
                 patch.object(update_oink, "snapshot", return_value={"a": "same"}), \
                 patch.object(update_oink.tempfile, "mkdtemp", return_value=str(root.parent / "artifacts")), \
                 patch.object(update_oink, "capture_before"), patch.object(update_oink, "performance_comparison", return_value={}), \
                 patch.object(update_oink, "validate") as validate, \
                 patch("sys.argv", ["update", "v1.1.0", "--mode", "quick"]):
                update_oink.main()
                self.assertEqual(baseline.read_text(), original)
                self.assertEqual(validate.call_args.args[1], "quick")
                report = json.loads((root.parent / "artifacts/review.json").read_text())
                self.assertEqual(report["status"], "quick-passed")
                with patch("sys.argv", ["update", "v1.1.0", "--resume", "--work-dir", str(root.parent / "artifacts")]):
                    update_oink.main()
                command.assert_not_called()
                self.assertEqual(validate.call_count, 2)
            self.assertEqual(json.loads(baseline.read_text())["version"], "v1.1.0")

    def test_unreviewed_change_collects_evidence_without_accepting_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "source"
            root.mkdir()
            (root / "go.mod").write_text("before mod")
            (root / "go.sum").write_text("before sum")
            baseline = root / "baseline.json"
            baseline.write_text(json.dumps({"version": "v1.0.0", "files": {"a": "old"}}))
            with patch.object(update_oink, "ROOT", root), patch.object(update_oink, "check_toolchain", return_value={}), patch.object(update_oink, "verify_hugo_graph", return_value="verified"), \
                 patch.object(update_oink, "prior_release", return_value={"Dir": str(root / "prior")}), \
                 patch.object(update_oink, "BASELINE", baseline), patch.object(update_oink, "preflight"), patch.object(update_oink, "prune_checksums"), \
                 patch.object(update_oink, "locked_version", return_value="v1.1.0"), \
                 patch.object(update_oink, "download_locked", return_value={"Dir": d}), \
                 patch.object(update_oink, "snapshot", return_value={"a": "new"}), \
                 patch.object(update_oink.tempfile, "mkdtemp", return_value=str(root.parent / "artifacts")), \
                 patch.object(update_oink, "capture_before"), patch.object(update_oink, "performance_comparison", return_value={}), \
                 patch.object(update_oink, "validate") as validate, \
                 patch("sys.argv", ["update", "v1.1.0", "--resume"]):
                with self.assertRaisesRegex(ValueError, "review required"):
                    update_oink.main()
                validate.assert_called_once()
                self.assertEqual(json.loads(baseline.read_text())["version"], "v1.0.0")
                report = json.loads((root.parent / "artifacts/review.json").read_text())
                self.assertEqual(report["status"], "review-required")
                self.assertEqual(report["validationCompleted"], "full")


if __name__ == "__main__":
    unittest.main()
