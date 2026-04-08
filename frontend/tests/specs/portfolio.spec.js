import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

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
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{ Ticker: 'AAPL' }]) });
        }

        if (url.includes('/api/portfolio/stats')) {
            return route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    current_nav: 100000,
                    nav_1d: 0,
                    nav_7d: 0,
                    nav_30d: 0,
                    nav_mtd: 0,
                    nav_ytd: 0,
                    nav_1y: 0,
                }),
            });
        }
        if (url.endsWith('/api/portfolio/live-status')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ connected: false, tws_enabled: false, connection_state: 'disabled', diagnosis: 'disabled' }) });
        }
        if (url.endsWith('/api/portfolio/holdings')) {
            return route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify([
                    { account_id: 'U1', symbol: 'AAPL', coverage_status: 'Uncovered', quantity: 100, market_price: 189.4, market_value: 18940, cost_basis: 170, unrealized_pnl: 1940, true_yield: 2.2, percent_of_nav: 18.9, security_type: 'STK' },
                    { account_id: 'U1', symbol: 'MSFT', coverage_status: 'Covered', quantity: 10, market_price: 412.2, market_value: 4122, cost_basis: 370, unrealized_pnl: 422, true_yield: 1.8, percent_of_nav: 4.1, security_type: 'STK' },
                ]),
            });
        }
        if (url.includes('/api/integrations/ibkr/sync')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'queued' }) });
        }

        return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });
};

test.describe('Portfolio Filters', () => {
    test('user can open portfolio view and apply uncovered filter', async ({ page }) => {
        await installMocks(page);

        const loginPage = new LoginPage(page);
        await loginPage.goto();
        await loginPage.login('admin', 'admin123');

        await page.getByRole('button', { name: 'My Portfolio' }).click();
        await expect(page.getByRole('button', { name: 'Uncovered' })).toBeVisible();

        await page.getByRole('button', { name: 'Uncovered' }).click();
        await expect(page.getByText('Rows:')).toBeVisible();
        await expect(page.getByRole('button', { name: 'Export CSV' })).toBeVisible();
    });
});
