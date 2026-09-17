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

// Execute the actual event planner: publication targets must not depend on
// arbitrary branch names or a fork running the reviewed staging workflow.
const os = require("node:os");
const { spawnSync } = require("node:child_process");
const plan = workflow.match(/      - name: Resolve trusted event plan[\s\S]*?        run: \|\n([\s\S]*?)(?=\n      - name:)/)[1]
  .split("\n").map((line) => line.replace(/^          /, "")).join("\n");

function runPlan(event, ref, repository) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "oink-event-plan-"));
  const output = path.join(directory, "outputs");
  try {
    const result = spawnSync("bash", ["-c", plan], {
      cwd: path.resolve(__dirname, "../.."),
      encoding: "utf8",
      env: { ...process.env, EVENT_NAME: event, EVENT_SHA: "a".repeat(40),
        GITHUB_REF: ref, GITHUB_REPOSITORY: repository, GITHUB_OUTPUT: output,
        PRODUCTION_ORIGIN: "https://hugegraph.apache.org/",
        STAGING_ORIGIN: "https://hugegraph-oink.staged.apache.org/" },
    });
    return { status: result.status, stderr: result.stderr,
      values: fs.existsSync(output) ? Object.fromEntries(fs.readFileSync(output, "utf8")
        .trim().split("\n").map((line) => line.split("="))) : {} };
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

test("reviewed Apache staging push targets only the complete staging site", () => {
  const result = runPlan("push", "refs/heads/staging/oink-reviewed", "apache/hugegraph-doc");
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.values.publish_branch, "asf-staging-oink");
  assert.equal(result.values.artifact_prefix, "staging");
  assert.equal(result.values.site_origin, "https://hugegraph-oink.staged.apache.org/");
  assert.equal(result.values.historical_origin, result.values.site_origin);
  assert.equal(result.values.selection, "latest,1.7,1.5,1.3,1.0");
  assert.equal(result.values.latest_sha, "a".repeat(40));
});

test("untrusted repository and unrelated branch cannot publish staging", () => {
  for (const [ref, repository] of [
    ["refs/heads/staging/oink-reviewed", "hugegraph/hugegraph-doc"],
    ["refs/heads/staging/oink-other", "apache/hugegraph-doc"],
    ["refs/tags/staging/oink-reviewed", "apache/hugegraph-doc"],
  ]) {
    const result = runPlan("push", ref, repository);
    assert.notEqual(result.status, 0);
    assert.equal(result.values.publish_branch, undefined);
  }
});

test("PRs remain unpublished and master retains the production target", () => {
  const pr = runPlan("pull_request", "refs/pull/472/merge", "apache/hugegraph-doc");
  assert.equal(pr.status, 0, pr.stderr);
  assert.equal(pr.values.publish_branch, "");
  const master = runPlan("push", "refs/heads/master", "apache/hugegraph-doc");
  assert.equal(master.status, 0, master.stderr);
  assert.equal(master.values.publish_branch, "asf-site");
  assert.equal(master.values.site_origin, "https://hugegraph.apache.org/");
});
