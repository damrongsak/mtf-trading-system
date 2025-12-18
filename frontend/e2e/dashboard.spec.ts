import { test, expect } from '@playwright/test';

test.describe('Dashboard Flow', () => {


  // Helper to register and login
  test.beforeEach(async ({ page, request }) => {
    const timestamp = Date.now();
    const email = `testuser${timestamp}@example.com`;
    const password = 'Password123!';

    // Monitor console logs
    page.on('console', msg => console.log(`BROWSER MSG: ${msg.text()}`));


    // 1. Register via API (bypass UI registration which has redirect issues)
    const registerResponse = await request.post('http://localhost:8000/api/v1/auth/register', {
        data: {
            username: `testuser${timestamp}`,
            email: email,
            password: password,
            full_name: 'Test User' // Optional
        }
    });
    
    if (!registerResponse.ok()) {
        console.error('Registration failed:', await registerResponse.text());
    }
    expect(registerResponse.ok()).toBeTruthy();

    // 2. Go to Login page
    await page.goto('/login');
    
    // 3. Login via UI
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');

    // 4. Wait for Login to succeed (Profile API called)
    await page.waitForResponse(response => 
        response.url().includes('/api/v1/auth/profile') && response.status() === 200
    );

    // 5. Manually navigate to dashboard (bypass potential redirect race condition)
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/dashboard/, { timeout: 20000 });
  });



  test('should display critical dashboard elements', async ({ page }) => {
    // 1. Check Sidebar existence
    const sidebar = page.locator('aside'); // Assuming sidebar is an <aside>
    await expect(sidebar).toBeVisible();

    // 2. Check Header existence
    const header = page.locator('header');
    await expect(header).toBeVisible();

    // 3. Check for specific dashboard Cards
    // "Recent Signals"
    await expect(page.getByText('Recent Signals')).toBeVisible({ timeout: 30000 });
    
    // "Market Watch" - might be part of a card
    await expect(page.getByText('Market Watch')).toBeVisible({ timeout: 30000 });

    // 4. Verify AI Analyst Card (if present)
    // await expect(page.getByText('AI Market Analyst')).toBeVisible();
  });

  test('should load market watch data', async ({ page }) => {
    // Check for "Market Watch" header
    await expect(page.getByText('Market Watch')).toBeVisible({ timeout: 30000 });
    
    // Check for a default symbol like "EUR/USD" which is rendered in a div
    await expect(page.getByText('EUR/USD')).toBeVisible({ timeout: 30000 });
  });

});
