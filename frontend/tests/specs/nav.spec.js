import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

const reportName = 'AI_Stock_Live_Comparison_20260408_120000.xlsx';

const installApiMocks = async (page) => {
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
        if (url.includes('/api/portfolio/stats')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ current_nav: 100000, nav_1d: 0, nav_7d: 0, nav_30d: 0, nav_mtd: 0, nav_ytd: 0, nav_1y: 0 }) });
        }
        if (url.endsWith('/api/portfolio/live-status')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ connected: false, tws_enabled: false, connection_state: 'disabled', diagnosis: 'disabled' }) });
        }
        if (url.includes('/api/integrations/ibkr/sync')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'queued' }) });
        }
        if (url.includes('/api/trades/analysis')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ trades: [], metrics: {} }) });
        }
        if (url.includes('/api/trades/live-status')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ connection_state: 'disabled', diagnosis: 'disabled', today_live_trade_count: 0 }) });
        }
        if (url.includes('/api/trades/live')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
        }
        if (url.includes('/api/orders/open')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
        }
        if (url.includes('/api/orders/live-status')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ connection_state: 'disabled', last_order_update: null }) });
        }

        return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });
};

test.describe('Auth & Navigation Flow', () => {
    test('user can login and switch Analysis/Portfolio/Trades/Orders views', async ({ page }) => {
        await installApiMocks(page);

        const loginPage = new LoginPage(page);
        await loginPage.goto();
        await loginPage.login('admin', 'admin123');

        await expect(page.getByRole('button', { name: 'Analysis' })).toBeVisible();

        await page.getByRole('button', { name: 'My Portfolio' }).click();
        await expect(page.getByRole('button', { name: 'Uncovered' })).toBeVisible();

        await page.getByRole('button', { name: 'Trade History' }).click();
        await expect(page.getByRole('button', { name: 'YTD' })).toBeVisible();

        await page.getByRole('button', { name: 'Orders' }).click();
        await expect(page.getByText('Open Orders:')).toBeVisible();
    });
});
