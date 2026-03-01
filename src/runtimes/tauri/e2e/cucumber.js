/**
 * Cucumber.js configuration – local development.
 *
 * See: https://github.com/cucumber/cucumber-js/blob/main/docs/configuration.md
 */
module.exports = {
  default: {
    paths: ['features/**/*.feature'],
    require: ['steps/**/*.ts', 'support/**/*.ts'],
    requireModule: ['ts-node/register'],
    format: [
      'progress-bar',
      'html:reports/e2e-report.html',
    ],
    formatOptions: { snippetInterface: 'async-await' },
    publishQuiet: true,
    // Fail fast during local dev for quick feedback
    failFast: false,
    // Retry flaky scenarios once (set to 0 for strict mode)
    retry: 0,
  },
};
