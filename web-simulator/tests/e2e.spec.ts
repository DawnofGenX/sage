import { test, expect } from '@playwright/test';

test('full user flow', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('text=Sage')).toBeVisible();
  await page.click('text=Extract Insights');
  await expect(page.locator('text=Schema Validation')).toBeVisible({ timeout: 10000 });
  await expect(page.locator('text=Proactive Insights')).toBeVisible();
});

test('demo mode', async ({ page }) => {
  await page.goto('/');
  await page.click('text=Demo Mode');
  await expect(page.locator('text=Demo Mode')).toBeVisible();
  await page.click('text=Start Demo');
  await expect(page.locator('text=Demo complete!')).toBeVisible({ timeout: 15000 });
});
