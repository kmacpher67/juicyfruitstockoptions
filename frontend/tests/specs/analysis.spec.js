import { test, expect } from '@playwright/test';
import { StockAnalysisPage } from '../pages/StockAnalysisPage';
import { LoginPage } from '../pages/LoginPage';
import { NavigationPage } from '../pages/NavigationPage';

test.describe('Stock Analysis Flow', () => {
  test('User can run live analysis and interact with rows', async ({ page }) => {
    // Scaffold Network mocks
    await page.route('**/api/users/me', async (route) => route.fulfill({ status: 200, body: JSON.stringify({ username: 'admin' }) }));
    await page.route('**/api/analysis/stock-list', async (route) => route.fulfill({
      status: 200, body: JSON.stringify([{ Ticker: 'LACLithium Americas Corp.$4.', Price: 100, CallPutSkew: 1.5 }])
    }));
    await page.route('**/api/ticker/**', async (route) => route.fulfill({
      status: 200, body: JSON.stringify({ ticker: 'LAC', last_updated: '2026-04-06' })
    }));

    // Login
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('admin', 'admin123');

    const analysisPage = new StockAnalysisPage(page);
    // Modal interaction from script
    await analysisPage.openTickerModal('LACLithium Americas Corp');
    await analysisPage.verifyTrendTechnicalsVisible();

  });
});
