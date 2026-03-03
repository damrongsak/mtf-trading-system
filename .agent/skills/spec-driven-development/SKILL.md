---
name: spec-driven-development
description: |
  Use this skill when the user asks for a new feature, API change, data model update, or schema modification.
  This skill enforces the "Spec-Driven Development" (SDD) workflow.
---

# Spec-Driven Development (SDD)
**Critical Rule:** Do NOT write implementation code until you have validated the specs.

## Process
When you receive a request to change the system (Add Feature, Change API, Fix Logic):

1.  **Check the Specs First**
    *   Read `specs/00_product_requirements.md` (for big features).
    *   Read `specs/03_data_model.yaml` (for database/schema changes).
    *   Read `specs/04_api_spec.yaml` (for API/Route changes).

2.  **Search for Duplicates (CRITICAL)**
    *   Before editing a spec, search for duplicate `.yaml` or `.md` files in subdirectories (e.g., `services/api-gateway/04_api_spec.yaml`).
    *   **DELETE duplicates immediately** to avoid stale configurations.

3.  **Update the Specs (if needed)**
    *   If the user's request requires a change to the data model, **YOU MUST** update `specs/03_data_model.yaml` first.
    *   If the user's request changes an API contract, **YOU MUST** update `specs/04_api_spec.yaml` first.

4.  **Create an Implementation Plan**
    *   Always create an `implementation_plan.md` (or update existing).
    *   Include a **Spec Compliance** section detailing which specs were modified and which generation scripts were run.

5.  **Generate Code (Don't Write Logic Yet)**
    *   **Backend Models:** Run `docker compose exec api-gateway /venv/bin/bash scripts/gen_backend.sh`.
    *   **Frontend Client:** Run `pnpm run gen:api` in the `frontend/` directory.

4.  **Implement Logic**
    *   Only *after* the steps above can you write the actual Python/React implementation.
    *   Reference the updated specs in your implementation comments.

## Example
**User:** "Add a 'risk_score' to the user profile."

**Agent Action:**
1.  Read `specs/03_data_model.yaml`.
2.  Edit `specs/03_data_model.yaml` to add `risk_score: float`.
3.  Run generation script.
4.  Edit `services/api-gateway/app/models/user.py` (if manual adjustment needed) or implement the logic that uses this score.
