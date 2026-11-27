const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const workflow = fs.readFileSync(
  path.resolve(__dirname, "../../.github/workflows/hugo.yml"),
  "utf8"
);

test("only publish receives write permission", () => {
  const jobsStart = workflow.indexOf("\njobs:\n");
  const jobsSource = jobsStart < 0 ? "" : workflow.slice(jobsStart + 7);
  const jobs = [
    ...jobsSource.matchAll(
      /^  ([A-Za-z0-9_-]+):\s*\n((?:(?!^  [A-Za-z0-9_-]+:)[\s\S])*)/gm
    )
  ];
  const permissions = jobs.flatMap(([, job, body]) => {
    const inline = body.match(/^    permissions:\s*\{([^}]*)\}/m);
    const block = body.match(
      /^    permissions:\s*\n((?:^      [^\n]+\n?)+)/m
    );
    return [...(inline?.[1] ?? block?.[1] ?? "").matchAll(
      /\b([A-Za-z0-9_-]+):\s*(read|write)\b/g
    )].map(([, scope, level]) => ({ job, scope, level }));
  });
  assert.ok(jobs.length > 0);
  assert.ok(permissions.length > 0);
  assert.equal(
    permissions.filter((permission) => permission.level === "write").length,
    1
  );
  assert.deepEqual(
    permissions.filter((permission) => permission.level === "write"),
    [{ job: "publish", scope: "contents", level: "write" }]
  );
  assert.doesNotMatch(workflow, /write-all/);
});

test("build consumers check out the immutable prepared source SHA", () => {
  assert.match(workflow, /echo "source_sha=\$latest_sha"/);
  const refs = [...workflow.matchAll(/^\s+ref: \$\{\{([^}]+)\}\}/gm)].map((match) => match[1]);
  assert.equal(refs.length, 4);
  assert.doesNotMatch(refs[0], /candidate_branch/);
  assert.equal(refs.slice(1).filter((ref) => ref.includes("needs.prepare.outputs.source_sha")).length, 3);
  assert.doesNotMatch(workflow, /test \"\$GITHUB_REF\" = \"refs\/heads\/\$candidate\"/);
  assert.match(workflow, /test \"\$GITHUB_REF\" = \"refs\/heads\/master\"/);
});

test("trusted workflow bounds the candidate module graph without pinning its version", () => {
  const step = workflow.split("      - name: Verify pinned OINK module\n")[1]
    .split("      - name:")[0];
  assert.match(step, /go list -m -f '\{\{ \.Path \}\}'.*github\.com\/apache\/hugegraph-doc/);
  assert.match(step, /go list -m all \| wc -l.*-eq 2/);
  assert.match(step, /test -z .*\.Replace.*github\.com\/pgsty\/oink/);
  assert.doesNotMatch(step, /github\.com\/pgsty\/oink@v/);
  assert.match(step, /python3 scripts\/update_oink\.py --check-baseline/);
});

test("dependency artifacts keep stable names across selective reruns", () => {
  assert.match(workflow, /name: resolved-versions-\$\{\{ github\.run_id \}\}/);
  assert.match(workflow, /name: \$\{\{ needs\.prepare\.outputs\.artifact_prefix \}\}-versions-\$\{\{ matrix\.group\.id \}\}-\$\{\{ github\.run_id \}\}/);
  assert.match(workflow, /extra\+=\(--workers 2\)/);
  assert.match(workflow, /name: hugegraph-site-\$\{\{ needs\.prepare\.outputs\.artifact_prefix \}\}-\$\{\{ github\.run_id \}\}/);
  assert.doesNotMatch(workflow, /name: (?:resolved-versions|hugegraph-site-[^\n]+)-\$\{\{ github\.run_id \}\}-\$\{\{ github\.run_attempt \}\}/);
  assert.equal((workflow.match(/\n\s+overwrite: true/g) ?? []).length, 3);
});

function jobBody(name) {
  const body = workflow.match(new RegExp(`^  ${name}:\\n([\\s\\S]*?)(?=^  [a-z_]+:|$(?![\\s\\S]))`, "m"));
  assert.ok(body, `missing job ${name}`);
  return body[1];
}

test("all Hugo jobs share the validated standard or legacy Extended toolchain", () => {
  const action = fs.readFileSync(path.resolve(__dirname, "../../.github/actions/setup-site-tools/action.yml"), "utf8");
  assert.doesNotMatch(workflow, /HUGO_VERSION:|go-version-file:/);
  assert.match(workflow, /scripts\/site_toolchain\.py --ref "\$SOURCE_SHA" --github-output/);
  for (const job of ["prepare", "build", "aggregate"]) {
    const body = jobBody(job);
    const setupPath = job === "prepare" ? "./.github/actions/setup-site-tools" : "./resolved/setup-site-tools";
    assert.equal(body.split(`uses: ${setupPath}\n`).length - 1, 1);
    const source = job === "prepare" ? "steps.toolchain.outputs" : "needs.prepare.outputs";
    assert.ok(body.includes("hugo-version: ${{ " + source + ".hugo_version }}"));
    assert.ok(body.includes("hugo-extended: ${{ " + source + ".hugo_extended }}"));
    assert.ok(body.includes("go-version: ${{ " + source + ".go_version }}"));
    if (job !== "aggregate") assert.doesNotMatch(body, /actions\/setup-node/);
  }
  assert.match(action, /uses: peaceiris\/actions-hugo@[a-f0-9]{40}/);
  assert.match(action, /extended: \$\{\{ inputs\.hugo-extended \}\}/);
  assert.doesNotMatch(action, /dart-sass|npm|setup-node/);
  assert.doesNotMatch(workflow, /DART_SASS_VERSION|dart-sass-version|sass --version/);
});

test("manual candidate sources receive the trusted tool action via prepared artifacts", () => {
  const { spawnSync } = require("node:child_process");
  const os = require("node:os");
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "trusted-site-tools-"));
  try {
    const source = path.join(directory, ".github/actions/setup-site-tools");
    fs.mkdirSync(source, {recursive: true});
    const action = fs.readFileSync(path.resolve(__dirname, "../../.github/actions/setup-site-tools/action.yml"));
    fs.writeFileSync(path.join(source, "action.yml"), action);
    const helper = fs.readFileSync(path.resolve(__dirname, "../../scripts/hugo_build.py"));
    fs.mkdirSync(path.join(directory, "scripts"));
    fs.writeFileSync(path.join(directory, "scripts/hugo_build.py"), helper);
    const result = spawnSync("bash", ["-e", "-c", stepScript("Package trusted compiler setup for candidate builds")], {
      cwd: directory, env: {...process.env, BASH_ENV: ""}
    });
    assert.equal(result.status, 0, result.stderr.toString());
    assert.deepEqual(fs.readFileSync(path.join(directory, "setup-site-tools/action.yml")), action);
    assert.deepEqual(fs.readFileSync(path.join(directory, "setup-site-tools/hugo_build.py")), helper);
    assert.match(stepBody("Upload resolved version manifest"), /path: \|[\s\S]*^            setup-site-tools\//m);
    // Consumers download the trusted bundle after checking out the candidate;
    // setup therefore works even when its source has no local action directory.
    for (const job of ["build", "aggregate"]) {
      const body = jobBody(job);
      assert.ok(body.indexOf("path: resolved") < body.indexOf("uses: ./resolved/setup-site-tools"));
      assert.doesNotMatch(body, /uses: \.\/\.github\/actions\/setup-site-tools/);
    }
  } finally {
    fs.rmSync(directory, {recursive: true, force: true});
  }
});

test("AI fixtures retain strict warning checks from the trusted artifact", () => {
  for (const name of ["Build manifest-derived AI fixture", "Build AI-disabled rollback fixture"]) {
    const body = stepBody(name);
    assert.match(body, /python3 resolved\/setup-site-tools\/hugo_build\.py hugo/);
    assert.match(body, /--printPathWarnings --printI18nWarnings --logLevel info/);
  }
});

test("historical and Hugo resource caches follow the native Hugo toolchain", () => {
  for (const job of ["prepare", "build"]) {
    const body = jobBody(job);
    assert.match(body, /--hugo-version "\$\(hugo version\)"/);
    assert.match(body, /--go-version "\$\(go version\)"/);
    assert.doesNotMatch(body, /--sass-version/);
  }
  const resourceCache = jobBody("build").split("      - name: Cache Hugo resources\n")[1]
    .split("      - name:")[0];
  assert.equal((resourceCache.match(/needs\.prepare\.outputs\.hugo_version/g) ?? []).length, 2);
  assert.equal((resourceCache.match(/hashFiles\('resolved\/setup-site-tools\/action\.yml'\)/g) ?? []).length, 2);
});

test("partial historical hits schedule one group without downloading a bundle in prepare", () => {
  const prepare = jobBody("prepare");
  const lookup = stepBody("Look up a compatible historical bundle");
  assert.match(lookup, /restore-keys: \$\{\{ runner\.os \}\}-\$\{\{ steps\.history-plan\.outputs\.prefix \}\}/);
  assert.match(lookup, /lookup-only: true/);
  const groups = stepBody("Select bounded build groups");
  assert.match(groups, /history-lookup\.outputs\.cache-matched-key != ''/);
  assert.doesNotMatch(groups, /outputs\.cache-hit/);
  assert.match(prepare, /echo "prefix=\$\(jq -r \.cachePrefix cache-plan\.json\)"/);
  assert.match(jobBody("build"), /restore-keys: \$\{\{ runner\.os \}\}-\$\{\{ needs\.prepare\.outputs\.cache_prefix \}\}/);
  // Only an exact complete hit skips recording a new complete bundle.
  assert.match(prepare, /history_hit:.*history-lookup\.outputs\.cache-hit/);
  assert.match(jobBody("aggregate"), /needs\.prepare\.outputs\.history_hit != 'true'/);
});

test("superseded runs can cancel reporting and the required gate", () => {
  assert.match(workflow, /group:.*format\('pr-\{0\}', github.event.pull_request.number\)/);
  assert.match(workflow, /cancel-in-progress: true/);
  assert.doesNotMatch(workflow, /if: always\(\)/);
  assert.match(jobBody("aggregate"), /if: \$\{\{ !cancelled\(\) \}\}/);
});

test("assembly runs blocking browser tests on its local artifact", () => {
  const aggregate = jobBody("aggregate");
  assert.doesNotMatch(workflow, /^  e2e:/m);
  assert.match(aggregate, /SITE_ROOT: \$\{\{ runner.temp \}\}\/public-site/);
  assert.match(aggregate, /id: e2e/);
  assert.match(aggregate, /run: \|\n\s+npm run test:ci\n/);
  assert.match(aggregate, /playwright install --with-deps chromium firefox webkit/);
  assert.doesNotMatch(aggregate, /continue-on-error:/);
  assert.match(aggregate, /^    name: deploy$/m);
  assert.match(aggregate, /needs: \[prepare, build\]/);
  assert.doesNotMatch(workflow, /^  deploy:/m);
  assert.match(jobBody("publish"), /needs: \[prepare, aggregate\]/);
});

test("legacy browser contracts remain required and native CSS candidates require all browsers", () => {
  const { spawnSync } = require("node:child_process");
  const os = require("node:os");
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "candidate-browser-gates-"));
  const log = path.join(directory, "calls");
  try {
    const stub = '#!/bin/sh\nprintf "%s %s\\n" "${0##*/}" "$*" >> "$CALL_LOG"\n'
      + 'if [ "$*" = "$FAIL_COMMAND" ]; then exit 12; fi\n';
    for (const name of ["npm", "npx"]) fs.writeFileSync(path.join(directory, name), stub, {mode: 0o755});
    const run = (name, extended, fail = "") => {
      fs.writeFileSync(log, "");
      const result = spawnSync("bash", ["--noprofile", "--norc", "-p", "-e", "-c", stepScript(name)], {
        cwd: directory, encoding: "utf8",
        env: {...process.env, BASH_ENV: "", PATH: `${directory}:${process.env.PATH}`,
          HUGO_EXTENDED: extended, CALL_LOG: log, FAIL_COMMAND: fail}
      });
      return {...result, calls: fs.readFileSync(log, "utf8").trim().split("\n")};
    };
    for (const extended of ["true", "false"]) {
      const install = run("Install browser test workspace", extended);
      assert.equal(install.status, 0, install.stderr);
      assert.deepEqual(install.calls, ["npm ci", "npx playwright install --with-deps chromium"
        + (extended === "false" ? " firefox webkit" : "")]);
      const check = run("Run blocking browser contracts", extended);
      assert.equal(check.status, 0, check.stderr);
      assert.deepEqual(check.calls, extended === "true" ? ["npm run test:ci"]
        : ["npm run test:ci", "npm run test:browsers"]);
      const failed = run("Run blocking browser contracts", extended, "run test:ci");
      assert.notEqual(failed.status, 0);
      assert.deepEqual(failed.calls, ["npm run test:ci"]);
    }
    assert.notEqual(run("Run blocking browser contracts", "false", "run test:browsers").status, 0);
    for (const step of ["Install browser test workspace", "Run blocking browser contracts"]) {
      assert.notEqual(run(step, "").status, 0);
      assert.doesNotMatch(stepBody(step), /--if-present/);
      assert.match(stepBody(step), /HUGO_EXTENDED: \$\{\{ needs\.prepare\.outputs\.hugo_extended \}\}/);
    }
  } finally {
    fs.rmSync(directory, {recursive: true, force: true});
  }
});

test("required gate rejects failed, skipped and cancelled prerequisites", () => {
  const { spawnSync } = require("node:child_process");
  const aggregate = jobBody("aggregate");
  assert.match(aggregate, /if: \$\{\{ !cancelled\(\) \}\}/);
  assert.match(aggregate, /steps:\n      - name: Require all blocking predecessors to succeed/);
  assert.ok(aggregate.indexOf('test "$BUILD_RESULT" = success') < aggregate.indexOf("- uses: actions/checkout@"));
  assert.match(aggregate, /PREPARE_RESULT: \$\{\{ needs.prepare.result \}\}/);
  assert.match(aggregate, /BUILD_RESULT: \$\{\{ needs.build.result \}\}/);
  const gate = aggregate.split("        run: |\n")[1].split("      - uses:")[0]
    .split("\n").filter(line => line.startsWith("          "))
    .map(line => line.slice(10)).join("\n");
  const success = { PREPARE_RESULT: "success", BUILD_RESULT: "success" };
  const run = env => spawnSync("bash", ["--noprofile", "--norc", "-p", "-e", "-c", gate], {env: {...process.env, BASH_ENV: "", ...env}}).status;
  assert.equal(run(success), 0);
  for (const key of Object.keys(success)) {
    for (const result of ["failure", "skipped", "cancelled"]) {
      assert.notEqual(run({...success, [key]: result}), 0, `${key}=${result}`);
    }
  }
});


test("version work uses bounded groups and preserves full validation", () => {
  const build = jobBody("build");
  assert.match(build, /max-parallel: 3/);
  assert.match(build, /fromJSON\(needs.prepare.outputs.groups\)/);
  assert.match(build, /scripts\/build_versions\.py/);
  assert.match(build, /--workers 2/);
  assert.match(build, /name: Restore historical artifact bundle/);
  assert.match(build, /if: github.event_name != 'workflow_dispatch'/);
  assert.match(build, /scripts\/version_cache\.py plan/);
  assert.match(jobBody("aggregate"), /scripts\/versioning\.py aggregate/);
  assert.match(jobBody("publish"), /keep_files: false/);
});


test("warm reruns exclude stale cold-group artifacts and only complete caches are saved", () => {
  const prepare = jobBody("prepare");
  assert.match(prepare, /lookup-only: true/);
  assert.match(prepare, /echo 'pattern=0'/);
  assert.match(jobBody("aggregate"), /versions-\$\{\{ needs\.prepare\.outputs\.group_pattern \}\}/);
  assert.match(jobBody("aggregate"), /merge-multiple: true/);
  assert.match(jobBody("build"), /--expected-plan resolved\/cache-plan\.json/);
  assert.match(jobBody("aggregate"), /if: steps.history-record.outputs.complete == 'true'/);
});

test("cache recording failures cannot block an already validated site", () => {
  const { spawnSync } = require("node:child_process");
  const os = require("node:os");
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "history-record-"));
  const block = jobBody("aggregate").split("      - name: Record validated historical artifacts\n")[1]
    .split("      - name: Save complete historical bundle\n")[0];
  const script = block.split("        run: |\n")[1].split("\n")
    .filter(line => line.startsWith("          ")).map(line => line.slice(10)).join("\n");
  try {
    fs.mkdirSync(path.join(directory, "resolved"));
    fs.writeFileSync(path.join(directory, "resolved/cache-plan.json"), JSON.stringify({
      versions: [{id: "latest", archived: false}, {id: "1.7", archived: true}]
    }));
    for (const code of [0, 1]) {
      fs.writeFileSync(path.join(directory, "python3"), `#!/bin/sh\nexit ${code}\n`, {mode: 0o755});
      const output = path.join(directory, `outputs-${code}`);
      const result = spawnSync("bash", ["--noprofile", "--norc", "-p", "-e", "-c", script], {
        cwd: directory,
        env: {...process.env, BASH_ENV: "", PATH: `${directory}:${process.env.PATH}`, GITHUB_OUTPUT: output, RUNNER_TEMP: directory}
      });
      assert.equal(result.status, 0, result.stderr.toString());
      assert.equal(fs.readFileSync(output, "utf8"), `complete=${code === 0}\n`);
    }
  } finally {
    fs.rmSync(directory, {recursive: true, force: true});
  }
});


test("cache lookup and restore outages fall back without bypassing tests", () => {
  for (const [job, id] of [["prepare", "history-lookup"], ["build", "history-cache"]]) {
    assert.match(jobBody(job), new RegExp(`id: ${id}\\n        continue-on-error: true`));
    assert.equal((jobBody(job).match(/continue-on-error:/g) ?? []).length, 1);
  }
  assert.match(jobBody("prepare"), /history-lookup.outcome == 'success'/);
  assert.doesNotMatch(jobBody("aggregate"), /continue-on-error:/);
});


test("fingerprints use the same resolved Python patch on all version runners", () => {
  assert.match(jobBody("prepare"), /python_version: \$\{\{ steps.python.outputs.python-version \}\}/);
  for (const job of ["build", "aggregate"]) {
    assert.match(jobBody(job), /python-version: \$\{\{ needs.prepare.outputs.python_version \}\}/);
  }
});

function stepBody(name) {
  return workflow.split(`      - name: ${name}\n`)[1].split(/\n      - (?:name:|uses:)/)[0];
}

function stepScript(name) {
  return stepBody(name).split("        run: |\n")[1].split("\n")
    .filter(line => line.startsWith("          ")).map(line => line.slice(10)).join("\n");
}

test("manual candidates build and validate every immutable selected version using the original CLI", () => {
  const { spawnSync } = require("node:child_process");
  const os = require("node:os");
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "manual-build-"));
  const name = "Build and validate manual candidate versions";
  assert.match(stepBody(name), /if: github.event_name == 'workflow_dispatch'/);
  assert.match(stepBody("Build and validate selected versions"), /if: github.event_name != 'workflow_dispatch'/);
  assert.match(stepBody("Build and validate selected versions"), /--expected-plan resolved\/cache-plan.json/);
  assert.doesNotMatch(stepScript(name), /version_cache|build_versions|--workers/);
  const versions = [{id: "latest", sha: "a".repeat(40)}, {id: "1.7", sha: "b".repeat(40)}];
  try {
    fs.writeFileSync(path.join(directory, "selected-versions.json"), JSON.stringify({include: versions}));
    fs.writeFileSync(path.join(directory, "git"), '#!/bin/sh\nprintf "%s\\n" "$*" >> "$RUNNER_TEMP/git.log"\n[ "$1" != cat-file ]\n', {mode: 0o755});
    fs.writeFileSync(path.join(directory, "python3"), '#!/bin/sh\nprintf "%s\\t" "$HUGO_CACHEDIR" "$@" >> "$RUNNER_TEMP/python.log"\nprintf "\\n" >> "$RUNNER_TEMP/python.log"\n', {mode: 0o755});
    const env = {...process.env, BASH_ENV: "", PATH: `${directory}:${process.env.PATH}`,
      RUNNER_TEMP: directory, HUGO_CACHEDIR: `${directory}/hugo`,
      SITE_ORIGIN: "https://staging.example/", HISTORICAL_ORIGIN: "https://history.example/"};
    const run = () => spawnSync("bash", ["--noprofile", "--norc", "-p", "-e", "-c", stepScript(name)], {cwd: directory, env});
    const result = run();
    assert.equal(result.status, 0, result.stderr.toString());
    const calls = fs.readFileSync(path.join(directory, "python.log"), "utf8").trim().split("\n").map(line => line.trim().split("\t"));
    assert.deepEqual(calls, versions.flatMap(({id, sha}) => ["build", "validate"].map(operation => [
      `${directory}/hugo/${id}`, "scripts/versioning.py", operation, "--version", id, "--sha", sha,
      "--site-origin", env.SITE_ORIGIN, "--historical-origin", env.HISTORICAL_ORIGIN,
      operation === "build" ? "--output" : "--artifact", `${directory}/version-artifacts/${id}`
    ])));
    const gitCalls = fs.readFileSync(path.join(directory, "git.log"), "utf8");
    for (const {sha} of versions) assert.ok(gitCalls.includes(`fetch --no-tags origin ${sha}`));
    fs.writeFileSync(path.join(directory, "selected-versions.json"), JSON.stringify({include: [{id: "latest", sha: "HEAD"}]}));
    assert.notEqual(run().status, 0);
    assert.equal(fs.readFileSync(path.join(directory, "python.log"), "utf8").trim().split("\n").length, 4);
  } finally {
    fs.rmSync(directory, {recursive: true, force: true});
  }
});

test("manual candidate tools come from immutable data, never its executable helper", () => {
  const { spawnSync } = require("node:child_process");
  const os = require("node:os");
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "candidate-toolchain-plan-"));
  const env = {...process.env, BASH_ENV: "", GOTOOLCHAIN: "local",
    GIT_AUTHOR_NAME: "Workflow contract", GIT_AUTHOR_EMAIL: "workflow@localhost",
    GIT_COMMITTER_NAME: "Workflow contract", GIT_COMMITTER_EMAIL: "workflow@localhost"};
  const git = (...args) => {
    const result = spawnSync("git", args, {cwd: directory, env, encoding: "utf8"});
    assert.equal(result.status, 0, result.stderr);
    return result.stdout.trim();
  };
  const execute = (name, extra) => spawnSync("bash", ["--noprofile", "--norc", "-p", "-e", "-c", stepScript(name)], {
    cwd: directory, encoding: "utf8", env: {...env, ...extra}
  });
  try {
    git("init", "--quiet", "--initial-branch=master");
    git("remote", "add", "origin", directory);
    fs.mkdirSync(path.join(directory, "scripts"));
    const helper = fs.readFileSync(path.resolve(__dirname, "../../scripts/site_toolchain.py"));
    fs.writeFileSync(path.join(directory, "scripts/site_toolchain.py"), helper);
    fs.writeFileSync(path.join(directory, "versions.json"), JSON.stringify({
      versions: [{id: "latest", archived: false, ref: "master"}]
    }));
    fs.writeFileSync(path.join(directory, "toolchain.json"), JSON.stringify({hugo: "0.168.0", go: "1.27.3"}));
    fs.writeFileSync(path.join(directory, "go.mod"), "module github.com/apache/hugegraph-doc\n\ngo 1.27.3\n");
    git("add", ".");
    git("-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", "trusted workflow");
    git("switch", "--quiet", "-c", "candidate");
    fs.writeFileSync(path.join(directory, "toolchain.json"), JSON.stringify({hugo: "0.170.1", go: "1.27.4"}));
    fs.writeFileSync(path.join(directory, "go.mod"), "module github.com/apache/hugegraph-doc\n\ngo 1.27.4\n");
    fs.writeFileSync(path.join(directory, "scripts/site_toolchain.py"), "raise RuntimeError('candidate code executed')\n");
    git("add", ".");
    git("-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", "future candidate");
    const sha = git("rev-parse", "HEAD");
    git("switch", "--quiet", "master");
    const output = path.join(directory, "plan-output");
    const plan = execute("Resolve trusted event plan", {
      EVENT_NAME: "workflow_dispatch", EVENT_SHA: git("rev-parse", "HEAD"),
      OPERATION: "staging-next", SCOPE: "latest", CANDIDATE_BRANCH: "candidate",
      CONFIRMATION: "publish asf-staging-oink", GITHUB_REF: "refs/heads/master",
      PRODUCTION_ORIGIN: "https://production.example/", STAGING_ORIGIN: "https://staging.example/",
      GITHUB_OUTPUT: output, RUNNER_TEMP: directory
    });
    assert.equal(plan.status, 0, plan.stderr);
    assert.ok(fs.readFileSync(output, "utf8").includes(`source_sha=${sha}\n`));
    const toolOutput = path.join(directory, "tool-output");
    const tools = execute("Resolve candidate toolchain as data", {SOURCE_SHA: sha, GITHUB_OUTPUT: toolOutput});
    assert.equal(tools.status, 0, tools.stderr);
    assert.equal(fs.readFileSync(toolOutput, "utf8"), "hugo_version=0.170.1\ngo_version=1.27.4\nhugo_extended=false\n");
    assert.deepEqual(fs.readFileSync(path.join(directory, "scripts/site_toolchain.py")), helper);
  } finally {
    fs.rmSync(directory, {recursive: true, force: true});
  }
});

test("publication explicitly requires the blocking browser result", () => {
  const { spawnSync } = require("node:child_process");
  const os = require("node:os");
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "publication-browser-gate-"));
  assert.match(jobBody("aggregate"), /e2e_result: \$\{\{ steps\.e2e\.outcome \}\}/);
  assert.match(jobBody("publish"), /needs\.aggregate\.outputs\.e2e_result == 'success'/);
  try {
    fs.mkdirSync(path.join(directory, "public-site/build-metadata"), {recursive: true});
    fs.writeFileSync(path.join(directory, "public-site/build-metadata/versions.json"), "{}");
    for (const result of ["success", "failure", "skipped", "cancelled", ""]) {
      const child = spawnSync("bash", ["--noprofile", "--norc", "-p", "-e", "-c", stepScript("Verify fixed publication target")], {
        cwd: directory, env: {...process.env, BASH_ENV: "", E2E_RESULT: result, TARGET: "asf-staging-oink", PREFIX: "staging"}
      });
      assert.equal(child.status === 0, result === "success", result);
    }
  } finally {
    fs.rmSync(directory, {recursive: true, force: true});
  }
});

test("manual source tests stay read-only while publication consumes only the static artifact", () => {
  assert.match(stepBody("Validate source and version tooling"), /if: github.event_name != 'workflow_dispatch'/);
  assert.match(stepBody("Validate manual candidate source and version tooling"),
    /if: github.event_name == 'workflow_dispatch' && matrix.group.id == '0'/);
  for (const job of ["prepare", "build", "aggregate", "visual"]) {
    assert.match(jobBody(job), /permissions: \{ contents: read \}/);
    assert.doesNotMatch(jobBody(job), /secrets\./);
  }
  const publish = jobBody("publish");
  assert.match(publish, /uses: actions\/download-artifact@[a-f0-9]{40}/);
  assert.match(publish, /name: hugegraph-site-\$\{\{ needs\.prepare\.outputs\.artifact_prefix \}\}-\$\{\{ github\.run_id \}\}/);
  assert.doesNotMatch(publish, /actions\/checkout|npm|python3|uses: \.\//);
  assert.match(workflow, /^  push:\n    branches: \[master\]$/m);
  assert.match(stepScript("Resolve trusted event plan"),
    /elif \[\[ "\$EVENT_NAME" == push \]\]; then\n\s+test "\$GITHUB_REF" = refs\/heads\/master\n\s+publish_branch="asf-site"/);
});

test("manual aggregation retains staging flags without requiring new candidate CLI options", () => {
  const { spawnSync } = require("node:child_process");
  const os = require("node:os");
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "manual-aggregate-"));
  const script = stepScript("Assemble publishable site");
  assert.doesNotMatch(script, /version_cache|build_versions/);
  try {
    fs.writeFileSync(path.join(directory, "python3"), '#!/bin/sh\nprintf "%s\\n" "$@"\n', {mode: 0o755});
    fs.writeFileSync(path.join(directory, "lscpu"), '#!/bin/sh\nexit 0\n', {mode: 0o755});
    for (const event of ["workflow_dispatch", "pull_request"]) {
      const result = spawnSync("bash", ["--noprofile", "--norc", "-p", "-e", "-c", script], {cwd: directory,
        env: {...process.env, BASH_ENV: "", PATH: `${directory}:${process.env.PATH}`, EVENT_NAME: event,
          PREFIX: "staging", RUNNER_TEMP: directory, SITE_ORIGIN: "https://staging.example/",
          HISTORICAL_ORIGIN: "https://history.example/", SELECTION: "latest,1.7"}});
      assert.equal(result.status, 0, result.stderr.toString());
      const args = result.stdout.toString().trim().split("\n");
      assert.equal(args.includes("--workers"), event !== "workflow_dispatch");
      assert.deepEqual(args.slice(-4), ["--asf-profile", "oink", "--asf-whoami", "asf-staging-oink"]);
      assert.deepEqual(args.slice(0, 4), ["scripts/versioning.py", "aggregate", "--artifacts", "version-artifacts"]);
    }
  } finally {
    fs.rmSync(directory, {recursive: true, force: true});
  }
});
