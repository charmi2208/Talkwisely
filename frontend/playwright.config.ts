import { defineConfig } from "@playwright/test";

/**
 * Browser end-to-end tests.
 *
 *   npm run test:e2e
 *
 * Starts a throwaway API (temporary SQLite database with demo data, mock AI, see
 * backend/scripts/e2e_server.py) on port 8020, builds the web app and serves it on port
 * 3020, then drives Google Chrome. Needs the backend virtualenv (backend/venv) and Chrome.
 * Stop any `next dev` for this project first: the build writes the same .next folder.
 */
const API_PORT = 8020;
const WEB_PORT = 3020;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1, // tests share one seeded database
  timeout: 90_000,
  expect: { timeout: 20_000 },
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    channel: "chrome",
    headless: true,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `../backend/venv/bin/python ../backend/scripts/e2e_server.py --port ${API_PORT} --web-origin http://localhost:${WEB_PORT}`,
      url: `http://127.0.0.1:${API_PORT}/health`,
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      // A production build: pages are precompiled, so tests don't wait on dev compiles
      command: `npm run build && npx next start -p ${WEB_PORT}`,
      url: `http://localhost:${WEB_PORT}/login`,
      timeout: 300_000,
      reuseExistingServer: false,
      env: { NEXT_PUBLIC_API_URL: `http://localhost:${API_PORT}/api/v1` },
    },
  ],
});
