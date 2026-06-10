import { test, expect } from '@playwright/test';

test('public page renders the model-viewer element', async ({ page }) => {
  // The test environment should provide a published project with a known token.
  // PLAYWRIGHT_PUBLIC_TOKEN is set by the test fixture; the suite skips otherwise.
  const token = process.env.PLAYWRIGHT_PUBLIC_TOKEN;
  test.skip(!token, 'PLAYWRIGHT_PUBLIC_TOKEN not set — skipping public page test.');

  await page.goto(`/s/${token}`);
  const viewer = page.getByTestId('model-viewer');
  await expect(viewer).toBeVisible();
  await expect(viewer).toHaveAttribute('ar', /.*/); // present (true or false)
});

test('not-found page renders for an unknown token', async ({ page }) => {
  await page.goto('/s/00000000-0000-0000-0000-000000000000');
  await expect(page.getByRole('heading', { level: 1 })).toContainText(/couldn't find/i);
});
