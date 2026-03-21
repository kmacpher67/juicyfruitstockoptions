To visualize the transition from the current "cramped widget" layout to a high-density, strategy-centric interface, I have outlined a wireframe layout below. This design prioritizes your need for **Annualized Yield** and **Comparison** between different timeframes (Weekly vs. Monthly).

### Wireframe: Strategy-Centric Opportunity Drawer

This layout assumes a "Drawer" model where clicking a ticker in your `PortfolioGrid` slides out a detailed analysis pane from the right, keeping your main list visible for context.

```text
+-----------------------------------------------------------------------+
| TICKER: [ D ] | Dominion Energy | P/E: 18 | C/P Skew: 4.12 | DIV: 4.0% |
+-----------------------------------------------------------------------+
| [ ACTIVE STRATEGY COMPARISON ]                                        |
+-----------------------------------------------------------------------+
| MONTHLY (BORING/STABLE)          | WEEKLY (VELOCITY/ACTIVE)           |
+----------------------------------+------------------------------------+
| Target Strike: 65                | Target Strike: 64                  |
| Expiry: April 17 (32 DTE)        | Expiry: March 20 (4 DTE)           |
| Premium: $1.05                   | Premium: $0.28                     |
|                                  |                                    |
| +------------------------------+ | +--------------------------------+ |
| | ANNUALIZED YIELD:  19.7%     | | | ANNUALIZED YIELD:  36.5%      | |
| +------------------------------+ | +--------------------------------+ |
| | TOTAL RETURN:      23.7%     | | | TOTAL RETURN:      40.5%      | |
| +------------------------------+ | +--------------------------------+ |
|                                  |                                    |
| Maintenance: Low (12x/Year)      | Maintenance: High (50x/Year)       |
| Assignment Risk: Low             | Assignment Risk: Moderate          |
+----------------------------------+------------------------------------+
| [ MARKOV PREDICTION CHART ]                                           |
| (Visualizing Price Probability for Expiry Windows)                    |
+-----------------------------------------------------------------------+
| [ EXECUTE SELECTION ]            | [ SAVE TO PLAN ]                   |
+-----------------------------------------------------------------------+

```

### Strategic Breakdown for Anti-Gravity

To ensure the coding agents build this correctly without wasting tokens, the implementation should follow this hierarchy:

1. **Backend "Juicy" Scanners**:
* Implement a new service that calculates the "Monthly Stable" and "Weekly Velocity" numbers for every ticker in your analysis list.
* Store these results in the `opportunities` collection with a `strategy_type` tag (e.g., `stable_yield` or `velocity_yield`).


2. **The "Yield-First" Component**:
* The UI should not just show the premium; it must render the calculated **Annualized Yield** and **Total Return** (which includes the 4% dividend you noted for D and T) as the primary visual anchors.


3. **Density Optimization**:
* Instead of the large empty buttons seen in your current UI, use a **Data Grid** inside the drawer to show Greeks and Markov probabilities side-by-side.



### Documentation Update for `features-requirements.md`

Add this to your **Epic 3: Dashboard & UX Features**:

* **[ ] High-Density Opportunity Drawer**:
* Replace `PortfolioGrid` popups with a right-aligned Drawer.
* **Logic**: Must display a side-by-side comparison of Monthly vs. Weekly strategies.
* **Visuals**: Use color-coded "Yield Badges" (Green for >20%, Gold for >40%).
* **Context**: Display P/E and C/P Skew prominently at the top of the drawer to validate the "Safe & Boring" thesis.

### from gemini convo: 
Juicy Fruit new/refine feature discussion regarding opportunities: 
https://gemini.google.com/share/711f5c56f9a9


QUESTION to gemini: 
Given today 20260316, stock analysis currently tickers: 
D 63.44 +.23up today has monthly (key only 12 option plays per month) as a April 17 32 days 65 (another key to remember) for $1.05 say i could do 12 of these per year 12*1.05/64 (~64 is cost basis) it's annualized yield of about 19.7% throw a 4% divvy on there and this a safe boring trade for ~20% per annum.  C/P skew is 4.12 
Compare T
T 27.73 +.01  flat they have weekly indicator of more action on options, sell 28 for .42 say we can do that 30x per year turns out 42% yield (more work week to week vs monthly) but more action. Divvy of 4%
both stocks have a decent 1 yr Call/Put Skew 3.5 
These are both low P/E stocks aka stable (18 & 9) given the decent Skew signal, these are two stocks I would want to see as recommendation from juicy fruit, 
How best  to write this requirement up so anti-gravity could write a opportunity finder for both tickers in my portfolio and tracker ones from analysis?
review the current feature-requirements list.  
Should i implement the requirements as part of existing code or extended or new feature build UI/UX tab?
Should I implement the scheduling and data pull and mongo first and then update UI/UX?  
The UI/uX opportunity widget in portfolio currently looks like shit. It's almost completely unusable for me using just the rolling call & dividend logic layout? 
Given my previous interactions on this topic, would recommend a different layout ui/ux? How best to document that for anti-gravity coding agents so they don't waste tokens and build a shit interface? 
My current: docs/features-requirements.md 
    - [ ] **Opportunity Finder**: Implement Opportunity Finder (ie: `/opportunity/{symbol}`) to show the most recent stats for an individual ticker.


My notes as i read it: : 
let me start with this complaint right out of the gate just to address an issue, maybe my fault also. but Monthly vs Weekly options doesn't necessary make something boring/safe.  The P/E price to earnings ratio is better traditional indicator of that ie: Weekly T has P/E of 9 (lower is better ie only 9 years at current earning to payoff the purchase price) vs big D as a p/e of 18.2 twice the time to payoff the purchase.  So one could say 2x more sloppy and less juicy.  However, the Call/Put Skew indicates a slightly better "bet" 4.11=D vs 3.5=T in the 1 year view and my main secret sauce for choosing juice fruits.  

I need to do better at explaining and/or capturing these complex multifactorial things.  Your help organizing them either in yml requirements. 

As I read thru the original document should I do one big feed back or do you "gemini" like it better if dissect in parts


## 
To optimize the Juicy Fruit opportunity finder for stable, high-yield trades like D and T, you need a requirement that specifically targets "Safe & Boring" yield generation alongside high-frequency weekly plays.
Below is the strategic review and the specific documentation updates for your coding agents.
1. Requirements Update for "Anti-Gravity"
To capture the logic for D (Monthly/Stable) and T (Weekly/Active), you should add a sub-section under Epic 2: Algorithmic Trading Engines. Use this specific language:
[ ] Systematic Yield Scanners (The "Boring but Juicy" Rule)
Monthly Stable Scan: Identify tickers with low P/E (<20) and high C/P Skew (>3.0).
Yield Logic: Filter for strikes near a specific target price (e.g., Strike 65 for D) where $\text{Annualized Yield} = (\text{Premium} \times \text{Occurrences/Year}) / \text{Cost Basis}$ exceeds 15%.
Weekly Velocity Scan: Identify tickers with weekly option liquidity (like T) that support a >30% annualized yield via frequent rolling.
Combined Signal: Output a "Total Expected Yield" (Options + Dividend %) for each opportunity.
2. Implementation Strategy: Backend First
You should implement the scheduling, data pull, and MongoDB persistence first.
Why: The UI/UX is currently "unusable" because it lacks the underlying data to display meaningful comparisons (like the 19.7% vs 42% yield difference you calculated).
The "Truth Engine": By storing these opportunities in Mongo first, the agent can "grade" them against actual price movement, ensuring that when the UI is built, it shows historical success rates.
3. UI/UX Overhaul Recommendation
The current "widget" approach is too cramped for the level of detail you need (Greeks, yield comparisons, and P/E ratios). Instead of 8-wide small boxes, move toward a Strategy-Centric Side Panel or Dedicated Opportunity Workspace.
Recommended Layout Change for Anti-Gravity:
The "Split-Pane" Analysis: In the TickerModal, replace the small buttons with a side-by-side "Strategy Comparison" table.
Visual Hierarchy:
Tier 1: Annualized Yield (The most important number for you).
Tier 2: Risk Metrics (P/E Ratio, C/P Skew, Dividend Safety).
Tier 3: Effort Level (Weekly vs. Monthly maintenance).
4. Documentation for Coding Agents
To prevent "wasted tokens" and "shit interfaces," update your features-requirements.md with a UI/UX Design Standard block:
Markdown
### UI/UX Design Standards (Juicy Fruit)
- **Density over Fluff**: Prioritize data tables and comparative metrics over large buttons/empty space.
- **Yield-First**: Every opportunity MUST display an "Annualized Yield %" and "Total Potential Return".
- **Comparison View**: The UI must allow comparing a 'Weekly' strategy vs a 'Monthly' strategy for the same ticker.
- **No Floating Modals for Core Data**: Use an expandable "Detail Drawer" on the right side of the screen to maintain context of the portfolio list.
