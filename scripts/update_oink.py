#!/usr/bin/env python3
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0.

"""Explicit, review-gated OINK upgrades using the existing site validators."""
import argparse
from contextlib import contextmanager
import gzip
import hashlib
import json
import os
import re
import shlex
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from hugo_build import is_unexpected_warning
from oink_module import MODULE, SITE_MODULE, VERSION, command, download_locked, locked_version

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "scripts/oink-overrides.json"
WATCH = ("assets/js/sidebar-state.js", "assets/js/sidebar-nav.js",
         "assets/js/docs-shell.js", "assets/js/search.js", "assets/js/search-engine.js",
         "assets/js/surface-coordinator.js", "assets/js/command-palette.js",
         "assets/js/appearance.js", "assets/js/dark-mode.js",
         "assets/js/compare-entry.js", "assets/js/compare-scroll.js",
         "assets/js/document-compare.js",
         "layouts/_partials/actions/context.html",
         "layouts/_partials/head.html",
         "layouts/_partials/compare/analytics.html",
         "layouts/_partials/compare/bootstrap.html",
         "layouts/_partials/compare/enabled.html",
         "layouts/_partials/compare/entry.html",
         "layouts/_partials/compare/page-key.html",
         "layouts/_partials/compare/scripts.html",
         "layouts/_partials/compare/targets.html",
         "layouts/_partials/shell/appearance-menu.html",
         "layouts/_partials/preset-config.html", "layouts/_partials/dark-mode-config.html",
         "layouts/_partials/css/bundle.html", "layouts/_partials/css/layers.html",
         "layouts/_partials/head-css.html",
         "layouts/_partials/scripts.html", "layouts/_partials/offline-search-index.html",
         "layouts/_partials/search/index-resources.html", "layouts/_partials/search/sections.html",
         "layouts/_partials/search/metadata.html", "layouts/_partials/content/field-anchor.html",
         "layouts/_partials/content/fields-list.html", "layouts/_markup/render-table.html",
         "layouts/_partials/content/table-render.html", "layouts/_partials/scripts/markmap.html",
         "layouts/_shortcodes/field.html", "layouts/_shortcodes/fields.html",
         "layouts/_partials/share/bar.html", "layouts/_partials/share/items.html",
         "assets/js/action-registry.js", "assets/js/page-actions.js", "assets/js/base.js")

# A small, repeatable set of real pages; functional coverage stays in test:ci.
VISUAL_SELECTION = ("en-upgrade-home-slate-light|en-fields-desktop-light|cn-fields-mobile-dark|"
                    "en-search-desktop-light|en-duo-desktop|cn-duo-mobile")
ACTIVE_WORK = None


def run(args, *, cwd=ROOT, env=None):
    print("+ " + " ".join(map(str, args)), flush=True)
    if ACTIVE_WORK is None:
        subprocess.run(list(map(str, args)), cwd=cwd, env=env, check=True)
        return
    report = json.loads((ACTIVE_WORK / "review.json").read_text())
    steps = report.setdefault("steps", [])
    number = len(steps) + 1
    log = ACTIVE_WORK / "logs" / f"{number:03d}.log"
    log.parent.mkdir(exist_ok=True)
    step = {"command": list(map(str, args)), "cwd": str(cwd), "log": str(log), "status": "running"}
    steps.append(step)
    write_report(ACTIVE_WORK, report)
    started = time.monotonic()
    try:
        with log.open("x") as output:
            process = subprocess.Popen(list(map(str, args)), cwd=cwd, env=env, text=True,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            for line in process.stdout:
                print(line, end="", flush=True)
                output.write(line)
                outcome = re.search(r"\[version ([^]]+)\] (cache validated|build validated)", line)
                if outcome:
                    step.setdefault("versions", {})[outcome[1]] = "cache" if outcome[2] == "cache validated" else "built"
            code = process.wait()
            process.stdout.close()
        if code:
            raise subprocess.CalledProcessError(code, args)
        step["status"] = "passed"
    except (OSError, subprocess.CalledProcessError) as error:
        step.update(status="failed", error=str(error))
        raise
    finally:
        step["seconds"] = round(time.monotonic() - started, 3)
        write_report(ACTIVE_WORK, report)


def write_report(work, report):
    """Keep failure/recovery evidence readable even if a later command fails."""
    # Source tests print simulated builder output too. Only the real builder's
    # invocation owns version outcomes; also clean reports made before this rule.
    for step in report.get("steps", []):
        if not any(Path(arg).name == "build_versions.py" for arg in step.get("command", [])[:2]):
            step.pop("versions", None)

    def replace(path, content):
        # A predictable .tmp name can be a pre-existing symlink. mkstemp's
        # exclusive creation and rename never follow a destination symlink.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=work,
                                         prefix=".oink-report-", delete=False) as output:
            temporary = Path(output.name)
            try:
                output.write(content)
                output.close()
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
    replace(work / "review.json", json.dumps(report, indent=2) + "\n")
    rows = ["# OINK upgrade report", "",
            f"- Release: `{report.get('from', 'pending')}` → `{report.get('to', 'pending')}`",
            f"- Status: **{report.get('status', 'prepared')}** ({report.get('mode', 'full')})",
            f"- Baseline source: `{report.get('baseHead', 'not captured')}`",
            "- ASF Staging and Production are separate release gates.", ""]
    performance = report.get("performance", {})
    if performance:
        rows.extend(["## Measured latest artifact", "", "| Metric | Before | After | Change |", "| --- | ---: | ---: | ---: |"])
        for label, metric in [("Build seconds", performance["buildSeconds"]), *performance["bytes"].items()]:
            rows.append(f"| {label} | {metric['before']} | {metric['after']} | {metric['change']} |")
        rows.extend(["", performance["conditions"], ""])
    for step in report.get("steps", []):
        if step.get("versions"):
            rows.extend(["Version build outcomes: " + ", ".join(f"{version}: {result}" for version, result in step["versions"].items()), ""])
    if report.get("error"):
        rows.extend(["## Remaining check", "", report["error"], ""])
    rows.extend(["See `review.json` for commands, logs, review impacts, recovery and resume instructions;",
                 "`before/` and `after/` for captures, and `before-browser/` and `after-browser/` for search samples.", ""])
    replace(work / "report.md", "\n".join(rows))


def update_report(work, **values):
    report = json.loads((work / "review.json").read_text())
    report.update(values)
    write_report(work, report)


def release_environment():
    """Release checks must use the published module, never a local preview."""
    env = dict(os.environ)
    env.pop("HUGO_MODULE_REPLACEMENTS", None)
    env.pop("HUGO_THEME", None)
    # The shared runner classifies warnings; never let a preview override it.
    env.pop("HUGO_PANICONWARNING", None)
    env.update(GOWORK="off", HUGO_MODULE_WORKSPACE="off")
    # Baseline/archived builds change cwd; resolve task-local tools first.
    for name in ("HUGO_BIN", "GO_BIN"):
        configured = env.get(name)
        executable = shutil.which(configured) if configured else None
        if executable:
            env[name] = str(Path(executable).resolve())
    return env


@contextmanager
def isolated_release():
    original = dict(os.environ)
    isolated = release_environment()
    try:
        os.environ.clear()
        os.environ.update(isolated)
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


@contextmanager
def graph_workspace(root):
    """Give Hugo disposable locks while preserving relative config/import paths.

    Hugo's graph command can fetch configured imports and rewrite both locks.
    A sibling workspace keeps parent-relative paths unchanged; link project
    inputs to their current files and copy the two writable root lock files.
    """
    root = Path(root).resolve()
    with tempfile.TemporaryDirectory(prefix="hugegraph-oink-graph-", dir=root.parent) as directory:
        workspace = Path(directory)
        for entry in root.iterdir():
            destination = workspace / entry.name
            if entry.name in {"go.mod", "go.sum"}:
                shutil.copy2(entry, destination)
            else:
                destination.symlink_to(entry, target_is_directory=entry.is_dir())
        yield workspace


def verify_hugo_graph(root, version):
    if (root / "_vendor").exists():
        raise ValueError("_vendor is unsupported by this module-only updater; move it aside and rerun, or refresh and review it separately")
    env = release_environment()
    with graph_workspace(root) as workspace:
        graph = subprocess.check_output([env.get("HUGO_BIN", "hugo"), "mod", "graph",
                                         "--config", "hugo.yaml", "--environment", "production", "--quiet"],
                                        cwd=workspace, env=env, text=True)
        graph = graph.replace(str(workspace), str(Path(root).resolve()))
    expected = MODULE + "@" + version
    edges = [line.split() for line in graph.splitlines() if line.strip()]
    root_imports = [tokens[1] for tokens in edges if len(tokens) == 2 and tokens[0] == SITE_MODULE]
    nodes = [token for tokens in edges for token in tokens
             if token == MODULE or token.startswith(MODULE + "@")]
    # Check every root import: an additional local theme can supply unpublished
    # templates even when the pinned OINK edge itself is correct. Dependencies
    # imported by OINK (and their transitive edges) remain valid.
    if (root_imports != [expected] or not nodes or any(node != expected for node in nodes)
            or any(len(tokens) != 2 for tokens in edges)):
        raise ValueError(f"expected Hugo root {SITE_MODULE} to import only published {MODULE}@{version}; actual graph: {graph}")
    return graph


def prior_release(root, version):
    with graph_workspace(root) as workspace:
        module = json.loads(command(["mod", "download", "-json", MODULE + "@" + version], workspace))
    if module.get("Error") or module.get("Version") != version or not module.get("Dir"):
        raise ValueError(f"cannot resolve reviewed previous release: {module}")
    return module


def snapshot(root, upstream):
    paths = set(WATCH)
    # Styles consume upstream selectors without a same-name template override.
    # Keep old paths when examining an old release, so removals remain visible.
    for folder, pattern in (("assets/css", "*.css"), ("assets/scss", "*.scss")):
        paths.update(str(p.relative_to(upstream)) for p in (upstream / folder).rglob(pattern))
    for folder in ("layouts", "assets", "i18n", "data"):
        def key(relative):
            name = relative.as_posix()
            # Locale filenames are case-insensitive; record the upstream spelling
            # rather than letting the host filesystem decide which file matches.
            return name.casefold().replace("_", "-") if folder == "i18n" else name

        upstream_paths = {key(p.relative_to(upstream)): p.relative_to(upstream).as_posix()
                          for p in (upstream / folder).rglob("*") if p.is_file()}
        paths.update(upstream_paths[key(p.relative_to(root))]
                     for p in (root / folder).rglob("*")
                     if p.is_file() and key(p.relative_to(root)) in upstream_paths)
    return {p: hashlib.sha256((upstream / p).read_bytes()).hexdigest()
            if (upstream / p).is_file() else None for p in sorted(paths)}


def changes(previous, current):
    return [p for p in sorted(previous.keys() | current.keys()) if previous.get(p) != current.get(p)]


def describe_changes(previous, current):
    return [f"{change_kind(previous, current, p)}: {p}"
            for p in changes(previous, current)]


def change_kind(previous, current, path):
    return "added" if previous.get(path) is None else "removed" if current.get(path) is None else "changed"


def prune_checksums(root, version):
    """Keep only target checksums after go get; do not use go mod tidy."""
    path = root / "go.sum"
    lines = [line for line in path.read_text().splitlines()
             if line.split()[:2] in [[MODULE, version], [MODULE, version + "/go.mod"]]]
    if len(lines) != 2 or len({line.split()[1] for line in lines}) != 2:
        raise ValueError(f"expected both target checksums before cleanup: {MODULE}@{version}")
    path.write_text("\n".join(lines) + "\n")


def resume_checksums(root, version, work):
    """Finish go get's go.mod-before-go.sum interruption window, then recheck."""
    try:
        prune_checksums(root, version)
        return
    except ValueError:
        entries = [line.split() for line in (root / "go.sum").read_text().splitlines() if line.strip()]
        pairs = [tuple(entry[:2]) for entry in entries]
        expected = {(MODULE, version), (MODULE, version + "/go.mod")}
        # Duplicate/malformed entries are not evidence of an interrupted write.
        if any(len(entry) != 3 for entry in entries) or len(set(pairs)) != len(pairs) or expected <= set(pairs):
            raise
    report = json.loads((work / "review.json").read_text())
    if (report.get("root") != str(root.resolve()) or report.get("to") != version
            or report.get("startedFromResume") is not False or locked_version(work / "before") == version):
        raise ValueError("missing target checksums require the original upgrade transaction; "
                         "resume its matching --work-dir or restore its original locks")
    # Go checks any existing digest against the published module. Do not discard
    # one that conflicts or manufacture a checksum from our own download.
    update_report(work, checksumRecovery={"status": "running", "target": version})
    command(["get", MODULE + "@" + version], root)
    prune_checksums(root, version)
    update_report(work, checksumRecovery={"status": "passed", "target": version})


def preflight(root, target, resume, work=None):
    if not VERSION.fullmatch(target):
        raise ValueError("use an explicit release such as v1.1.0; branches and latest are not accepted")
    if (root / "_vendor").exists():
        raise ValueError("_vendor is unsupported by this module-only updater; move it aside and rerun, or refresh and review it separately")
    if resume:
        if locked_version(root) != target:
            # A baseline failure can happen before go get. Resume that original
            # transaction only while both locks still equal its first backup.
            report_path = work.expanduser().resolve() / "review.json" if work else None
            report = json.loads(report_path.read_text()) if report_path and report_path.is_file() else {}
            pending = (report.get("to") == target and report.get("root") == str(root.resolve()) and
                       all((report_path.parent / "before" / name).is_file() and
                           (report_path.parent / "before" / name).read_bytes() == (root / name).read_bytes()
                           for name in ("go.mod", "go.sum")))
            if not pending:
                raise ValueError("--resume requires the pinned target or the unchanged original locks in its matching --work-dir")
    elif subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip():
        raise ValueError("working tree is not clean; commit/stash your work first, or use --resume for this pinned target")


def version_tuple(value):
    match = re.search(r"(?<![0-9])(\d+)\.(\d+)\.(\d+)(?![0-9])", value)
    if not match:
        raise ValueError(f"cannot identify tool version: {value!r}")
    return tuple(map(int, match.groups()))


def tool_output(argv):
    try:
        return subprocess.check_output(argv, env=release_environment(), text=True,
                                       stderr=subprocess.STDOUT).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "output", None) or str(error)
        raise ValueError(f"toolchain command {' '.join(argv)} failed: {detail}; "
                         "prepare the tools in scripts/oink-upgrade.md and rerun with the same --work-dir") from None


def tool_versions():
    return {"hugo": tool_output([release_environment().get("HUGO_BIN", "hugo"), "version"]),
            "go": tool_output([os.environ.get("GO_BIN", "go"), "version"]),
            "webp": tool_output(["cwebp", "-version"])}


def check_toolchain(root, target):
    """Resolve target metadata and compile in disposable roots before changing locks."""
    try:
        import tomllib
    except ImportError:
        raise ValueError("OINK upgrades require Python >= 3.11; use Python 3.13 as documented in scripts/oink-upgrade.md") from None
    module = prior_release(root, target)
    upstream = Path(module["Dir"])
    minimum = max((0, 169, 0), version_tuple(tomllib.loads((upstream / "theme.toml").read_text())["min_version"]))
    versions = tool_versions()
    if version_tuple(versions["hugo"]) < minimum:
        raise ValueError(f"Hugo >= {'.'.join(map(str, minimum))} is required for {target}; "
                         f"found {versions['hugo']}. Prepare tools using scripts/oink-upgrade.md; locks are unchanged")
    directive = re.search(r"(?m)^go\s+(\d+)\.(\d+)(?:\.(\d+))?\s*$", (upstream / "go.mod").read_text())
    if not directive:
        raise ValueError(f"cannot identify target Go requirement for {target}; locks are unchanged")
    minimum_go = tuple(int(part or 0) for part in directive.groups())
    if version_tuple(versions["go"]) < minimum_go:
        raise ValueError(f"Go >= {'.'.join(map(str, minimum_go))} is required for {target}; "
                         f"found {versions['go']}. Prepare tools using scripts/oink-upgrade.md; locks are unchanged")
    # Check the toolchain used by CI before go get can raise the Go directive.
    if (root / "toolchain.json").is_file():
        from site_toolchain import check_toolchain_files, load_toolchain
        pinned = load_toolchain(root)
        check_toolchain_files(root)
        for name, required in (("hugo", minimum), ("go", minimum_go)):
            if version_tuple(pinned[name]) < required:
                raise ValueError(f"toolchain.json {name}={pinned[name]} is below the target requirement "
                                 f"{'.'.join(map(str, required))}; update the manifest, run "
                                 "scripts/site_toolchain.py --sync and install those tools before upgrading; locks are unchanged")
            if version_tuple(versions[name]) != version_tuple(pinned[name]):
                raise ValueError(f"{name} must match toolchain.json ({pinned[name]}); found {versions[name]}; locks are unchanged")
    with tempfile.TemporaryDirectory(prefix="oink-css-check-") as directory:
        fixture = Path(directory)
        (fixture / "hugo.toml").write_text('baseURL = "https://example.test/"\ndisableKinds = ["taxonomy", "term", "RSS", "sitemap"]\n')
        (fixture / "layouts").mkdir()
        (fixture / "assets").mkdir()
        (fixture / "assets/probe.css").write_text(':root { --width: 12px; } .probe { width: var(--width); }\n')
        (fixture / "layouts/index.html").write_text(
            '{{ $css := slice (resources.Get "probe.css") | resources.Concat "probe.css" | minify }}{{ $css.Content }}')
        env = release_environment()
        try:
            result = subprocess.run([env.get("HUGO_BIN", "hugo"), "--source", str(fixture),
                                     "--environment", "production", "--logLevel", "info"],
                                    env=env, text=True, capture_output=True, timeout=30)
        except subprocess.TimeoutExpired:
            raise ValueError("Hugo native CSS smoke build timed out; locks are unchanged") from None
        rendered = fixture / "public/index.html"
        unexpected = any(is_unexpected_warning(line) for line in (result.stdout + result.stderr).splitlines())
        if result.returncode or unexpected or not rendered.is_file() or "var(--width)" not in rendered.read_text():
            raise ValueError(f"Hugo native CSS smoke build failed with {versions['hugo']}: "
                             f"{result.stdout}{result.stderr}. "
                             "Prepare tools using scripts/oink-upgrade.md; locks are unchanged")
    return versions


def prepare_work(root, baseline, requested, resume, target):
    from versioning import require_no_symlinked_output_components, require_output_outside_git_checkouts
    raw = requested.expanduser() if requested else Path(tempfile.mkdtemp(prefix="hugegraph-oink-"))
    try:
        require_no_symlinked_output_components(raw, "--work-dir", {Path(tempfile.gettempdir()), Path("/tmp")})
    except SystemExit as error:
        raise ValueError(str(error)) from None
    work = raw.resolve()
    source = root.resolve()
    if work == source or work in source.parents or source in work.parents:
        raise ValueError("--work-dir must be outside the repository and its ancestors; use a fresh --work-dir")
    # Reuse the release builder's complete checkout guard, including linked
    # worktrees and an enclosing repository. Check output siblings separately:
    # this transaction legitimately owns before-source/ as a detached checkout.
    try:
        require_no_symlinked_output_components(work / "before-source", "baseline checkout", {work})
        writable = ("before", "after", "logs", "before-browser", "after-browser", "review.json", "report.md",
                    "toolchain.json", "resolved.json", "build-plan.json", "validation-snapshot.json",
                    "before-metrics.json", "after-metrics.json", "ai.json", "ai-disabled.json",
                    "strict", "artifacts", "site", "ai", "ai-disabled", "baseline-site", "version-cache", "hugo-cache")
        for name in writable:
            destination = work / name
            require_no_symlinked_output_components(destination, "upgrade output", {work})
            if destination.is_dir() and any(path.is_symlink() for path in destination.rglob("*")):
                raise ValueError(f"upgrade output must not contain a symbolic link: {destination}")
        for name in ("strict", "artifacts", "site", "ai", "ai-disabled", "baseline-site"):
            require_output_outside_git_checkouts(work / name, "upgrade output")
    except SystemExit as error:
        raise ValueError(str(error)) from None
    work.mkdir(parents=True, exist_ok=True)
    backup = work / "before"
    names = ("go.mod", "go.sum", "oink-overrides.json")
    present = [(backup / name).exists() for name in names]
    report = work / "review.json"
    if any(present):
        if not all(present):
            raise ValueError(f"incomplete original lock backup in {backup}; use a fresh --work-dir")
        if not resume or not report.is_file():
            raise ValueError("existing upgrade backup requires --resume and its original review.json; use a fresh --work-dir")
    elif report.exists():
        raise ValueError("review.json has no original lock backup; use a fresh --work-dir")
    if report.is_file():
        previous = json.loads(report.read_text())
        if previous.get("to") != target or previous.get("root") != str(root.resolve()):
            raise ValueError("--work-dir belongs to another target or checkout; use its matching --resume command")
    if not any(present):
        reserved = ("toolchain.json", "resolved.json", "build-plan.json", "validation-snapshot.json",
                    "strict", "artifacts", "site", "ai", "ai-disabled", "ai.json", "ai-disabled.json",
                    "hugo-cache", "version-cache", "after", "before-source", "baseline-site", "before-metrics.json", "after-metrics.json", "report.md")
        conflicts = [name for name in reserved if (work / name).exists() or (work / name).is_symlink()]
        if conflicts:
            raise ValueError(f"--work-dir contains reserved runner outputs: {', '.join(conflicts)}; use a fresh --work-dir")
        backup.mkdir(exist_ok=True)
        for name, source in (("go.mod", root / "go.mod"), ("go.sum", root / "go.sum"),
                             ("oink-overrides.json", baseline)):
            with (backup / name).open("xb") as destination:
                destination.write(source.read_bytes())
        recovery = " && ".join("cp " + shlex.quote(str(backup / name)) + " " + shlex.quote(str(destination))
                               for name, destination in (("go.mod", root / "go.mod"), ("go.sum", root / "go.sum"),
                                                         ("oink-overrides.json", baseline)))
        write_report(work, {"root": str(root.resolve()), "to": target, "startedFromResume": resume,
                                      "recoveryCommand": recovery,
                                      "recoveryScope": "Restores locks and reviewed inventory from the first invocation in this directory; "
                                                       "startedFromResume means the backup may already pin the target. Local adaptations are retained.",
                                      "resumeCommand": " ".join(map(shlex.quote, [sys.executable, str(root / "scripts/update_oink.py"),
                                                                                target, "--resume", "--accept-reviewed", "--work-dir", str(work)]))})
    return work


def site_metrics(site, seconds):
    """Measure generated latest-site bytes; gzip is an estimate, not network traffic."""
    files = {}
    totals = {"css": 0, "js": 0, "search": 0}
    for path in sorted(site.rglob("*")):
        if not path.is_file():
            continue
        kind = "search" if "offline-search" in path.name and path.suffix == ".json" else path.suffix[1:]
        if kind not in totals:
            continue
        content = path.read_bytes()
        files[path.relative_to(site).as_posix()] = {"bytes": len(content), "gzipBytes": len(gzip.compress(content, mtime=0))}
        totals[kind] += len(content)
    return {"buildSeconds": round(seconds, 3), "htmlPages": sum(1 for _ in site.rglob("*.html")),
            "bytes": totals, "files": files, "scope": "latest artifact only; all emitted files, not first-page transfer; gzip estimated at level 9"}


def browser_setup(work, full=False):
    lock = hashlib.sha256((ROOT / "tests/e2e/package-lock.json").read_bytes()).hexdigest()
    report = json.loads((work / "review.json").read_text())
    ready = report.get("browserLock") == lock and (ROOT / "tests/e2e/node_modules/@playwright/test").is_dir()
    if not ready:
        run(["npm", "ci"], cwd=ROOT / "tests/e2e")
    installed = report.get("browsers", []) if ready else []
    executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    if executable:
        if not os.access(executable, os.X_OK):
            raise ValueError(f"PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH is not executable: {executable}")
    elif "chromium" not in installed:
        run(["npx", "playwright", "install", "chromium"], cwd=ROOT / "tests/e2e")
    required = ["chromium", "firefox", "webkit"] if full else ["chromium"]
    missing = [name for name in required if name != "chromium" and name not in installed]
    if missing:
        run(["npx", "playwright", "install", *missing], cwd=ROOT / "tests/e2e")
    update_report(work, browserLock=lock, browsers=sorted(set(installed + required)))


def capture_browser(work, site, label):
    browser_setup(work)
    env = dict(os.environ, SITE_ROOT=str(site), VISUAL_RESULTS_DIR=str(work / label),
               UPGRADE_METRICS_DIR=str(work / f"{label}-browser"))
    run(["npm", "run", "test:visual", "--", "--grep", VISUAL_SELECTION], cwd=ROOT / "tests/e2e", env=env)
    run(["npm", "run", "test:metrics"], cwd=ROOT / "tests/e2e", env=env)


def capture_before(work):
    """Freeze the original commit once; retries never relabel a modified site as before."""
    report = json.loads((work / "review.json").read_text())
    if report.get("before", {}).get("status") == "passed":
        return
    head = report.get("baseHead") or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    update_report(work, baseHead=head, before={"status": "running", "source": head})
    source = work / "before-source"
    if not source.exists():
        run(["git", "worktree", "add", "--detach", source, head])
    else:
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
        if actual != head or subprocess.check_output(["git", "status", "--porcelain"], cwd=source, text=True).strip():
            raise ValueError("baseline worktree differs from its original commit; retain evidence and use a fresh --work-dir")
    env = release_environment()
    if os.environ.get("BEFORE_HUGO_BIN"):
        env["HUGO_BIN"] = str(Path(shutil.which(os.environ["BEFORE_HUGO_BIN"]) or os.environ["BEFORE_HUGO_BIN"]).resolve())
    hugo_version = subprocess.check_output([env.get("HUGO_BIN", "hugo"), "version"], env=env, text=True).strip()
    with tempfile.TemporaryDirectory(prefix="before-hugo-", dir=work) as cache:
        env["HUGO_CACHEDIR"] = cache
        started = time.monotonic()
        run([source / "scripts/hugo.sh", "build", "--destination", work / "baseline-site"], cwd=source, env=env)
        elapsed = time.monotonic() - started
    metrics = site_metrics(work / "baseline-site", elapsed)
    metrics.update(source=head, hugo=hugo_version, go=tool_output([os.environ.get("GO_BIN", "go"), "version"]))
    (work / "before-metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    capture_browser(work, work / "baseline-site", "before")
    update_report(work, before={"status": "passed", "source": head, "hugo": hugo_version,
                                "metrics": str(work / "before-metrics.json"), "captures": str(work / "before")})


def performance_comparison(work):
    before = json.loads((work / "before-metrics.json").read_text())
    after = json.loads((work / "after-metrics.json").read_text())
    def delta(old, new):
        return {"before": old, "after": new, "change": round(new - old, 3),
                "percent": round(100 * (new - old) / old, 2) if old else None}
    return {"buildSeconds": delta(before["buildSeconds"], after["buildSeconds"]),
            "bytes": {name: delta(before["bytes"][name], after["bytes"][name]) for name in before["bytes"]},
            "beforeBrowser": str(work / "before-browser"), "afterBrowser": str(work / "after-browser"),
            "conditions": "Same runner; isolated Hugo caches. Toolchain versions recorded separately. One build sample per revision; not a benchmark claim."}


def validate(work, mode="full"):
    with isolated_release():
        # prepare_work has verified this external transaction directory. Let
        # existing output guards accept its fixed child paths without relaxing
        # versioning.py's protections or changing the caller's environment.
        os.environ["RUNNER_TEMP"] = str(work.resolve())
        _validate(work, mode)


def validation_snapshot(root, work):
    """Capture current publishable sources without touching the user's index."""
    def git(*args, env=None):
        return subprocess.check_output(["git", *args], cwd=root, env=env, text=True).strip()

    head = git("rev-parse", "HEAD")
    head_tree = git("rev-parse", "HEAD^{tree}")
    with tempfile.TemporaryDirectory(prefix="oink-validation-index-") as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / "index"))
        git("read-tree", head, env=env)
        git("add", "-A", "--", "content", "static", env=env)
        tree = git("write-tree", env=env)
        latest = head
        if tree != head_tree:
            identity = dict(env, GIT_AUTHOR_NAME="OINK validation", GIT_AUTHOR_EMAIL="validation@localhost",
                            GIT_COMMITTER_NAME="OINK validation", GIT_COMMITTER_EMAIL="validation@localhost")
            latest = git("commit-tree", tree, "-p", head, "-m", "chore: snapshot validation sources", "-m",
                         "- capture current content/static\n- preserve user index and refs\n- feed latest validation artifact", env=identity)
    report = {"baseHead": head, "latestSha": latest, "tree": tree,
              "source": "working tree content/static" if latest != head else "HEAD (content/static unchanged)",
              "scope": ["content", "static"],
              "exclusions": "Untracked ignored files and all changes outside content/static; normal Git ignore rules apply.",
              "references": "Validation-only unreferenced commit; real index, HEAD, branches and Git configuration are unchanged."}
    (work / "validation-snapshot.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Latest validation source: {latest} ({report['source']}); details: {work / 'validation-snapshot.json'}", flush=True)
    return latest


def _validate(work, mode="full"):
    py = sys.executable
    cli = [py, "scripts/versioning.py"]
    origin = "https://hugegraph.apache.org/"
    historical = "https://hugegraph.apache.org/"
    run(["bash", "dist/validate-links.sh"])
    run([py, "-m", "unittest", "discover", "-s", "scripts", "-p", "test_*.py"])
    with tempfile.TemporaryDirectory(prefix="after-hugo-", dir=work) as cache:
        started = time.monotonic()
        run(["scripts/hugo.sh", "build", "--destination", work / "strict"],
            env=dict(os.environ, HUGO_CACHEDIR=cache))
        elapsed = time.monotonic() - started
    metrics = site_metrics(work / "strict", elapsed)
    metrics.update(json.loads((work / "toolchain.json").read_text()))
    (work / "after-metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    if (work / "before-metrics.json").is_file():
        update_report(work, performance=performance_comparison(work))
    capture_browser(work, work / "strict", "after")
    if mode == "quick":
        run(["npx", "playwright", "test", "search-ranking.spec.js", "--reporter=line"],
            cwd=ROOT / "tests/e2e", env=dict(os.environ, SITE_ROOT=str(work / "strict"), EXPECTED_VERSIONS="latest"))
        return
    resolved = work / "resolved.json"
    latest = validation_snapshot(ROOT, work)
    run([*cli, "prepare", "--latest-sha", latest, "--output", resolved])
    versions = json.loads((work / "toolchain.json").read_text())
    plan = work / "build-plan.json"
    run([py, "scripts/version_cache.py", "plan", "--resolved-manifest", resolved,
         "--site-origin", origin, "--historical-origin", historical,
         "--hugo-version", versions["hugo"],
         "--go-version", versions["go"], "--webp-version", versions["webp"],
         "--cache-dir", work / "version-cache", "--output", plan])
    run([py, "scripts/build_versions.py", "--resolved-manifest", resolved, "--plan", plan,
         "--cache-dir", work / "version-cache", "--output", work / "artifacts",
         "--site-origin", origin, "--historical-origin", historical, "--workers", "2"],
        env=dict(os.environ, HUGO_CACHEDIR=str(work / "hugo-cache")))
    # aggregate validates every version artifact before merging it.
    run([*cli, "aggregate", "--resolved-manifest", resolved,
         "--artifacts", work / "artifacts", "--site-origin", origin,
         "--historical-origin", historical, "--output", work / "site"])
    run([py, "-m", "unittest", "scripts.test_download_data.DownloadDataTest.test_rendered_download_pages_have_verified_rows", "-v"],
        env=dict(os.environ, DOWNLOAD_PUBLIC_DIR=str(work / "site")))
    for name, port, config in [("ai", 4174, "ai-enabled"), ("ai-disabled", 4175, "ai-disabled")]:
        run([*cli, "config", "--version", "latest", "--site-origin", f"http://127.0.0.1:{port}/",
             "--historical-origin", historical, "--output", work / f"{name}.json"])
        run([py, "scripts/hugo_build.py", os.environ.get("HUGO_BIN", "hugo"), "--config",
             f"hugo.yaml,{work / f'{name}.json'},tests/e2e/{config}.yaml",
             "--destination", work / name, "--cleanDestinationDir", "--gc", "--minify",
             "--environment", "production", "--printPathWarnings", "--printI18nWarnings", "--logLevel", "info"])
    env = dict(os.environ, SITE_ROOT=str(work / "site"), AI_SITE_ROOT=str(work / "ai"),
               AI_DISABLED_SITE_ROOT=str(work / "ai-disabled"), VISUAL_RESULTS_DIR=str(work / "after"))
    browser_setup(work)
    run(["npm", "run", "test:ci"], cwd=ROOT / "tests/e2e", env=env)
    browser_setup(work, full=True)
    run(["npm", "run", "test:browsers"], cwd=ROOT / "tests/e2e", env=env)
    run(["npm", "run", "test:visual"], cwd=ROOT / "tests/e2e", env=env)


def main():
    global ACTIVE_WORK
    try:
        with isolated_release():
            _main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        if ACTIVE_WORK:
            report = json.loads((ACTIVE_WORK / "review.json").read_text())
            update_report(ACTIVE_WORK, status="review-required" if report.get("status") == "review-required" else "failed", error=str(error))
        raise
    finally:
        ACTIVE_WORK = None


def _main():
    global ACTIVE_WORK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?")
    parser.add_argument("--check-baseline", action="store_true", help="read-only CI check of reviewed upstream files")
    parser.add_argument("--resume", action="store_true", help="validate/adapt the already-pinned target in a dirty worktree")
    parser.add_argument("--accept-reviewed", action="store_true", help="acknowledge review of upstream changes; still run every selected validator")
    parser.add_argument("--work-dir", type=Path, help="artifact directory; reuse the same directory with --resume")
    parser.add_argument("--mode", choices=("quick", "full"), default="full",
                        help="quick checks latest for iteration; only full can advance the reviewed baseline")
    args = parser.parse_args()
    if args.check_baseline and (args.version or args.resume or args.accept_reviewed or args.work_dir or args.mode != "full"):
        parser.error("--check-baseline cannot be combined with upgrade options")
    if args.accept_reviewed and not args.version:
        parser.error("--accept-reviewed requires a target version")
    if args.check_baseline:
        module = download_locked(ROOT)
        verify_hugo_graph(ROOT, module["Version"])
        baseline = json.loads(BASELINE.read_text())
        changed = describe_changes(baseline["files"], snapshot(ROOT, Path(module["Dir"])))
        if baseline["version"] != module["Version"] or changed:
            detail = "; ".join(changed) or "no file changes"
            raise ValueError(f"OINK baseline differs (reviewed {baseline['version']}, pinned {module['Version']}): "
                             f"{detail}; local override additions/removals also require review; "
                             "follow scripts/oink-upgrade.md")
        print("Reviewed OINK upstream baseline matches")
        return
    if args.version is None:
        parser.error("version is required for upgrades")
    preflight(ROOT, args.version, args.resume, args.work_dir)
    previous = json.loads(BASELINE.read_text())
    versions = check_toolchain(ROOT, args.version)
    work = prepare_work(ROOT, BASELINE, args.work_dir, args.resume, args.version)
    ACTIVE_WORK = work
    update_report(work, status="capturing-before", mode=args.mode)
    (work / "toolchain.json").write_text(json.dumps(versions, indent=2) + "\n")
    print(f"Upgrade artifacts and review report: {work}", flush=True)
    capture_before(work)
    backup = work / "before"
    previous = json.loads((backup / "oink-overrides.json").read_text())
    if previous["version"] == args.version:
        prior_module = None
    else:
        prior_module = prior_release(ROOT, previous["version"])
    if locked_version(ROOT) != args.version:
        command(["get", MODULE + "@" + args.version], ROOT)
        prune_checksums(ROOT, args.version)
    elif args.resume:
        resume_checksums(ROOT, args.version, work)
    module = download_locked(ROOT)
    graph = verify_hugo_graph(ROOT, args.version)
    current = snapshot(ROOT, Path(module["Dir"]))
    changed = changes(previous["files"], current)
    report = {**json.loads((work / "review.json").read_text()), "from": previous["version"], "reviewRequired": changed,
              "priorModuleDir": (prior_module or module)["Dir"], "targetModuleDir": module["Dir"],
              "hugoModuleGraph": graph,
              "changes": [{"path": p, "kind": change_kind(previous["files"], current, p),
                           "reason": "upstream stylesheet dependency" if p.startswith(("assets/css/", "assets/scss/")) else
                                     "local override or watched upstream interface"} for p in changed],
              "reviewMeaning": "These are upstream review impacts, not a list of required local edits. Added/removed describe watched inventory coverage; stylesheet changes may need no adaptation.",
              "scope": "same-name layouts/assets/translations/data overrides, CSS, search/fields/navigation/appearance/compare public interfaces; not a full compatibility proof"}
    write_report(work, report)
    update_report(work, status="validating", error=None)
    validate(work, args.mode)
    update_report(work, performance=performance_comparison(work), validationCompleted=args.mode)
    if changed and not args.accept_reviewed:
        update_report(work, status="review-required")
        raise ValueError(f"{args.mode} checks passed; review required for {len(changed)} upstream files before acceptance. "
                         f"Inspect {work / 'report.md'} and review.json, then rerun with {report['resumeCommand']}")
    update_report(work, status=args.mode + "-passed",
                  acceptance="local full validation" if args.mode == "full" else "iteration only; full validation still required")
    if args.mode == "full":
        BASELINE.write_text(json.dumps({"version": args.version, "files": current}, indent=2) + "\n")
    print(f"{args.mode.title()} checks passed: {args.version}. "
          f"{'Reviewed baseline updated.' if args.mode == 'full' else 'Reviewed baseline unchanged; rerun --mode full for acceptance.'} "
          f"Evidence: {work}. ASF Staging and publication remain separate release gates.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"OINK check failed: {error}" if "--check-baseline" in sys.argv else
              f"OINK upgrade incomplete: {error}. Changes and artifacts are retained.", file=sys.stderr)
        sys.exit(1)
