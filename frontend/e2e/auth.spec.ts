import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {

    test('should allow user to navigate to login page', async ({ page }) => {
        await page.goto('/login');
        await expect(page.locator('h1')).toContainText(/Welcome Back/i);
        await expect(page.locator('input[name="email"]')).toBeVisible();
        await expect(page.locator('input[type="password"]')).toBeVisible();
    });

    // TODO: Add full login test once we have valid test credentials or mock
    test('should show error for invalid credentials', async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[name="email"]', 'invalid@example.com');
        await page.fill('input[type="password"]', 'invalidpassword');
        await page.click('button[type="submit"]');

        // Adjust selector based on actual error message UI
        await expect(page.getByText(/Invalid credentials/i)).toBeVisible();
    });

});
