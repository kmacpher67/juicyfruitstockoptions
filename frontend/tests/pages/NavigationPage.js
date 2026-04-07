import { expect } from '@playwright/test';

export class NavigationPage {
  constructor(page) {
    this.page = page;
    this.myPortfolioTab = page.getByRole('button', { name: 'My Portfolio' });
    this.tradeHistoryTab = page.getByRole('button', { name: 'Trade History' });
    this.ordersTab = page.getByRole('button', { name: 'Orders' });
    this.settingsButton = page.getByRole('button').nth(4); // Based on raw recording, index 4 is usually options/settings
    this.logoutButton = page.getByRole('button').nth(5);
    
    // Setting Modals
    this.saveSettingsButton = page.getByRole('button', { name: 'Save All' });
    this.closeModalButton = page.getByRole('button', { name: 'Close' });
  }

  async navigateToPortfolio() {
    await this.myPortfolioTab.click();
  }

  async navigateToTradeHistory() {
    await this.tradeHistoryTab.click();
  }

  async navigateToOrders() {
    await this.ordersTab.click();
  }

  async openSettings() {
    await this.settingsButton.click();
  }

  async logout() {
    await this.logoutButton.click();
  }
}
