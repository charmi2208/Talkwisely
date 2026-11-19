import { expect, test } from "@playwright/test";
import { login } from "./helpers";

test("admin signs in, sees the live dashboard and stays signed in after a reload", async ({ page }) => {
  await login(page, "Admin");
  await expect(page.getByText("Total Conversations")).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Team member" })).toBeVisible();

  await page.reload();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("Total Conversations")).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("a wrong password shows an error on the login page", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email address").fill("admin@demo.talkwiseai.com");
  await page.getByRole("textbox", { name: "Password" }).fill("not-the-password");
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Invalid email or password" })).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
});

test("signed-out visitors are sent to the login page", async ({ page }) => {
  await page.goto("/analytics");
  await expect(page).toHaveURL(/\/login$/);
});
