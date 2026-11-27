const { test, expect } = require('./artifact-test');

const fields = [
  ['config/config-option', 'restserver.connection_max_requests'],
  ['quickstart/hugegraph/hugegraph-pd', 'pd.initial-store-count'],
  ['quickstart/hugegraph/hugegraph-hstore', 'pdserver.address']
];

for (const language of ['en', 'cn']) {
  const prefix = language === 'cn' ? '/cn' : '';
  test(`${language} PD fields distinguish distributed values from built-in defaults`, async ({ page }) => {
    await page.goto(`${prefix}/docs/quickstart/hugegraph/hugegraph-pd/`);
    const field = page.locator('[data-td-search-entry="partition.default-shard-count"]');
    const metadata = field.locator('.td-field__meta');
    await expect(metadata).toHaveCount(2);
    await expect(metadata.locator('.td-field__meta-label')).toHaveText(language === 'cn'
      ? ['主线目录值', '内置默认值'] : ['Master distribution value', 'Built-in default']);
    await expect(metadata.locator('.td-field__meta-value')).toHaveText(['1', '3']);
    await page.emulateMedia({ media: 'print' });
    await expect(metadata.nth(0)).toBeVisible();
    await expect(metadata.nth(1)).toBeVisible();
  });
  for (const [route, name] of fields) {
    test(`${language} native field search opens ${name} at its definition`, async ({ page, request }) => {
      await page.goto(`${prefix}/docs/${route}/`);
      const field = page.locator(`[data-td-search-entry="${name}"]`);
      await expect(field).toHaveCount(1);
      const anchor = await field.getAttribute('id');
      expect(anchor).toBeTruthy();
      const title = (await page.locator('h1').first().textContent()).trim();
      await page.locator('[data-td-shell-search-open]').first().click();
      await page.locator('.td-shell-search__input').fill(name);
      const results = page.locator('#td-shell-search-results .td-shell-search__group').first().getByRole('option');
      const match = results.filter({ has: page.locator('.td-shell-search__item-title', { hasText: `${title} › ${name}` }) });
      await expect(match).toHaveCount(1);
      await match.click();
      await expect(page).toHaveURL(url => url.pathname === `${prefix}/docs/${route}/` && decodeURIComponent(url.hash) === `#${anchor}`);
      await expect(field).toBeInViewport();
      await expect(field.locator('.td-field__description')).not.toBeEmpty();
      for (const width of [1440, 390, 320]) {
        await page.setViewportSize({ width, height: 900 });
        await field.scrollIntoViewIfNeeded();
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
        expect(await field.locator('.td-field__name').evaluate(node => parseFloat(getComputedStyle(node).fontSize))).toBeGreaterThanOrEqual(14);
      }
      const markdown = await request.get(`${prefix}/docs/${route}/index.md`);
      expect(markdown.ok()).toBe(true);
      expect(await markdown.text()).toContain(name);
      await page.emulateMedia({ media: 'print' });
      await expect(field).toBeVisible();
      await expect(field.locator('.td-field__description')).not.toBeEmpty();
    });
  }
}
