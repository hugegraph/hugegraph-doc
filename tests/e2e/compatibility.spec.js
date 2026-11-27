const { test, expect } = require('./artifact-test');

for (const language of ['en', 'cn']) {
  for (const width of [1440, 390]) {
    test(`${language} native search, navigation and Duo View work at ${width}px`, async ({ page }) => {
      const prefix = language === 'cn' ? '/cn' : '';
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ reducedMotion: 'reduce' });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(`${prefix}/docs/config/config-option/`);
      if (width < 900) {
        await page.locator('[data-td-shell-drawer-open]').click();
        await expect(page.locator('html')).toHaveAttribute('data-td-shell-drawer', 'open');
        await page.keyboard.press('Escape');
      }
      await page.locator('[data-td-shell-search-open]').first().click();
      await page.locator('.td-shell-search__input').fill('restserver.connection_max_requests');
      const result = page.locator('#td-shell-search-results [role="option"]').filter({ hasText: 'restserver.connection_max_requests' }).first();
      await expect(result).toBeVisible();
      await result.click();
      const field = page.locator('[data-td-search-entry="restserver.connection_max_requests"]');
      await expect(page).toHaveURL(url => url.hash === '#field-restserver-connection_max_requests');
      await expect(field).toBeInViewport();
      await page.locator('[data-td-compare-open]').click();
      const dialog = page.locator('dialog[data-td-compare]');
      await expect(dialog).toBeVisible();
      const frames = dialog.locator('iframe[data-td-compare-frame]');
      await expect(frames).toHaveCount(2);
      for (const frame of await frames.all()) {
        const content = await (await frame.elementHandle()).contentFrame();
        await expect(content.locator('[data-td-search-entry="restserver.connection_max_requests"]')).toHaveCount(1);
      }
      if (width < 900) {
        await dialog.locator('.td-compare__tab').nth(1).click();
        await expect(dialog.locator('[data-td-compare-side="1"]')).toHaveAttribute('aria-hidden', 'false');
      }
      await page.keyboard.press('Escape');
      await expect(dialog).toBeHidden();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      expect(errors).toEqual([]);
    });
  }
}
