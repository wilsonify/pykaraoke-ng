/**
 * Cucumber.js configuration – CI environment.
 *
 * Identical to default but with fail-fast enabled and structured reports.
 */
module.exports = {
  default: {
    paths: ['features/**/*.feature'],
    require: ['steps/**/*.ts', 'support/**/*.ts'],
    requireModule: ['ts-node/register'],
    format: [
      'progress-bar',
      'json:reports/e2e-results.json',
      'html:reports/e2e-report.html',
    ],
    formatOptions: { snippetInterface: 'async-await' },
    publishQuiet: true,
    failFast: true,
    retry: 0,
  },
};
