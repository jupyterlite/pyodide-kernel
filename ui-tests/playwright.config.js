const baseConfig = require('@jupyterlab/galata/lib/playwright-config');

module.exports = {
  ...baseConfig,
  reporter: [[process.env.CI ? 'dot' : 'list'], ['html']],
  use: {
    acceptDownloads: true,
    appPath: '',
    autoGoto: false,
    baseURL: 'http://localhost:8000',
    trace: 'on-first-retry',
    video: 'retain-on-failure'
  },
  projects: [
    {
      name: 'default',
      use: {
        baseURL: 'http://localhost:8000'
      }
    },
    {
      name: 'crossoriginisolated',
      use: {
        baseURL: 'http://localhost:8080'
      }
    }
  ],
  retries: 1,
  webServer: [
    {
      command: 'yarn start',
      port: 8000,
      timeout: 120 * 1000,
      reuseExistingServer: true
    },
    {
      command: 'yarn start:crossoriginisolated',
      port: 8080,
      timeout: 120 * 1000,
      reuseExistingServer: true
    }
  ]
};
