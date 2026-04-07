import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { NavigationPage } from '../pages/NavigationPage';
import { StockAnalysisPage } from '../pages/StockAnalysisPage';

test.describe('Ticker Modal Validation', () => {
  test('Clicking a ticker opens the parallel intercept requests', async ({ page }) => {
    // 1. Scaffold global mocks
    await page.route('**/api/users/me', async (route) => route.fulfill({ status: 200, body: JSON.stringify({ username: 'admin' }) }));
    await page.route('**/api/analysis/stock-list', async (route) => route.fulfill({
      status: 200, body: JSON.stringify([{ Ticker: 'AAPL', Price: 150 }])
    }));

    // 2. Parallel intercept mocks simulating the 6 modal tabs
    await page.route('**/api/ticker/AAPL', async (route) => route.fulfill({ status: 200, body: JSON.stringify({ ticker: 'AAPL' }) }));
    await page.route('**/api/opportunity/AAPL', async (route) => route.fulfill({ status: 200, body: JSON.stringify({ score: 95 }) }));
    await page.route('**/api/portfolio/optimizer/AAPL', async (route) => route.fulfill({ status: 200, body: JSON.stringify({}) }));
    await page.route('**/api/analysis/rolls/AAPL', async (route) => route.fulfill({ status: 200, body: JSON.stringify({}) }));
    await page.route('**/api/analysis/signals/AAPL', async (route) => route.fulfill({ status: 200, body: JSON.stringify({}) }));

    // 3. Login
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('admin', 'admin123');

    // 4. Open Modal Actions
    const analysisPage = new StockAnalysisPage(page);
    await analysisPage.openTickerModal('AAPL');
    
    // Validate Ticker Detail Modal exists by looking for the Offline/Degraded badge or Tab content
    await analysisPage.verifyTrendTechnicalsVisible();
  });
});
