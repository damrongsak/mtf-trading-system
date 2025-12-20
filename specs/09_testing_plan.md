# Testing Plan (v1.0)

## 1. Overview
This document defines the strategy for End-to-End (E2E) testing of the MTF Trading System. The goal is to ensure critical user flows function correctly across the full stack (Next.js Frontend + FastAPI Backend + Database).

## 2. Technology Stack
- **Framework:** [Playwright](https://playwright.dev/)
- **Language:** TypeScript
- **Runner:** `npm run test:e2e` (to be configured)
- **CI Integration:** GitHub Actions (future)

## 3. Scope & Critical Flows

### 3.1 Authentication Flow
- [ ] User can register a new account.
- [ ] User can login with valid credentials.
- [ ] Invalid credentials show error message.
- [ ] Protected routes redirect to login.

### 3.2 Dashboard & Market Analysis
- [ ] Dashboard loads without crashing.
- [ ] Signal cards display data.
- [ ] Market Watch loads candles (mocked/real).

### 3.3 Trading Operations (Mock Execution)
- [ ] User can place a MANUAL trade via "Open Position" or Signal.
- [ ] Optimization/Backtest form submission works.

### 3.4 Journaling
- [ ] User can create a new journal entry via the Wizard.
- [ ] Entry appears in the list view.

## 4. Setup Instructions

### 4.1 Directory Structure
```
frontend/
  e2e/
    auth.spec.ts
    dashboard.spec.ts
    cms.spec.ts
  playwright.config.ts
```

### 4.2 Configuration
- Base URL: `http://localhost:3000`
- Headless mode by default.
- Global setup for authentication state (save storage state).

## 5. Next Steps
1. Install Playwright in `frontend/`.
2. Configure `playwright.config.ts`.
3. Write `auth.spec.ts` as the first test case.
