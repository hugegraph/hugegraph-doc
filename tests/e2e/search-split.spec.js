// Licensed to the Apache Software Foundation (ASF) under one or more
// contributor license agreements. See the NOTICE file distributed with
// this work for additional information regarding copyright ownership.
// The ASF licenses this file to You under the Apache License, Version 2.0.

const { test, expect } = require('@playwright/test');
const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const reference = '/docs/e2e-search-split/';
const title = 'Splitmetadataneedle catalogue';
const bodyQuery = 'splitbodyneedle';
const bodyRequest = /\/offline-search-body\.en\.[a-f0-9]+\.json$/;
let directory, origin, server;

// Use the existing artifact server on an OS-selected port. This fixture can
// run alongside the normal aggregate/AI servers and never changes SITE_ROOT.
async function serve(output) {
  const code = [
    'import sys',
    'from functools import partial',
    'from http.server import SimpleHTTPRequestHandler',
    'from serve import ArtifactServer',
    'server = ArtifactServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=sys.argv[1]))',
    'print(server.server_address[1], flush=True)',
    'server.serve_forever()'
  ].join('\n');
  server = spawn(process.env.PYTHON_BIN || 'python3', ['-u', '-c', code, output], { cwd: __dirname });
  server.stderr.resume();
  const port = await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.once('exit', code => reject(new Error(`Split fixture server exited: ${code}`)));
    server.stdout.once('data', value => resolve(Number(value.toString().trim())));
  });
  if (!Number.isInteger(port) || port <= 0) throw new Error('Split fixture server did not publish its port');
  server.stdout.resume();
  return `http://127.0.0.1:${port}`;
}

test.beforeAll(async ({ browser }, testInfo) => {
  test.setTimeout(120000);
  directory = fs.mkdtempSync(path.join(os.tmpdir(), 'hugegraph-search-split-'));
  const content = path.join(directory, 'content');
  const output = path.join(directory, 'public');
  fs.mkdirSync(path.join(content, 'docs'), { recursive: true });
  fs.mkdirSync(output);
  // Real Markdown goes through the unmodified native index template. Its
  // body alone exceeds the fixed 2 MiB split threshold, but stays below the
  // 8 MiB automatic-fetch budget. Neither threshold is configured or mocked.
  const paragraph = 'This temporary catalogue exercises native full text indexing and transport. ';
  const padding = paragraph.repeat(Math.ceil(2.25 * 1024 * 1024 / Buffer.byteLength(paragraph)));
  fs.writeFileSync(path.join(content, 'docs/e2e-search-split.md'),
    `---\ntitle: ${title}\ndescription: Temporary search regression catalogue.\n---\n\n${padding}\n${bodyQuery}\n`);
  origin = await serve(output);
  const config = path.join(directory, 'config.json');
  const mount = (source, language) => ({ source, target: 'content', sites: { matrix: { languages: [language] } } });
  fs.writeFileSync(config, JSON.stringify({
    baseURL: origin + '/', enableGitInfo: false,
    module: { mounts: [mount('content/en', 'en'), mount('content/cn', 'cn'), mount(content, 'en')] },
    params: { ai_search: { enabled: false } }
  }));
  const result = spawnSync(process.env.PYTHON_BIN || 'python3', [
    'scripts/hugo_build.py', process.env.HUGO_BIN || 'hugo', '--config', `hugo.yaml,${config}`,
    '--destination', output, '--environment', 'production', '--minify', '--printPathWarnings', '--printI18nWarnings'
  ], { cwd: root, encoding: 'utf8', timeout: 100000,
    env: { ...process.env, HUGO_CACHEDIR: path.join(directory, 'hugo-cache'), GOWORK: 'off', HUGO_MODULE_WORKSPACE: 'off' } });
  expect(result.status, result.error?.message || result.stdout + result.stderr).toBe(0);
  const published = prefix => {
    const names = fs.readdirSync(output).filter(name => name.startsWith(prefix) && name.endsWith('.json'));
    expect(names).toHaveLength(1);
    const file = path.join(output, names[0]);
    return { path: names[0], bytes: fs.statSync(file).size, entries: JSON.parse(fs.readFileSync(file, 'utf8')) };
  };
  const metadata = published('offline-search-index.en.');
  const body = published('offline-search-body.en.');
  expect(body.bytes).toBeGreaterThan(2 * 1024 * 1024);
  expect(body.bytes).toBeLessThanOrEqual(8 * 1024 * 1024);
  expect(metadata.entries.every(entry => !Object.hasOwn(entry, 'body'))).toBe(true);
  expect(metadata.entries.find(entry => entry.ref === reference)?.title).toBe(title);
  expect(JSON.stringify(metadata.entries)).not.toContain(bodyQuery);
  expect(body.entries.find(entry => entry.ref === reference)?.body).toContain(bodyQuery);
  const evidence = testInfo.outputPath('native-split-artifacts.json');
  fs.mkdirSync(path.dirname(evidence), { recursive: true });
  fs.writeFileSync(evidence, JSON.stringify({
    metadata: { path: metadata.path, bytes: metadata.bytes, records: metadata.entries.length },
    body: { path: body.path, bytes: body.bytes, records: body.entries.length },
    browser: browser.version(),
    fixture: 'Temporary Markdown mounted over the real HugeGraph site; native thresholds and runtime unchanged.'
  }, null, 2));
  await testInfo.attach('native-split-artifacts', { contentType: 'application/json', path: evidence });
});

test.afterAll(async () => {
  if (server && server.exitCode === null) {
    const stopped = new Promise(resolve => server.once('exit', resolve));
    server.kill();
    await stopped;
  }
  if (directory) fs.rmSync(directory, { recursive: true, force: true });
});

const result = page => page.getByRole('option').filter({ has: page.locator('.td-shell-search__item-title', { hasText: title }) });
const loadBody = page => page.getByRole('option', { name: /Search page text \(/ });

async function openSearch(page) {
  await page.addInitScript(() => localStorage.setItem('hg-language', 'en'));
  const eager = [];
  const watch = request => { if (/\/offline-search-(?:index|body)\.en\./.test(request.url())) eager.push(request.url()); };
  page.on('request', watch);
  await page.goto(origin + '/docs/');
  expect(eager, 'Native indexes must stay lazy until readers open search').toEqual([]);
  page.off('request', watch);
  await page.locator('[data-td-shell-search-open]').first().click();
  await page.locator('.td-shell-search__input').fill('splitmetadataneedle');
  await expect(result(page)).toHaveCount(1);
}

test('native split index answers metadata before the automatic body fetch finishes', async ({ page }) => {
  let requests = 0, release;
  const held = new Promise(resolve => { release = resolve; });
  await page.route(bodyRequest, async route => { requests++; await held; await route.continue(); });
  try {
    await openSearch(page);
    await expect.poll(() => requests).toBe(1);
    await page.locator('.td-shell-search__input').fill(bodyQuery);
    await expect(result(page)).toHaveCount(0);
    release();
    await expect(result(page)).toHaveCount(1);
    expect(requests).toBe(1);
    await result(page).click();
    await expect(page).toHaveURL(origin + reference);
  } finally { release(); }
});

test('Save-Data waits for explicit body search and fetches it only once', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(navigator, 'connection', { value: { saveData: true }, configurable: true }));
  let requests = 0;
  page.on('request', request => { if (bodyRequest.test(request.url())) requests++; });
  await openSearch(page);
  await expect(loadBody(page)).toBeVisible();
  expect(requests).toBe(0);
  await page.locator('.td-shell-search__input').fill(bodyQuery);
  await expect(result(page)).toHaveCount(0);
  await loadBody(page).click();
  await expect(result(page)).toHaveCount(1);
  await expect(loadBody(page)).toHaveCount(0);
  await page.locator('.td-shell-search__input').fill('splitmetadataneedle');
  await expect(result(page)).toHaveCount(1);
  expect(requests).toBe(1);
});

test('a failed body download preserves metadata results and offers native retry', async ({ page }) => {
  let requests = 0;
  await page.route(bodyRequest, route => ++requests === 1
    ? route.fulfill({ status: 503, contentType: 'text/plain', body: 'Temporary test outage' }) : route.continue());
  await openSearch(page);
  await expect(loadBody(page)).toBeVisible();
  expect(requests).toBe(1);
  await page.locator('.td-shell-search__input').fill(bodyQuery);
  await expect(result(page)).toHaveCount(0);
  await loadBody(page).click();
  await expect(result(page)).toHaveCount(1);
  await expect(loadBody(page)).toHaveCount(0);
  expect(requests).toBe(2);
});
