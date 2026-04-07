# Playwright Manifesto

> **Confidence over Coverage.**  
> We do not test everything. We test the things that matter, reliably, every time.

---

## Part 1 — What is a `.claude/worktrees/` Setup?

Git worktrees let you check out multiple branches of the same repo simultaneously into separate directories. Combined with an agent-per-worktree model, each Claude agent gets its own isolated file system slice with no cross-contamination.

```
repo/
├── .claude/
│   ├── CLAUDE.md                   ← global agent instructions
│   ├── playwright-manifesto.md     ← this file (shared context for all agents)
│   └── worktrees/                  ← agent working directories
│       ├── feature-my-feature/     ← Agent A (building)
│       ├── test-integration/       ← Agent B (e2e validation)
│       └── fix-regression/         ← Agent C (patching)
├── e2e/
│   ├── specs/                      ← integration specs live here
│   └── fixtures/
├── playwright.config.ts
└── package.json
```

### Shell setup

```bash
# Create a worktree for an agent working on a feature branch
git worktree add .claude/worktrees/feature-my-feature feature/my-feature

# Create a worktree for the integration test agent
git worktree add .claude/worktrees/test-integration test/integration

# List all active worktrees
git worktree list

# Remove when done
git worktree remove .claude/worktrees/feature-my-feature
```

### Why worktrees for agents?

- Each agent operates on its own branch with no shared working tree state
- The integration test agent can run against a frozen feature snapshot while the feature agent keeps building
- No stash conflicts, no accidental cross-branch file mutations
- The `.claude/` directory (including this manifesto) is shared from the root — all agents read the same rules

---

## Part 2 — Integration Specs (e2e with Playwright)

Integration specs cover **user journeys**, not implementation details.

### What belongs in an integration spec

| In scope | Out of scope |
|---|---|
| User can sign in with valid credentials | Internal auth state machine transitions |
| User can add item to cart and check out | Redux store shape |
| Error message appears on invalid form submit | Which validator function fires |
| Dashboard loads with correct data after login | API response object structure |

### Spec anatomy

```typescript
// e2e/specs/checkout.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Checkout — happy path', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Use fixtures or page objects — never hardcode test data inline
    await loginAsTestUser(page);
  });

  test('user can complete purchase', async ({ page }) => {
    // Arrange — navigate to a known state
    await page.getByRole('link', { name: 'Shop' }).click();

    // Act — user-facing actions only
    await page.getByRole('button', { name: 'Add to cart' }).first().click();
    await page.getByRole('link', { name: 'Cart' }).click();
    await page.getByRole('button', { name: 'Checkout' }).click();

    // Assert — observable outcome, not internal state
    await expect(page.getByRole('heading', { name: 'Order confirmed' })).toBeVisible();
  });
});
```

### Naming convention

```
e2e/specs/
├── auth/
│   ├── sign-in.spec.ts
│   └── sign-out.spec.ts
├── checkout/
│   ├── happy-path.spec.ts
│   └── error-states.spec.ts
└── dashboard/
    └── data-loading.spec.ts
```

One spec file per feature area. Group `describe` blocks by scenario, not by page.

---

## Part 3 — Definition of Done

A feature is not done until these gates pass. No exceptions.

### DoD Checklist

- [ ] All existing e2e specs pass on the feature branch (zero regressions)
- [ ] New integration spec written for every new user-facing behavior
- [ ] New spec covers at least: happy path + one meaningful error state
- [ ] No `test.only` or `test.skip` left in committed code
- [ ] No hardcoded waits (`page.waitForTimeout`) — use `waitFor` conditions instead
- [ ] Spec runs in CI without flake across 3 consecutive runs
- [ ] Spec is tagged with the feature area (`@checkout`, `@auth`, etc.)
- [ ] PR description links to the spec file(s) added or modified

### CI gate configuration

```typescript
// playwright.config.ts
export default defineConfig({
  retries: process.env.CI ? 1 : 0,  // one retry in CI to catch transient infra noise
  reporter: [
    ['html'],
    ['junit', { outputFile: 'results/junit.xml' }],  // required for CI gate
  ],
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
});
```

The CI pipeline blocks merge if:
- Any spec fails after retries
- A new spec is missing for a PR that adds user-facing behavior
- Flake rate for the changed spec set exceeds 5% over the last 10 runs

---

## Part 4 — Manifesto for Avoiding Brittle Tests

Brittle tests destroy confidence. A test suite that fails randomly trains engineers to ignore failures — the worst possible outcome.

### The anti-brittle rules

#### 1. Select by role and semantic label, never by CSS

```typescript
// BAD — breaks on any styling refactor
await page.locator('.checkout-btn-primary').click();
await page.locator('#submit').click();
await page.locator('div > form > button:nth-child(2)').click();

// GOOD — survives redesigns, tests what users actually see
await page.getByRole('button', { name: 'Checkout' }).click();
await page.getByRole('link', { name: 'Sign in' }).click();
await page.getByLabel('Email address').fill('user@example.com');
```

#### 2. Never wait for time — wait for state

```typescript
// BAD — arbitrary sleep, always wrong
await page.waitForTimeout(2000);

// GOOD — wait for the condition that matters
await expect(page.getByRole('status')).toHaveText('Saved');
await page.waitForURL('**/dashboard');
await page.getByRole('progressbar').waitFor({ state: 'hidden' });
```

#### 3. Test behavior, not implementation

```typescript
// BAD — tests internal wiring, not the user experience
expect(store.getState().cart.items.length).toBe(1);

// GOOD — tests what the user observes
await expect(page.getByRole('status', { name: 'Cart' })).toContainText('1 item');
```

#### 4. Keep tests independent

Every test must be able to run in any order, alone, or in parallel.

```typescript
// BAD — test depends on previous test having run
test('user can check out', async ({ page }) => {
  // assumes "add to cart" test already ran and populated state
  await page.goto('/cart');
  ...
});

// GOOD — each test creates its own state
test('user can check out', async ({ page }) => {
  await addItemToCart(page, 'Widget Pro');
  await page.goto('/cart');
  ...
});
```

#### 5. Use test fixtures for setup — never repeat login logic

```typescript
// fixtures/authenticated.ts
export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({ page }, use) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill(process.env.TEST_USER_EMAIL!);
    await page.getByLabel('Password').fill(process.env.TEST_USER_PASSWORD!);
    await page.getByRole('button', { name: 'Sign in' }).click();
    await page.waitForURL('**/dashboard');
    await use(page);
  },
});

// spec file — clean, no ceremony
test('user sees their orders', async ({ authenticatedPage: page }) => {
  await page.getByRole('link', { name: 'Orders' }).click();
  await expect(page.getByRole('table')).toBeVisible();
});
```

#### 6. Tag and scope — run only what the PR touches

```typescript
// Tag by feature area
test('user can reset password', { tag: '@auth' }, async ({ page }) => { ... });

// Run only auth specs in CI for auth-only PRs
// npx playwright test --grep @auth
```

#### 7. One assertion per behavioral outcome — not per DOM element

```typescript
// BAD — fragile, tests markup structure
await expect(page.locator('h1')).toHaveText('Order confirmed');
await expect(page.locator('.order-number')).toBeVisible();
await expect(page.locator('.confirmation-icon')).toHaveClass(/success/);

// GOOD — tests that the outcome is present and meaningful
await expect(page.getByRole('heading', { name: 'Order confirmed' })).toBeVisible();
await expect(page.getByText(/order #\d+/i)).toBeVisible();
```

---

## Part 5 — Confidence over Coverage: the philosophy

**Coverage is a vanity metric. Confidence is the goal.**

A 95% coverage number means nothing if:
- The tests are brittle and fail on every deploy
- The tests don't cover the paths users actually take
- Engineers have learned to re-run CI until it passes

### What confidence looks like

- The suite is **fast enough to run on every PR** (target: under 3 minutes for critical paths)
- A **red build is always meaningful** — engineers stop and look, not re-run and hope
- **New features ship with specs** that protect them from future regression
- The manifesto is **read by agents and humans alike** — it's the contract, not a suggestion

### The two questions every spec must answer

1. **What user behavior does this protect?** (If you can't name it, the test shouldn't exist)
2. **Would a regression in this behavior be caught within one CI run?** (If no, fix the test)

### Explicitly not in scope for integration specs

- Internal API contract testing → use unit tests or contract tests (Pact, MSW)
- Visual regression pixel-diffing → use Chromatic or Percy as a separate step
- Load and performance testing → use k6 or Lighthouse CI as a separate step
- 100% branch coverage → not the job of e2e; that's unit test territory

---

## Quick reference — agent instructions

When an agent in `.claude/worktrees/` is working on tests, it reads this file and follows these rules in order:

1. Run the existing suite first. If anything is broken before your change, flag it — don't suppress it.
2. Write specs for user journeys, not for implementation.
3. Select by role. Never by CSS class, ID, or nth-child.
4. Every test is independent. Every test leaves no state behind.
5. A test that flakes once in CI is a bug. Fix it before merging.
6. The DoD checklist above is not optional. Every item must be checked before the PR is ready for review.

> The suite is a safety net for users, not a trophy for coverage dashboards.
