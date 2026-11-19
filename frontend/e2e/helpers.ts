import { expect, type Page } from "@playwright/test";

export type DemoRole = "Admin" | "Manager" | "Agent";

/** Sign in with one of the demo accounts from the login page's quick-fill buttons. */
export async function login(page: Page, role: DemoRole) {
  await page.goto("/login");
  // The login page is server-rendered: clicks before React hydrates do nothing, so retry
  // the quick-fill until it has filled the form. (Button text is lowercase, capitalized by CSS.)
  const email = page.getByLabel("Email address");
  await expect(async () => {
    await page.getByRole("button", { name: role.toLowerCase(), exact: true }).click();
    await expect(email).toHaveValue(/@demo\.talkwiseai\.com$/, { timeout: 1_000 });
  }).toPass({ timeout: 30_000 });
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  // Let the dashboard finish loading so the next navigation isn't interrupted
  await expect(page.getByText("Total Conversations")).toBeVisible();
}

/** A tiny WAV file; the mock speech-to-text provider ignores the audio. */
export function fakeRecording(name = "e2e-call.wav") {
  const header = Buffer.from("RIFF\x24\x00\x00\x00WAVEfmt ", "binary");
  return { name, mimeType: "audio/wav", buffer: Buffer.concat([header, Buffer.alloc(64)]) };
}

export function uniqueTitle(prefix: string) {
  return `${prefix} ${Date.now().toString(36)}`;
}
