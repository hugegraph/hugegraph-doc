#!/usr/bin/env python3
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0.

"""Read exact site tool versions as data; keep platform-specific pins in sync."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(r"(?:0|[1-9][0-9]{0,3})\.(?:0|[1-9][0-9]{0,3})\.(?:0|[1-9][0-9]{0,3})")
GO_DIRECTIVE = re.compile(r"(?m)^go[ \t]+([^ \t\r\n]+)[ \t]*$")


def read_source(root, path, ref=None):
    if ref is not None:
        if not re.fullmatch(r"[0-9a-f]{40}", ref):
            raise ValueError("toolchain --ref must be an immutable commit SHA")
        # Only fixed data paths are read. Never import or run a candidate helper.
        content = subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=root, text=True)
    else:
        content = (Path(root) / path).read_text()
    if len(content) > 16384:
        raise ValueError(f"unexpectedly large toolchain input: {path}")
    return content


def load_toolchain(root=ROOT, *, ref=None):
    pins = json.loads(read_source(root, "toolchain.json", ref))
    if not isinstance(pins, dict) or set(pins) != {"hugo", "go"}:
        raise ValueError("toolchain.json must contain exactly the hugo and go version pins")
    for name, value in pins.items():
        if not isinstance(value, str) or not VERSION.fullmatch(value):
            raise ValueError(f"toolchain.json {name} must be an exact numeric X.Y.Z version")
    return pins


def derived_sources(root, pins):
    """Prepare all replacements before writing either derived file."""
    go_mod = read_source(root, "go.mod")
    if len(GO_DIRECTIVE.findall(go_mod)) != 1:
        raise ValueError("go.mod must contain exactly one go directive")
    expected = {"go.mod": GO_DIRECTIVE.sub(lambda _: f"go {pins['go']}", go_mod)}
    netlify = read_source(root, "netlify.toml")
    for name in ("hugo", "go"):
        pattern = re.compile(rf'(?m)^{name.upper()}_VERSION = "[^"\n]+"$')
        netlify, count = pattern.subn(f'{name.upper()}_VERSION = "{pins[name]}"', netlify)
        if count != 1:
            raise ValueError(f"netlify.toml must contain exactly one {name.upper()}_VERSION")
    expected["netlify.toml"] = netlify
    return expected


def check_toolchain_files(root=ROOT, *, ref=None):
    pins = load_toolchain(root, ref=ref)
    go_versions = GO_DIRECTIVE.findall(read_source(root, "go.mod", ref))
    if go_versions != [pins["go"]]:
        raise ValueError("go.mod differs from toolchain.json; run python3 scripts/site_toolchain.py --sync")
    if ref is None:
        for path, expected in derived_sources(root, pins).items():
            if read_source(root, path) != expected:
                raise ValueError(f"{path} differs from toolchain.json; run python3 scripts/site_toolchain.py --sync")
    return pins


def sync_toolchain_files(root=ROOT):
    pins = load_toolchain(root)
    for path, content in derived_sources(root, pins).items():
        (Path(root) / path).write_text(content)
    return pins


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="verify derived go.mod and Netlify pins")
    mode.add_argument("--sync", action="store_true", help="refresh derived pins after editing toolchain.json")
    parser.add_argument("--ref", help="read immutable candidate data with the trusted checkout's parser")
    parser.add_argument("--github-output", action="store_true", help="print validated workflow output lines")
    args = parser.parse_args()
    if args.ref and args.sync:
        parser.error("--ref cannot be combined with --sync")
    try:
        if args.sync:
            pins = sync_toolchain_files()
        elif args.check or args.ref:
            pins = check_toolchain_files(ref=args.ref)
        else:
            pins = load_toolchain()
        if args.github_output:
            for name in ("hugo", "go"):
                print(f"{name}_version={pins[name]}")
        else:
            print(json.dumps(pins, indent=2))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Site toolchain check failed: {error}") from None


if __name__ == "__main__":
    main()
