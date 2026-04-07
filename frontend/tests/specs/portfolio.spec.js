import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { NavigationPage } from '../pages/NavigationPage';
import { PortfolioPage } from '../pages/PortfolioPage';

test.describe('Portfolio Filters', () => {
  test('User can apply Coverage and Text filters', async ({ page }) => {
    // Scaffold Network mocks
    await page.route('**/api/users/me', async (route) => route.fulfill({ status: 200, body: JSON.stringify({ username: 'admin' }) }));
    await page.route('**/api/portfolio/stats', async (route) => route.fulfill({ status: 200, body: JSON.stringify({}) }));
    await page.route('**/api/portfolio/holdings', async (route) => route.fulfill({
      status: 200, body: JSON.stringify([{ ticker: 'AAPL', coverage_status: 'Uncovered' }, { ticker: 'MSFT', coverage_status: 'Covered' }])
    }));

    // Login & Goto
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('admin', 'admin123');

    const navPage = new NavigationPage(page);
    await navPage.navigateToPortfolio();

    // Portfolio filters
    const portfolioPage = new PortfolioPage(page);
    
    // Test the button filter
    await expect(portfolioPage.uncoveredFilterButton).toBeVisible();
    await portfolioPage.filterUncovered();

    // Verify CSV button exists
    await expect(portfolioPage.exportCsvButton).toBeVisible();
  });
});
