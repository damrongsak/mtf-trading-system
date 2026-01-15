---
name: code-review
description: |
  Use this skill when reviews code changes for bugs, style issues, and best practices.
  Use when reviewing PRs or checking code quality.
---

# Code Review Guidelines

When reviewing code for the MTF Olympus project, strictly follow this checklist.

## 1. Spec Compliance (Crucial)
*   [ ] **Spec First:** If this is a new feature or API change, does it match `specs/03_data_model.yaml` and `specs/04_api_spec.yaml`?
*   [ ] **No Magic:** Are the changes reflected in the documentation?

## 2. Python / Backend Standards
*   [ ] **Type Hints:** All functions **MUST** have type hints (e.g., `def foo(x: int) -> str:`).
*   [ ] **Async Correctness:** Ensure `await` is used correctly. No blocking calls in `async def`.
*   [ ] **Error Handling:** No bare `except:`. Always catch specific exceptions (e.g., `except ValueError:`).
*   [ ] **Vectorization:** In `strategy-core`, ensure `pandas` and `vectorbt` are used for data processing. Avoid iterating over DataFrames with `for` loops.

## 3. Frontend / React Standards
*   [ ] **Strict Types:** No `any`. Use auto-generated types from `frontend/lib/api/types.gen.ts`.
*   [ ] **Hooks:** Ensure `useEffect` dependencies are exhaustive.
*   [ ] **Performance:** Check for unnecessary re-renders.

## 4. Testing
*   [ ] **Coverage:** Do new functions have corresponding unit tests?
*   [ ] **Mocks:** Are external calls (Oanda, DB) properly mocked?

## How to Provide Feedback
*   Group comments by file.
*   Use **bold** for critical blocking issues.
*   Provide code snippets for suggested fixes.
