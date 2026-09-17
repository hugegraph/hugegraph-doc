const { test, expect } = require("./artifact-test");
const AxeBuilder = require("@axe-core/playwright").default;

for (const route of [
  "/docs/",
  "/cn/docs/",
  "/community/",
  "/cn/community/",
  "/docs/download/download/",
  "/cn/docs/download/download/",
]) {
  test(`axe WCAG 2.2 AA guard ${route}`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto(route);
    await page.addStyleTag({
      content: "*,*::before,*::after{animation:none!important;transition:none!important}"
    });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(250);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
      .analyze();
    const knownOinkBaseline = new Set(["list", "target-size"]);
    const blocking = results.violations.filter(
      (item) =>
        ["critical", "serious"].includes(item.impact) &&
        !knownOinkBaseline.has(item.id)
    );
    expect(blocking).toEqual([]);
  });
}

for (const locale of ["en", "cn"]) {
  test(`download table scrolls with the keyboard on mobile ${locale}`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`${locale === "cn" ? "/cn" : ""}/docs/download/download/`);
    const region = page.locator(".hg-asf-release .td-asset-list__table-wrap").first();
    await region.scrollIntoViewIfNeeded();
    await region.focus();
    await expect(region).toBeFocused();
    await region.press("ArrowRight");
    await expect.poll(() => region.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0);
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}
