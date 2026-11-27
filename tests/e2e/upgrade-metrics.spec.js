// Licensed to the Apache Software Foundation (ASF) under one or more
// contributor license agreements. See the NOTICE file distributed with
// this work for additional information regarding copyright ownership.
// The ASF licenses this file to You under the Apache License, Version 2.0.

const { test, expect } = require('./artifact-test');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const output = process.env.UPGRADE_METRICS_DIR;
const samples = [];
const repeats = 5;
const cases = [
  ['en', 'server quickstart', '/docs/quickstart/hugegraph/hugegraph-server/', 'metadata'],
  ['cn', 'Server 快速上手', '/cn/docs/quickstart/hugegraph/hugegraph-server/', 'metadata'],
  ['en', 'auth.token_secret', '/docs/config/config-authentication/', 'body'],
  ['cn', '重启后继续有效', '/cn/docs/config/config-authentication/', 'body']
];
const indexes = Object.fromEntries(['en', 'cn'].map(locale => {
  const name = fs.readdirSync(process.env.SITE_ROOT)
    .find(file => file.startsWith(`offline-search-index.${locale}.`) && file.endsWith('.json'));
  return [locale, JSON.parse(fs.readFileSync(path.join(process.env.SITE_ROOT, name), 'utf8'))];
}));

// Measure in the page, including index download and the native input handler.
// MutationObserver + one animation frame ends at a visible, correct result;
// no Playwright polling interval is included in the measured duration.
async function measure(page, query, title, open) {
  return page.evaluate(({ query, title, open }) => new Promise((resolve, reject) => {
    const input = document.querySelector('.td-shell-search__input');
    const results = document.querySelector('#td-shell-search-results');
    const matches = () => Array.from(results.querySelector('.td-shell-search__group')?.querySelectorAll('[role="option"]') || [])
      .slice(0, 3).some(row => {
        const label = row.querySelector('.td-shell-search__item-title')?.textContent.trim();
        return label === title || label?.startsWith(title + ' › ');
      });
    const started = performance.now();
    const timeout = setTimeout(() => { observer.disconnect(); reject(new Error(`No correct result: ${query}; ${location.href}; ${results.textContent}`)); }, 25000);
    let finishing = false;
    const observer = new MutationObserver(() => {
      if (!finishing && matches()) {
        finishing = true;
        requestAnimationFrame(() => {
          clearTimeout(timeout);
          observer.disconnect();
          resolve(performance.now() - started);
        });
      }
    });
    observer.observe(results, { childList: true, subtree: true, characterData: true });
    if (open) document.querySelector('[data-td-shell-search-open]').click();
    input.value = query;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }), { query, title, open });
}

for (const [locale, query, expectedRef, kind] of cases) {
  for (let sample = 1; sample <= repeats; sample++) {
    test(`measure ${locale} ${kind} search sample ${sample}`, async ({ page, browser }) => {
      test.skip(!output, 'Set UPGRADE_METRICS_DIR to collect advisory measurements');
      const title = indexes[locale].find(record => record.ref === expectedRef)?.title;
      expect(title).toBeTruthy();
      await page.goto(locale === 'cn' ? '/cn/docs/' : '/docs/');
      await expect(page.locator('[data-td-shell-search-open]').first()).toBeVisible();
      const coldMs = await measure(page, query, title, true);
      await page.locator('.td-shell-search__input').fill('');
      await expect.poll(() => page.locator('#td-shell-search-results .td-shell-search__item-title').evaluateAll(
        (nodes, title) => nodes.some(node => node.textContent.trim() === title || node.textContent.trim().startsWith(title + ' › ')), title
      )).toBe(false);
      const warmMs = await measure(page, query, title, false);
      const requests = await page.evaluate(() => performance.getEntriesByType('resource')
        .filter(entry => /offline-search-(?:index|body)\./.test(entry.name))
        .map(entry => ({ url: new URL(entry.name).pathname, durationMs: entry.duration,
          transferBytes: entry.transferSize, decodedBytes: entry.decodedBodySize })));
      samples.push({ locale, query, kind, sample, coldMs, warmMs, requests,
        browser: browser.version(), userAgent: await page.evaluate(() => navigator.userAgent) });
    });
  }
}

test.afterAll(() => {
  if (!output) return;
  fs.mkdirSync(output, { recursive: true });
  const median = values => values.sort((a, b) => a - b)[Math.floor(values.length / 2)];
  const summaries = cases.map(([locale, query, , kind]) => {
    const selected = samples.filter(sample => sample.locale === locale && sample.query === query);
    return { locale, query, kind, count: selected.length,
      coldMedianMs: selected.length ? median(selected.map(value => value.coldMs)) : null,
      warmMedianMs: selected.length ? median(selected.map(value => value.warmMs)) : null };
  });
  fs.writeFileSync(path.join(output, 'metrics.json'), JSON.stringify({
    schemaVersion: 1, complete: samples.length === repeats * cases.length,
    environment: { platform: os.platform(), architecture: os.arch(), cpu: os.cpus()[0]?.model,
      node: process.version, workers: 1 },
    method: 'Five fresh browser contexts per query; cold includes opening the palette and index fetch; warm reuses the same in-memory engine. Local artifact server, no throttling. Resource transfer sizes may be unavailable for routed responses.',
    summaries, samples
  }, null, 2) + '\n');
});
