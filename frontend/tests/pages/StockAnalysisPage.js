export class StockAnalysisPage {
  constructor(page) {
    this.page = page;
    this.trendAndTechnicalsHeading = page.getByRole('heading', { name: 'Trend & Technicals' });
    this.addTickerInput = page.getByRole('textbox', { name: 'Add Ticker...' });
  }

  async openTickerModal(ticker) {
    // In actual tests, use a data-testid or strong role lookup,
    // fallback based on the codegen clicking a cell
    await this.page.getByText(ticker).first().click();
  }

  async verifyTrendTechnicalsVisible() {
    await this.trendAndTechnicalsHeading.waitFor({ state: 'visible' });
  }
}
