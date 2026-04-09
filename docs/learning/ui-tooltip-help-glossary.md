# UI Tooltip Help Glossary
Topic key: `ui-tooltip-help`

This glossary defines concise hover-help copy for common Juicy Fruit UI abbreviations and headers.

## Core Header Terms
- `DTE`: Days to expiration for the option contract.
- `NtM %`: Near-the-money distance between strike and underlying price.
- `P.BTC`: Pending buy-to-close contracts from open orders.
- `OI`: Open interest for the option contract.
- `Liq`: Liquidity grade for execution quality.
- `TSMOM 60`: 60-day time-series momentum score.
- `1D %`: One-day percent change.
- `% NAV`: Position weight as percent of total NAV.

## Common Action Controls
- `All`: Show all rows and clear focus filters.
- `Uncovered`: Show positions with uncovered shares.
- `Naked`: Show positions where short calls exceed share coverage.
- `Covered`: Show fully covered-call positions only.
- `Pending Cover`: Show rows with pending orders that improve coverage.
- `Pending BTC`: Show rows with pending buy-to-close intent.
- `Pending Roll`: Show rows with pending roll intent.
- `Expiring (<ND)`: Toggle options expiring within selected DTE threshold.
- `Near Money (<N%)`: Toggle options near-the-money by strike distance.
- `Export CSV`: Download current visible row set.

## Implementation Rule (Forward)
- Any new frontend button, link, or grid header should include concise help text (`title` or AG Grid `headerTooltip`) at implementation time.
- Any FR item that adds new UI controls or columns should include at least one test assertion covering tooltip/help presence.
