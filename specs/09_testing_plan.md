# Testing Plan (v1.0)

## 1. Overview
This document defines the strategy for End-to-End (E2E) testing of the MTF Trading System. The goal is to ensure critical user flows function correctly across the full stack (Next.js Frontend + FastAPI Backend + Database).

- **CI Integration:** GitHub Actions (future)

## 2. Technology Stack
### 2.1 Frontend (E2E)
- **Framework:** [Playwright](https://playwright.dev/)
- **Language:** TypeScript

### 2.2 Backend (Unit & Integration)
- **Framework:** [Pytest](https://docs.pytest.org/) (>=8.0.0)
- **Async Support:** `pytest-asyncio` (>=0.25.0)
- **Coverage:** `pytest-cov`

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

## 6. Dependency Testing Strategy

### 6.1 Critical UI Dependencies
- **Charts (`recharts`, `lightweight-charts`)**:
    - **E2E**: Verify chart container is visible and canvas/svg elements render (`page.locator('canvas').toBeVisible()`).
    - **Visual**: Use Snapshot testing for static charts (`recharts`).
- **UI Libs (`@radix-ui`, `framer-motion`)**:
    - **Interactive**: Verify open/close states of Dialogs, Dropdowns via Playwright.

### 6.2 State & Logic
- **Context (`AuthContext`)**:
    - **Unit**: Test `useAuth` hook limits and token persistence logic.
- **API (`axios`)**:
    - **Unit**: Verify interceptor error handling (401/500 responses).
