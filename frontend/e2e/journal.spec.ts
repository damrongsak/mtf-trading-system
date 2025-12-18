import { test, expect } from '@playwright/test';

test.describe('Journal Entry Flow', () => {

  const timestamp = Date.now();
  const email = `testuser${timestamp}@example.com`;
  const password = 'Password123!';

  test.beforeEach(async ({ page, request }) => {
    // Monitor console logs
    page.on('console', msg => console.log(`BROWSER MSG: ${msg.text()}`));

    // 1. Register via API (Real Backend)
    const registerResponse = await request.post('http://localhost:8000/api/v1/auth/register', {
        data: {
            username: `testuser${timestamp}`,
            email: email,
            password: password,
            full_name: 'Test User'
        }
    });
    expect(registerResponse.ok()).toBeTruthy();

    // 2. Login via UI
    await page.goto('/login');
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');

    // 3. Wait for Login to succeed (Profile API called)
    await page.waitForResponse(response => 
        response.url().includes('/api/v1/auth/profile') && response.status() === 200
    );

    // 4. Manually navigate to avoid redirect issues
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/dashboard/, { timeout: 30000 });

    // Mock Journal Create (to avoid dependency on backend DB state)
    await page.route('**/api/v1/journal/entries', async route => {
         console.log('MOCK HIT: POST /api/v1/journal/entries');
         await route.fulfill({ json: { status: 'success', data: { id: 'journal-123' } } });
    });
  });

  test('should complete the journal wizard', async ({ page }) => {
    // 1. Navigate to New Journal Page
    await page.goto('/journal/new');

    // Step 1: Technical
    await expect(page.getByText('Market Data (Forex)')).toBeVisible({ timeout: 10000 });
    
    // Select symbol (default is XAU/USD, let's keep it or change)
    const symbolSelect = page.locator('select').first(); 
    // Or label based:
    // page.getByLabel('Pair') - waiting for hydration?
    
    // Click LONG
    await page.getByText('LONG').click();
    
    // Enter Price
    // Inputs: Entry Price, Stop Loss, Take Profit, Risk Amount ($), Exit Price, Realized P&L ($)
    // There are many inputs. Let's find by nearby text or order.
    // Label "Entry Price"
    // locator('label:has-text("Entry Price") + input')?
    
    // Or just fill all inputs roughly if they are unique types? No they are all number.
    // Use layout.
    // We can use placeholders if they exist, but code didn't show them.
    // We can use: page.locator('input[type="number"]').nth(0) -> Entry Price
    
    const inputs = page.locator('input[type="number"]');
    await inputs.nth(0).fill('2000'); // Entry
    await inputs.nth(1).fill('1990'); // SL
    await inputs.nth(2).fill('2020'); // TP
    await inputs.nth(3).fill('100');  // Risk
    await inputs.nth(4).fill('2010'); // Exit
    await inputs.nth(5).fill('500');  // PnL
    
    await page.getByText('Next: Game Level').click();

    // Step 2: Game Level
    await expect(page.getByText('How was your execution?')).toBeVisible();
    await page.getByText('A-Game').click();
    await page.getByText('Next: Mental Pattern').click();

    // Step 3: Mental Pattern
    // Just click Next (defaults are fine)
    await page.getByText('Next: Root Cause').click();

    // Step 4: Root Cause
    // Just click Submit (fields optional or fillable)
    await page.getByRole('button', { name: 'Submit Journal Entry' }).click();

    // Verify Redirect to /journal
    await expect(page).toHaveURL(/\/journal$/, { timeout: 30000 });
  });

});
