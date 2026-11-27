const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const test = require('node:test');

const root = path.resolve(__dirname, '../..');
const assets = JSON.parse(fs.readFileSync(path.join(root, 'data/oink_css_assets.json')));

// Exercise the actual Hugo bundle adapter without a theme download or Sass.
function bundle(css, missingAsset = '') {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-css-assets-'));
  function write(file, contents) {
    const destination = path.join(directory, file);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, contents);
  }
  try {
    for (const file of ['layouts/_partials/css/bundle.html', 'data/oink_css_assets.json']) {
      write(file, fs.readFileSync(path.join(root, file)));
    }
    for (const asset of Object.keys(assets)) {
      if (asset === missingAsset) continue;
      const file = `static/img/bootstrap-controls/${asset}.svg`;
      write(file, fs.readFileSync(path.join(root, file)));
    }
    write('hugo.json', JSON.stringify({ baseURL: 'https://example.org/',
      disableKinds: ['taxonomy', 'term', 'RSS', 'sitemap', 'robotsTXT', '404'] }));
    write('layouts/_partials/css/layers.html', '{{ return (dict "main" (slice "fixture")) }}');
    write('assets/css/td/fixture.css', css);
    write('layouts/home.html', '{{ with partial "css/bundle.html" "main" }}{{ .Content | safeHTML }}{{ end }}');
    const result = spawnSync(process.env.HUGO_BIN || 'hugo', ['--source', directory], {
      encoding: 'utf8', timeout: 30_000,
    });
    return { ...result, css: result.status === 0
      ? fs.readFileSync(path.join(directory, 'public/index.html'), 'utf8') : '' };
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

test('reviewed Bootstrap SVGs stay local without changing other CSS', () => {
  const css = Object.entries(assets).map(([name, uri]) =>
    `.${name} { background-image: url("${uri}"); }`).join('\n');
  const result = bundle(css + '\n.keep { color: #123456; }');
  assert.equal(result.status, 0, result.stderr + result.stdout);
  assert.doesNotMatch(result.css, /data:/i);
  for (const name of Object.keys(assets)) {
    assert.ok(result.css.includes(`url("../img/bootstrap-controls/${name}.svg")`));
  }
  assert.ok(result.css.includes('.keep { color: #123456; }'));
});

test('unknown upstream data URIs require review instead of a relaxed CSP', () => {
  const result = bundle('.new { background: url("data:image/svg+xml,%3Csvg%3E%3C/svg%3E"); }');
  assert.notEqual(result.status, 0);
  assert.match(result.stderr + result.stdout, /unreviewed data URI/);
});

test('missing reviewed local SVG blocks the build', () => {
  const result = bundle(`.close { background: url("${assets.close}"); }`, 'close');
  assert.notEqual(result.status, 0);
  assert.match(result.stderr + result.stdout, /missing reviewed local SVG/);
});
