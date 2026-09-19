const base = require("@playwright/test");

const LOCAL_ARTIFACT_ORIGIN = "http://127.0.0.1:4173";
const PUBLISHED_ORIGINS = new Set([
  "https://hugegraph.apache.org",
  "https://hugegraph-oink.staged.apache.org"
]);

const test = base.test.extend({
  page: async ({ page }, use) => {
    await page.route("**/*", async (route) => {
      const requested = new URL(route.request().url());
      if (!PUBLISHED_ORIGINS.has(requested.origin)) {
        await route.continue();
        return;
      }
      const local = new URL(requested.pathname + requested.search, LOCAL_ARTIFACT_ORIGIN);
      try {
        const response = await route.fetch({ url: local.href });
        await route.fulfill({
          response,
          headers: {
            ...response.headers(),
            "access-control-allow-origin": "*"
          }
        });
      } catch (error) {
        if (String(error).includes("Test ended")) return;
        throw error;
      }
    });
    await use(page);
    await page.unrouteAll({ behavior: "ignoreErrors" });
  }
});

module.exports = { test, expect: base.expect };
