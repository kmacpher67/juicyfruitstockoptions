import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

const reportName = 'AI_Stock_Live_Comparison_20260408_120000.xlsx';

const mockAnalysisRows = [
    {
        Ticker: 'AAPL',
        'Current Price': 189.42,
        'Call/Put Skew': 1.31,
        '1D % Change': '1.15%',
        'YoY Price %': '14.2%',
        TSMOM_60: 0.072,
        RSI_14: 53.2,
        EMA_20: 184.11,
        HMA_20: 185.42,
        MA_30: 182.91,
        MA_60: 179.55,
        MA_120: 170.22,
        MA_200: 166.81,
        'Annual Yield Put Prem': 5.44,
        '3-mo Call Yield': 2.21,
        '6-mo Call Yield': 4.38,
        '1-yr Call Yield': 8.13,
        'Div Yield': 0.43,
        'Last Update': '2026-04-08 12:00:00',
    },
];

const installDashboardMocks = async (page) => {
    await page.route('**/api/token', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ access_token: 'fake-jwt-token' }),
        });
    });

    await page.route('**/api/users/me', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ username: 'admin', role: 'admin' }),
        });
    });

    await page.route('**/api/settings', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ pageSize: 100, sortColumn: 'Ticker', sortOrder: 'asc' }),
        });
    });

    await page.route('**/api/jobs/latest/stock-live-comparison', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ status: 'completed' }),
        });
    });

    await page.route('**/api/portfolio/holdings', async (route) => {
        await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });

    await page.route('**/api/reports', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify([reportName]),
        });
    });

    await page.route(`**/api/reports/${reportName}/data`, async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockAnalysisRows),
        });
    });
};

test.describe('Stock Analysis Flow', () => {
    test('analysis grid renders key calculated columns and supports report download', async ({ page }) => {
        await installDashboardMocks(page);

        let downloadRequested = false;
        await page.route(`**/api/reports/${reportName}/download`, async (route) => {
            downloadRequested = true;
            await route.fulfill({
                status: 200,
                contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                body: 'xlsx-bytes',
            });
        });

        const loginPage = new LoginPage(page);
        await loginPage.goto();
        await loginPage.login('admin', 'admin123');

        await expect(page.getByRole('button', { name: 'Analysis' })).toBeVisible();
        await expect(page.locator('.ag-header-cell-text', { hasText: 'RSI 14' })).toBeVisible();
        await expect(page.locator('.ag-header-cell-text', { hasText: 'EMA 20' })).toBeVisible();
        await expect(page.locator('.ag-header-cell-text', { hasText: 'HMA 20' })).toBeVisible();
        await expect(page.locator('.ag-header-cell-text', { hasText: 'MA 30' })).toBeVisible();
        await expect(page.locator('.ag-header-cell-text', { hasText: 'MA 200' })).toBeVisible();
        await expect(page.locator('.ag-header-cell-text', { hasText: '1Y Put Prem %' })).toBeVisible();
        await expect(page.locator('.ag-header-cell-text', { hasText: '1Y Call %' })).toBeVisible();

        await page.getByRole('button', { name: 'Download' }).click();
        await expect.poll(() => downloadRequested).toBeTruthy();
    });
});
