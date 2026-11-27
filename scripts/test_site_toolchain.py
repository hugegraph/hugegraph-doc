#!/usr/bin/env python3
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0.

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from site_toolchain import check_toolchain_files, load_toolchain, sync_toolchain_files


class SiteToolchainTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.pins = {"hugo": "0.170.1", "go": "1.27.4"}
        self.manifest = self.root / "toolchain.json"
        self.manifest.write_text(json.dumps(self.pins))
        (self.root / "go.mod").write_text("module example.test/site\n\ngo 1.27.3\n\nrequire example.test/theme v1.2.3\n")
        (self.root / "netlify.toml").write_text('[build.environment]\nGO_VERSION = "1.27.3"\nHUGO_VERSION = "0.168.0"\n')

    def test_sync_is_repeatable_and_preserves_nonversion_source(self):
        with self.assertRaisesRegex(ValueError, "go.mod differs"):
            check_toolchain_files(self.root)
        sync_toolchain_files(self.root)
        once = {p.name: p.read_text() for p in self.root.iterdir()}
        self.assertIn("go 1.27.4\n\nrequire example.test/theme v1.2.3", once["go.mod"])
        self.assertEqual(check_toolchain_files(self.root), self.pins)
        sync_toolchain_files(self.root)
        self.assertEqual({p.name: p.read_text() for p in self.root.iterdir()}, once)
        (self.root / "netlify.toml").write_text(once["netlify.toml"].replace('"0.170.1"', '"0.169.0"'))
        with self.assertRaisesRegex(ValueError, "netlify.toml differs"):
            check_toolchain_files(self.root)

    def test_rejects_ambiguous_or_executable_tool_requests(self):
        for value in ("latest", "0.170", "01.170.1", "v0.170.1", "0.170.1\nevil=value",
                      "$(touch sentinel)", "https://example.test/hugo", 170, None):
            with self.subTest(value=value):
                self.manifest.write_text(json.dumps({**self.pins, "hugo": value}))
                with self.assertRaises(ValueError):
                    load_toolchain(self.root)
        for pins in ({"hugo": "0.170.1"}, {**self.pins, "script": "build.sh"}, []):
            self.manifest.write_text(json.dumps(pins))
            with self.assertRaises(ValueError):
                load_toolchain(self.root)
        self.assertFalse((self.root / "sentinel").exists())

    def test_invalid_derived_file_does_not_partially_sync(self):
        before = (self.root / "go.mod").read_text()
        (self.root / "netlify.toml").write_text('GO_VERSION = "1.27.3"\n')
        with self.assertRaisesRegex(ValueError, "HUGO_VERSION"):
            sync_toolchain_files(self.root)
        self.assertEqual((self.root / "go.mod").read_text(), before)

    def test_candidate_is_read_as_immutable_data_without_running_its_helper(self):
        env = dict(os.environ, GIT_AUTHOR_NAME="Toolchain test", GIT_AUTHOR_EMAIL="test@localhost",
                   GIT_COMMITTER_NAME="Toolchain test", GIT_COMMITTER_EMAIL="test@localhost")
        def git(*args):
            return subprocess.check_output(["git", *args], cwd=self.root, env=env, text=True).strip()

        sync_toolchain_files(self.root)
        (self.root / "scripts").mkdir()
        (self.root / "scripts/site_toolchain.py").write_text("raise RuntimeError('must not execute')\n")
        git("init", "--quiet")
        git("add", ".")
        git("-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", "candidate")
        ref = git("rev-parse", "HEAD")
        self.manifest.write_text(json.dumps({"hugo": "0.171.0", "go": "1.28.0"}))
        self.assertEqual(check_toolchain_files(self.root, ref=ref), self.pins)
        for unsafe_ref in ("HEAD", "master", "-p", ref + ":toolchain.json"):
            with self.assertRaisesRegex(ValueError, "immutable commit"):
                check_toolchain_files(self.root, ref=unsafe_ref)

    def test_repository_pins_are_synchronized(self):
        check_toolchain_files(Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    unittest.main()
