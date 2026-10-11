#!/usr/bin/env python3
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0.

from pathlib import Path
import tempfile
import unittest
import json
import os
import subprocess
import sys
from unittest.mock import patch

import update_oink

from oink_module import MODULE
from update_oink import describe_changes, prune_checksums, snapshot


class UpgradeInventoryTest(unittest.TestCase):
    def test_default_hugo_is_resolved_from_subprocess_path(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(update_oink.shutil, "which") as which:
            self.assertNotIn("HUGO_BIN", update_oink.release_environment())
            which.assert_not_called()

    def test_release_graph_ignores_local_preview_environment_and_restores_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hugo = root / "hugo"
            hugo.write_text(f"#!{sys.executable}\n" +
                            "import os\n" +
                            "assert 'HUGO_MODULE_REPLACEMENTS' not in os.environ\n" +
                            "assert os.environ['GOWORK'] == 'off'\n" +
                            "assert os.environ['HUGO_MODULE_WORKSPACE'] == 'off'\n" +
                            f"print('site {MODULE}@v1.2.0')\n")
            hugo.chmod(0o755)
            preview = {"HUGO_BIN": str(hugo), "HUGO_MODULE_REPLACEMENTS": "oink -> /tmp/local-theme",
                       "GOWORK": "/tmp/go.work", "HUGO_MODULE_WORKSPACE": "/tmp/hugo.work"}
            with patch.dict(os.environ, preview):
                with update_oink.isolated_release():
                    update_oink.verify_hugo_graph(root, "v1.2.0")
                for key, value in preview.items():
                    self.assertEqual(os.environ[key], value)

    def test_hugo_graph_rejects_wrong_release_replacement_and_vendor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for graph in (f"site {MODULE}@v1.1.0\n", f"site {MODULE}@v1.2.0+vendor\n",
                          f"site {MODULE}@v1.2.0 => /tmp/local\n", "site unrelated@v1.2.0\n",
                          f"site {MODULE}@v1.2.0\nsite {MODULE}@v1.1.0\n",
                          f"site {MODULE}@v1.2.0\n{MODULE}@v1.1.0 dependency@v1.0.0\n",
                          f"site {MODULE}@v1.2.0\n{MODULE}@v1.2.0 => /tmp/local\n"):
                with patch.object(update_oink.subprocess, "check_output", return_value=graph):
                    with self.assertRaisesRegex(ValueError, "expected Hugo"):
                        update_oink.verify_hugo_graph(root, "v1.2.0")
            (root / "_vendor").mkdir()
            with patch.object(update_oink.subprocess, "check_output") as command:
                with self.assertRaisesRegex(ValueError, "_vendor"):
                    update_oink.verify_hugo_graph(root, "v1.2.0")
                with self.assertRaisesRegex(ValueError, "_vendor"):
                    update_oink.preflight(root, "v1.2.0", False)
                command.assert_not_called()

    def test_hugo_graph_accepts_published_theme_with_outgoing_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            graph = f"site {MODULE}@v1.2.0\n{MODULE}@v1.2.0 dependency@v1.0.0\n"
            with patch.object(update_oink.subprocess, "check_output", return_value=graph):
                self.assertEqual(update_oink.verify_hugo_graph(Path(directory), "v1.2.0"), graph)

    def test_validation_subprocesses_inherit_isolation_and_absolute_hugo_path(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / "resolved.json").write_text(json.dumps({"versions": [{"id": "latest", "sha": "example"}]}))
            observations = []

            def run(argv, **kwargs):
                env = kwargs.get("env") or os.environ
                observations.append(list(argv))
                self.assertNotIn("HUGO_MODULE_REPLACEMENTS", env)
                self.assertEqual(env["GOWORK"], "off")
                self.assertEqual(env["HUGO_MODULE_WORKSPACE"], "off")
                self.assertEqual(env["HUGO_BIN"], "/resolved/hugo")

            with patch.dict(os.environ, {"HUGO_BIN": "./relative-hugo", "HUGO_MODULE_REPLACEMENTS": "preview"}), \
                 patch.object(update_oink.shutil, "which", return_value="/resolved/hugo"), \
                 patch.object(update_oink, "validation_snapshot", return_value="local-snapshot"), \
                 patch.object(update_oink, "run", side_effect=run):
                update_oink.validate(work)
            self.assertTrue(any("build" in argv and "--version" in argv for argv in observations))
            self.assertTrue(any(argv[0] == "/resolved/hugo" for argv in observations))
            self.assertTrue(any("discover" in argv for argv in observations))
            prepare = next(argv for argv in observations if "prepare" in argv)
            self.assertEqual(prepare[prepare.index("--latest-sha") + 1], "local-snapshot")

    def test_null_inventory_hashes_classify_added_and_removed_upstream_files(self):
        self.assertEqual(describe_changes({"new": None, "gone": "old"}, {"new": "hash", "gone": None}),
                         ["removed: gone", "added: new"])

    def test_validation_builds_both_ai_modes_before_browser_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / "resolved.json").write_text(json.dumps({"versions": []}))
            with patch.object(update_oink, "validation_snapshot", return_value="local-snapshot"), \
                 patch.object(update_oink, "run") as run:
                update_oink.validate(work)
            calls = run.call_args_list
            browser = next(call for call in calls if call.args[0] == ["npm", "run", "test:ci"])
            for name, config, variable in [("ai", "ai-enabled", "AI_SITE_ROOT"),
                                            ("ai-disabled", "ai-disabled", "AI_DISABLED_SITE_ROOT")]:
                self.assertEqual(browser.kwargs["env"][variable], str(work / name))
                builds = [call for call in calls if "--destination" in call.args[0]
                          and call.args[0][call.args[0].index("--destination") + 1] == work / name]
                self.assertEqual(len(builds), 1)
                self.assertIn(f"tests/e2e/{config}.yaml", str(builds[0].args[0]))
                self.assertLess(calls.index(builds[0]), calls.index(browser))

    def test_validation_snapshot_captures_worktree_sources_without_mutating_git_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            work = Path(directory) / "report"
            work.mkdir()

            def git(*args):
                return subprocess.check_output(["git", "-c", "user.name=Test", "-c", "user.email=test@localhost", *args],
                                               cwd=root, text=True).strip()

            def write(name, text):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)

            git("init", "-q")
            names = ["content/staged.md", "content/unstaged.md", "static/staged.txt",
                     "content/deleted.md", "static/deleted.txt", "content/ignored/tracked.md", "unrelated.txt"]
            for name in names:
                write(name, "head")
            # Track one ignored-directory file before introducing ignore rules.
            git("add", ".")
            write(".gitignore", "content/ignored/\nstatic/ignored/\n")
            git("add", ".gitignore")
            git("commit", "-qm", "initial")
            head = git("rev-parse", "HEAD")
            write("content/staged.md", "staged")
            write("static/staged.txt", "staged")
            write("unrelated.txt", "staged unrelated")
            (root / "static/deleted.txt").unlink()
            git("add", "-A")
            write("content/staged.md", "working tree wins")
            write("content/unstaged.md", "unstaged")
            write("content/ignored/tracked.md", "tracked ignored update")
            (root / "content/deleted.md").unlink()
            write("content/new.md", "new content")
            write("static/new.txt", "new asset")
            write("content/ignored/new.md", "ignored content")
            write("static/ignored/new.txt", "ignored asset")
            write("unrelated-new.txt", "exclude untracked")
            index = (root / ".git/index").read_bytes()
            status = git("status", "--porcelain")
            refs = git("show-ref")
            config = git("config", "--local", "--list")
            latest = update_oink.validation_snapshot(root, work)
            self.assertNotEqual(latest, head)
            for name, value in {"content/staged.md": "working tree wins", "content/unstaged.md": "unstaged",
                                "static/staged.txt": "staged", "content/new.md": "new content", "static/new.txt": "new asset",
                                "content/ignored/tracked.md": "tracked ignored update", "unrelated.txt": "head"}.items():
                self.assertEqual(git("show", f"{latest}:{name}"), value)
            paths = git("ls-tree", "-r", "--name-only", latest).splitlines()
            for name in ["content/deleted.md", "static/deleted.txt", "content/ignored/new.md",
                         "static/ignored/new.txt", "unrelated-new.txt"]:
                self.assertNotIn(name, paths)
            self.assertEqual(git("rev-parse", "HEAD"), head)
            self.assertEqual((root / ".git/index").read_bytes(), index)
            self.assertEqual(git("status", "--porcelain"), status)
            self.assertEqual(git("show-ref"), refs)
            self.assertEqual(git("config", "--local", "--list"), config)
            report = json.loads((work / "validation-snapshot.json").read_text())
            self.assertEqual(report["latestSha"], latest)
            self.assertEqual(report["scope"], ["content", "static"])
            self.assertEqual(git("show", "-s", "--format=%an <%ae>", latest), "OINK validation <validation@localhost>")
            git("reset", "--hard", "-q", head)
            git("clean", "-fdq")
            def commits():
                return {line for line in git("cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype)").splitlines()
                        if line.endswith(" commit")}
            before_commits = commits()
            # Ignored untracked assets remain and must still not produce a snapshot.
            self.assertEqual(update_oink.validation_snapshot(root, work), head)
            self.assertEqual(commits(), before_commits)

    def test_resume_cleans_interrupted_upgrade_before_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "go.mod").write_text("module fixture")
            target = f"{MODULE} v1.1.0 h1:new\n{MODULE} v1.1.0/go.mod h1:newmod\n"
            (root / "go.sum").write_text(f"{MODULE} v1.0.0 h1:old\n" + target)
            baseline = root / "baseline.json"
            baseline.write_text(json.dumps({"version": "v1.1.0", "files": {}}))

            def download(path):
                self.assertEqual((path / "go.sum").read_text(), target)
                return {"Dir": str(root)}

            with patch.object(update_oink, "ROOT", root), patch.object(update_oink, "BASELINE", baseline), \
                 patch.object(update_oink, "locked_version", return_value="v1.1.0"), \
                 patch.object(update_oink, "download_locked", side_effect=download), \
                 patch.object(update_oink, "verify_hugo_graph", return_value="verified"), \
                 patch.object(update_oink, "snapshot", return_value={}), \
                 patch.object(update_oink, "validate") as validate, \
                 patch.object(update_oink, "command") as command, \
                 patch.object(update_oink.tempfile, "mkdtemp", return_value=directory), \
                 patch("sys.argv", ["update", "v1.1.0", "--resume"]):
                update_oink.main()
                update_oink.main()
                command.assert_not_called()
                self.assertEqual(validate.call_count, 2)

    def test_data_override_and_locale_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root, upstream = Path(directory) / "site", Path(directory) / "theme"
            for base, paths in [(root, ["data/brand.yaml", "data/site-only.yaml", "i18n/zh_CN.yaml"]),
                                (upstream, ["data/brand.yaml", "data/upstream-only.yaml", "i18n/zh-cn.yaml"])]:
                for name in paths:
                    path = base / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("value")
            result = snapshot(root, upstream)
            self.assertIn("data/brand.yaml", result)
            self.assertIn("i18n/zh-cn.yaml", result)
            self.assertNotIn("data/site-only.yaml", result)
            self.assertNotIn("data/upstream-only.yaml", result)
            before = dict(result)
            (root / "data/brand.yaml").unlink()
            self.assertIn("removed: data/brand.yaml", describe_changes(before, snapshot(root, upstream)))

    def test_change_diagnostics(self):
        self.assertEqual(describe_changes({"b": "old", "c": "old"}, {"a": "new", "b": "new"}),
                         ["added: a", "changed: b", "removed: c"])

    def test_upgrade_removes_old_checksums(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = f"{MODULE} v1.0.0 h1:old\n{MODULE} v1.0.0/go.mod h1:oldmod\n"
            new = f"{MODULE} v1.1.0 h1:new\n{MODULE} v1.1.0/go.mod h1:newmod\n"
            (root / "go.sum").write_text(old + new)
            prune_checksums(root, "v1.1.0")
            self.assertEqual((root / "go.sum").read_text(), new)
            with self.assertRaises(ValueError):
                prune_checksums(root, "v9.0.0")
            self.assertEqual((root / "go.sum").read_text(), new)


if __name__ == "__main__":
    unittest.main()
