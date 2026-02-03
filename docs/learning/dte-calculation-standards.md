# DTE Calculation Standards

In the world of options, DTE (Days to Expiration) is the countdown clock for your contract's time value. While it sounds simple, the "correct" value actually depends on whether you are looking at it like a mathematician or a trader.

## 1. How is DTE calculated?

In standard retail trading (like on **Interactive Brokers**, which we use), DTE is almost always calculated using **calendar days**, not just trading days.

* **The Calculation**: `Date of Expiration - Current Date`
* **The Logic**: Time decay (Theta) doesn't stop just because the market is closed. Options lose value over the weekend and holidays, so the models (like Black-Scholes) treat every day as a "decay day."

### Example Breakdown
(Scenario: Today is **Monday**, Expiration is **Friday**)

* **Monday to Tuesday:** 1 day
* **Tuesday to Wednesday:** 2 days
* **Wednesday to Thursday:** 3 days
* **Thursday to Friday:** 4 days

**Total DTE:** 4 Days

---

## 2. Start vs. End of Day: The "Flip"

The DTE value you see on the dashboard typically changes at a specific "cutoff" time. This is where it can get confusing:

* **Intraday (During Market Hours):** Most platforms show you the DTE as it stands at the start of the day. So, all day Monday, it will likely show **4 DTE**.
* **The "Flip" at Market Close:** Once the market closes on Monday (4:00 PM EST), many platforms "flip" the counter to **3 DTE**. They are signaling that the current trading session is over, and the "time risk" has shifted to the next day.
* **0DTE Status:** An option becomes **0DTE** at the start of its expiration day (Friday morning). At that point, the clock is measured in hours and minutes rather than days.

---

## 3. Trading Days vs. Calendar Days

While the displayed DTE is usually based on **Calendar Days**, Greeks (specifically **Theta**) are calculated behind the scenes using a more precise "Time to Maturity".

| Method | Days Included | Used For |
| --- | --- | --- |
| **Calendar Days** | 7 days a week | Standard DTE display and most Theta models (Yield calculations). |
| **Trading Days** | ~252 days a year | Some advanced volatility models that assume nothing happens on weekends. |

> **Pro Tip:** Since we focus on "returns" and "annualized yields", the most accurate way to calculate yield is by using the **calendar days** remaining. If we collect $1.00 on a 4 DTE trade, we are being compensated for 4 days of "risk," including the overnight decay.
