const base = require('./playwright.config');

module.exports = {
  ...base,
  testMatch: 'compatibility.spec.js',
  outputDir: 'test-results-compat',
  reporter: [['line'], ['html', { outputFolder: 'playwright-compat-report', open: 'never' }]],
  use: { ...base.use, launchOptions: {} },
  projects: [
    { name: 'firefox', use: { browserName: 'firefox' } },
    { name: 'webkit', use: { browserName: 'webkit', launchOptions: process.env.PLAYWRIGHT_WEBKIT_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_WEBKIT_EXECUTABLE_PATH } : {} } }
  ]
};
