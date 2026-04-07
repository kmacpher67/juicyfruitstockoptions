import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { NavigationPage } from '../pages/NavigationPage';

test.describe('Auth & Navigation Flow', () => {
  test('User can login and navigate through sidebar', async ({ page }) => {
    // 1. Mock the API endpoint that validates login tokens globally
    await page.route('**/api/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ username: 'admin', role: 'admin' }),
      });
    });

    const loginPage = new LoginPage(page);
    const navPage = new NavigationPage(page);

    // 2. Perform Login action
    await loginPage.goto();
    // Usually we would intercept the actual form post as well, here we assume dev mode local bypass or we mock the login route
    await page.route('**/api/auth/token', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ access_token: 'fake-jwt-token' }) });
    });
    await loginPage.login('admin', 'admin123');

    // 3. Verify side navigation interactions
    await navPage.navigateToPortfolio();
    await expect(page.getByRole('button', { name: 'Uncovered' })).toBeVisible();

    await navPage.navigateToTradeHistory();
    await expect(page.getByRole('button', { name: 'YTD' })).toBeVisible();

    await navPage.navigateToOrders();
    await expect(page.getByText('Open Orders:')).toBeVisible();

    // 4. Settings modal & logout
    await navPage.openSettings();
    await expect(page.getByRole('heading', { name: 'Dashboard Settings' })).toBeVisible();
    await navPage.closeModalButton.click();

    await navPage.logout();
    await expect(page.getByRole('button', { name: 'Login' })).toBeVisible();
  });
});
