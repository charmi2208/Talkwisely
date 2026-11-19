import { expect, test } from "@playwright/test";
import { login, uniqueTitle } from "./helpers";

test("agents don't see team management or the team filter", async ({ page }) => {
  await login(page, "Agent");
  const sidebar = page.locator("[data-sidebar=sidebar]").first();
  await expect(sidebar.getByRole("link", { name: "Dashboard" })).toBeVisible();
  await expect(sidebar.getByRole("link", { name: "Team" })).toHaveCount(0);
  await expect(page.getByRole("combobox", { name: "Team member" })).toHaveCount(0);
});

test("admins add a team member", async ({ page }) => {
  await login(page, "Admin");
  await page.goto("/team");
  await page.getByRole("button", { name: "Add member" }).click();

  const name = uniqueTitle("E2E Member");
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Full name").fill(name);
  await dialog.getByLabel("Email").fill(`${name.replace(/\s+/g, ".").toLowerCase()}@example.com`);
  await dialog.getByLabel("Temporary password").fill("Temporary123");
  await dialog.getByRole("button", { name: "Add member" }).click();

  await expect(page.getByText(name, { exact: true })).toBeVisible();
});
