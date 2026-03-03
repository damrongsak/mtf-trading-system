# Implementation Plan - [Feature Name]

## Description
Briefly describe the change and its goal.

## Spec Compliance (MANDATORY)
Check off which specs are affected and have been updated.

- [ ] `specs/01_architecture.md`
- [ ] `specs/03_data_model.yaml`
- [ ] `specs/04_api_spec.yaml`
- [ ] `specs/08_logic_rules.md`

### Generation Scripts Run
- [ ] `docker compose exec api-gateway /venv/bin/bash scripts/gen_backend.sh`
- [ ] `cd frontend && pnpm run gen:api`

## Proposed Changes
List changes file by file.

### [Service Name]
#### [MODIFY] [file basename](file:///path/to/file)
- Change description.

## Verification Plan
### Automated Tests
- Command to run.
### Manual Verification
- Steps to verify.
