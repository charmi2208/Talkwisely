import { expect, test } from "@playwright/test";
import { login, uniqueTitle } from "./helpers";

test("analytics questions in the Copilot are answered from the data", async ({ page }) => {
  await login(page, "Manager");
  await page.goto("/ai-assistant");
  await page.getByPlaceholder(/Ask Copilot/).fill("What percentage of calls were positive?");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(/% of the \d+ conversations in the last 30 days were positive/)).toBeVisible();
  await expect(page.getByText(/computed from your data/)).toBeVisible();
  await expect(page.getByRole("cell", { name: "positive" }).first()).toBeVisible();
});

test("tasks can be added and completed", async ({ page }) => {
  await login(page, "Agent");
  await page.goto("/action-items");
  await page.getByRole("button", { name: "Add Task" }).click();
  const task = uniqueTitle("E2E follow-up task");
  await page.getByLabel("Task description").fill(task);
  await page.getByRole("button", { name: "Save" }).click();

  const row = page.locator("[data-slot=item]").filter({ hasText: task });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: "Complete task" }).click();
  await expect(row.getByRole("button", { name: "Reopen task" })).toBeVisible();
});

test("preferences are saved to the account", async ({ page }) => {
  await login(page, "Agent");
  await page.goto("/settings");
  const alerts = page.getByRole("switch").nth(1);
  await expect(alerts).toBeChecked();
  await alerts.click();
  await expect(page.getByText("Preference saved")).toBeVisible();

  await page.reload();
  await expect(page.getByRole("switch").nth(1)).not.toBeChecked();
  await page.getByRole("switch").nth(1).click(); // restore the default
  await expect(page.getByRole("switch").nth(1)).toBeChecked();
});

test("managers import meeting recordings", async ({ page }) => {
  await login(page, "Manager");
  await page.goto("/meetings");
  await page.getByRole("button", { name: "Import recordings" }).click();
  await expect(page.getByText(/Imported 2 new recordings|No new recordings to import/)).toBeVisible();

  await expect(async () => {
    await page.reload();
    await expect(page.getByText("Zoom meeting: Quarterly business review with Northwind")).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 60_000 });
});
