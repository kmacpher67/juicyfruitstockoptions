import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { StockAnalysisPage } from '../pages/StockAnalysisPage';

const reportName = 'AI_Stock_Live_Comparison_20260408_120000.xlsx';

const installMocks = async (page) => {
    await page.route('**/api/**', async (route) => {
        const url = route.request().url();
        const method = route.request().method();

        if (url.endsWith('/api/token') && method === 'POST') {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ access_token: 'fake-jwt-token' }) });
        }
        if (url.endsWith('/api/users/me')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ username: 'admin', role: 'admin' }) });
        }
        if (url.endsWith('/api/settings')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ pageSize: 100, sortColumn: 'Ticker', sortOrder: 'asc' }) });
        }
        if (url.includes('/api/jobs/latest/stock-live-comparison')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'completed' }) });
        }
        if (url.endsWith('/api/reports')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([reportName]) });
        }
        if (url.includes(`/api/reports/${reportName}/data`)) {
            return route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify([{ Ticker: 'AAPL', 'Current Price': 189.42, 'Call/Put Skew': 1.31, '1D % Change': '1.15%', 'YoY Price %': '14.2%' }]),
            });
        }
        if (url.endsWith('/api/portfolio/holdings')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
        }

        if (url.includes('/api/ticker/AAPL')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ found: true, stock: { Ticker: 'AAPL', 'Current Price': 189.42, '1D % Change': '1.15%', Last_Update: '2026-04-08 12:00:00' } }) });
        }
        if (url.includes('/api/opportunity/AAPL')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ score: 82, recommendations: [] }) });
        }
        if (url.includes('/api/portfolio/optimizer/AAPL')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
        }
        if (url.includes('/api/analysis/rolls/AAPL')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ rows: [] }) });
        }
        if (url.includes('/api/analysis/signals/AAPL')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ signals: [] }) });
        }

        return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });
};

test.describe('Ticker Modal Validation', () => {
    test('clicking a ticker opens the modal and analytics sections', async ({ page }) => {
        await installMocks(page);

        const loginPage = new LoginPage(page);
        await loginPage.goto();
        await loginPage.login('admin', 'admin123');

        const analysisPage = new StockAnalysisPage(page);
        await analysisPage.openTickerModal('AAPL');
        await analysisPage.verifyTrendTechnicalsVisible();
        await expect(page.getByRole('heading', { name: 'Core Pricing' })).toBeVisible();
    });
});
