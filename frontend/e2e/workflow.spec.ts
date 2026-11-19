import { expect, test } from "@playwright/test";
import { fakeRecording, login, uniqueTitle } from "./helpers";

// docs/SPEC.md §61: login -> upload -> transcription -> analysis -> insights -> follow-up -> email -> CRM approval
test("upload a recording and work through its analysis", async ({ page }) => {
  await login(page, "Agent");
  const title = uniqueTitle("E2E discovery call");

  await page.goto("/conversations");
  await page.getByRole("button", { name: "Upload Recording" }).first().click();
  const dialog = page.getByRole("dialog");
  await dialog.locator("input[type=file]").setInputFiles(fakeRecording());
  await dialog.getByLabel("Conversation Title").fill(title);
  await dialog.getByRole("button", { name: "Upload & Analyze" }).click();
  await expect(page.getByText("File uploaded! Processing has started.")).toBeVisible();

  // Processing runs in the background; the detail page polls until it's done
  await page.getByRole("link", { name: new RegExp(title) }).click();
  await expect(page.getByText("Executive Summary")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("Lead Score")).toBeVisible();

  // Transcript: rename a speaker everywhere
  await page.getByRole("tab", { name: "Transcript" }).click();
  await page.getByRole("button", { name: "Rename speakers" }).click();
  const renameDialog = page.getByRole("dialog");
  await renameDialog.getByRole("textbox").last().fill("Dana (Customer)");
  await renameDialog.getByRole("button", { name: "Save names" }).click();
  await expect(page.getByText("Speakers renamed")).toBeVisible();
  await expect(page.getByText("Dana (Customer)").first()).toBeVisible();

  // Follow-up email draft (never sent automatically)
  await page.getByRole("button", { name: "Follow-up email" }).click();
  const emailDialog = page.getByRole("dialog");
  await emailDialog.getByRole("button", { name: "Generate draft" }).click();
  await expect(emailDialog.getByLabel("Subject")).not.toHaveValue("");
  await page.keyboard.press("Escape");

  // Approve the AI's CRM proposal
  await page.getByRole("tab", { name: "CRM Updates" }).click();
  await page.getByRole("button", { name: "Approve & update CRM" }).click();
  await expect(page.getByText("Applied", { exact: true })).toBeVisible();
});
