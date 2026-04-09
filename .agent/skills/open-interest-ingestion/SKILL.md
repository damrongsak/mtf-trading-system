---
name: open-interest-ingestion
description: Handles the ingestion of Open Interest Matrix Excel files into the MTF Trading System database.
---

# Open Interest Ingestion

This skill provides a standardized workflow for importing Gold (or other instrument) Open Interest Matrix Excel files into the system's PostgreSQL database.

## Workflow

### 1. File & Metadata Verification
Before processing, identify the target file (usually an `.xlsx` in `temp/oi_heatmap/`) and verify the snapshot date.
- **Date Check**: The parser extracts the snapshot date from the Excel **Sheet Name** (e.g., `Mon, Apr 6, 2026`). Verify this matches the user's intent.

### 2. Staging the Data
To ensure the `data-pipeline` service can access the file, copy it into the service's staged directory:
```bash
cp "path/to/source.xlsx" services/data-pipeline/oi_upload.xlsx
```

### 3. Execution
Run the ingestion script within the `data-pipeline` container context:
```bash
docker compose exec data-pipeline python3 scripts/import_oi_data.py oi_upload.xlsx
```

### 4. Verification (MANDATORY)
Always run these SQL checks in the `mtf-postgres` container after ingestion:

**A. Count & Date Validation**
```sql
SELECT snapshot_at, COUNT(*) 
FROM open_interest 
WHERE snapshot_at = 'YYYY-MM-DD' -- Insert extracted date
GROUP BY snapshot_at;
```

**B. Data Sanity Check**
```sql
SELECT contract_symbol, strike, call_oi, put_oi, underlying_price 
FROM open_interest 
WHERE snapshot_at = 'YYYY-MM-DD' 
AND (call_oi > 0 OR put_oi > 0)
LIMIT 5;
```

## Constraints
- **Format**: Only supports the specific multi-contract matrix format (Strikes in Col 0, C/P headers in Row 3).
- **Service Dependency**: Requires `data-pipeline` and `mtf-postgres` services to be healthy and running.
- **SDD Compliance**: Ensure the `OpenInterest` model in `specs/03_data_model.yaml` is not modified without a spec update.
