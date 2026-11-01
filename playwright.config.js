import {defineConfig} from '@playwright/test';
export default defineConfig({
  testDir:'./tests/browser',
  timeout:120000,
  expect:{timeout:90000},
  workers:1,
  use:{baseURL:process.env.APP_URL || 'http://127.0.0.1:4173',trace:'retain-on-failure',actionTimeout:15000},
  webServer:process.env.APP_URL ? undefined : {
    command:'npm run preview',url:'http://127.0.0.1:4173',reuseExistingServer:!process.env.CI,
  },
});
