---
name: frontend-expert
description: Guidelines and procedures for creating, updating, or modifying the Next.js 16 (React 19) frontend, handling Node v22 via NVM, pnpm dependencies, Docker standalone builds, and strictly following 'use client' and TypeScript rules.
---

# Frontend Expert Guidelines

This skill provides mandatory guardrails when modifying or creating components in the Next.js 16 / React 19 frontend directory.

## 0. Mandatory Discovery (AI Auto-Understand)
Before making ANY changes or proposing a plan, you **MUST** perform these discovery steps to "auto-understand" the current state:
1.  **Dependency Scan**: Read `frontend/package.json` to identify installed UI libraries (Radix, Lucide, Tailwind versions) and chart libraries.
2.  **Config Review**: Read `frontend/next.config.ts` and `frontend/tsconfig.json` to check for path aliases (e.g., `@/*`) and output settings.
3.  **Pattern Matching**: List `frontend/components/` and `frontend/app/` to identify the existing folder structure and naming conventions (e.g., Kebab-case vs. PascalCase).
4.  **Type Check**: Verify the location of generated types in `frontend/lib/api/generated/`.

## 1. Environment & Dependencies (NVM & pnpm)
- **Node Version**: The project uses Node.js v22 managed via NVM.
- **Always source NVM**: Before running ANY frontend command (`pnpm run build`, `pnpm install`), you MUST load the NVM environment in your shell command:
  ```bash
  source ~/.nvm/nvm.sh && cd frontend && pnpm <command>
  ```
- **Monorepo Context**: Use `pnpm` exclusively. Do not use `npm` or `yarn`. If you add a dependency to `frontend/package.json`, run `pnpm i` from the `frontend/` directory (or use `pnpm --filter frontend add <package>`).

## 2. Next.js 16 & React 19 Architecture
- **App Router**: Use the Next.js App Router (`frontend/app/`). Do not create or use the legacy `pages/` directory.
- **Server vs. Client Components**:
  - By default, components in the `app/` directory are **Server Components**.
  - If a component requires React Hooks (`useState`, `useEffect`, `useRef`), browser APIs (`window`, `document`), or interactivity (onClick), you **MUST** add `"use client";` at the very top of the file.
  - Exception: Keep `"use client"` components as low in the component tree as possible (e.g., wrap a chart component rather than an entire page).

## 3. Libraries & Styling
- **Tailwind CSS**: Use Tailwind for all styling. Do not create `.css` files unless absolutely necessary for global configurations.
- **UI Components**: Check for existing components (e.g., Radix UI, Lucide React) in `frontend/package.json` before introducing new ones.
- **Charts (lightweight-charts)**: Note that `lightweight-charts` v5 removed deprecated methods. Use `chart.addSeries(LineSeries, ...)` instead of `chart.addLineSeries(...)`.

## 4. TypeScript & OpenAPI Generator
- **Strict Typing**: Do not use `any` unless absolutely forced. Use the generated types.
- **API Contracts**: The frontend consumes types generated from `specs/04_api_spec.yaml`. These types are found in `frontend/lib/api/generated/`.
- If an API response changes, prompt the user to re-generate types using:
  ```bash
  source ~/.nvm/nvm.sh && cd frontend && pnpm run gen:api
  ```

## 5. Docker & Standalone Builds
- **Standalone Mode**: Next.js is configured with `output: 'standalone'` in `next.config.ts`.
- **Dockerfile Awareness**: If you modify build behavior or public assets, understand that the `Dockerfile` copies `.next/standalone/app` to the root (or specific path) during the build. Do not modify the `Dockerfile` without understanding the `server.js` trace path structure.

## 6. Development Workflow
1. **Analyze First**: Check `frontend/package.json` and `frontend/next.config.ts` to understand existing configurations.
2. **Make Changes**: Create or update components.
3. **Validate**: Always run TypeScript compilation and linter before declaring the task complete:
   ```bash
   source ~/.nvm/nvm.sh && cd frontend && pnpm run build
   ```
   (Alternatively, run `pnpm tsc --noEmit` to just check types quickly).
