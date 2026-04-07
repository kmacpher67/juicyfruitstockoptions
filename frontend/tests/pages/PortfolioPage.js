export class PortfolioPage {
  constructor(page) {
    this.page = page;
    // Main filter buttons
    this.uncoveredFilterButton = page.getByRole('button', { name: 'Uncovered' });
    this.exportCsvButton = page.getByRole('button', { name: 'Export CSV' });
    this.filterInput = page.getByRole('textbox', { name: 'Filter Value' });
  }

  async filterUncovered() {
    await this.uncoveredFilterButton.click();
  }

  async exportCsv() {
    await this.exportCsvButton.click();
  }
}
