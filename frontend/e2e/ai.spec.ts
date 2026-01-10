import { test, expect } from '@playwright/test';

test.describe('AI Analyst Flow', () => {

    test('should allow user to chat with AI Analyst', async ({ page }) => {
        // 1. Login
        await page.goto('/login');
        await page.fill('input[name="email"]', 'trader1@example.com');
        await page.fill('input[type="password"]', 'password123'); // Default mock password
        await page.click('button[type="submit"]');

        // Wait for dashboard to load (look for AI Analyst Card)
        await expect(page.locator('text=AI Market Observer')).toBeVisible({ timeout: 15000 });

        // 2. Locate AI Widget
        const aiCard = page.locator('.col-span-1.md\\:col-span-2.lg\\:col-span-3'); // Basic robust card locator or use text
        await expect(aiCard).toBeVisible();

        const input = aiCard.locator('input[placeholder*="Ask about"]');
        const sendBtn = aiCard.locator('button:has(.lucide-send)');

        // 3. Send Message
        await input.fill('Analyze XAU/USD test');
        await sendBtn.click();

        // 4. Verify Loading State
        // Look for the bouncing dots
        const loader = aiCard.locator('.animate-bounce');
        // Wait for loader to appear (short timeout as it should be immediate)
        await expect(loader.first()).toBeVisible({ timeout: 5000 });

        // 5. Verify Response
        // Wait for loader to disappear (response received)
        await expect(loader.first()).toBeHidden({ timeout: 30000 }); // Give AI time to respond

        // Check for assistant response bubble
        const assistantMessage = aiCard.locator('.bg-gray-800').last();
        await expect(assistantMessage).toBeVisible();

        // Optional: Check content if predictable, but for now just check existence
        // await expect(assistantMessage).toContainText("XAU"); 
    });

});
