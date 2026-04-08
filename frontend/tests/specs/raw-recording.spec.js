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
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{ Ticker: 'AAPL', 'Current Price': 189.42, 'Call/Put Skew': 1.31 }]) });
        }
        if (url.endsWith('/api/portfolio/holdings')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
        }
        return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });
};

test('dashboard smoke: login, open ticker modal, open settings and logout', async ({ page }) => {
    await installMocks(page);

    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('admin', 'admin123');

    await expect(page.getByText('AAPL')).toBeVisible();
    await page.getByText('AAPL').first().click();
    await expect(page.getByRole('heading', { name: 'Trend & Technicals' })).toBeVisible();

    await page.getByRole('button').nth(4).click();
    await expect(page.getByRole('heading', { name: 'Dashboard Settings' })).toBeVisible();
    await page.getByRole('button', { name: 'Close' }).click();

    await page.getByRole('button').nth(5).click();
    await expect(page.getByRole('button', { name: 'Login' })).toBeVisible();
});
