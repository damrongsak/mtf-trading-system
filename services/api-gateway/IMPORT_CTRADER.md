# Importing cTrader Trading History

This guide explains how to import your cTrader trading history into the MTF Trading System journal.

## Prerequisites

- cTrader account statement exported as **Excel (.xlsx)** file
- User account created in the system (e.g., `trader1`)
- Backend services running

## Export from cTrader

1. Login to your cTrader account
2. Go to **History** or **Reports**
3. Select the date range for your trades
4. Export as **Excel (.xlsx)** format
5. Save the file (e.g., `cT_6023410_2025-12-04_12-41.xlsx`)

## Import Process

### Step 1: Place the Excel File

Copy your exported Excel file to a location accessible from the backend:

```bash
# Example: Copy to the example directory
cp ~/Downloads/cT_6023410_2025-12-04_12-41.xlsx /home/dan/workspace/mtf-trading-system/example/
```

### Step 2: Run the Import Script

Navigate to the API gateway directory and run the import script:

```bash
cd /home/dan/workspace/mtf-trading-system/services/api-gateway

# Run the import script
~/.local/bin/uv run python scripts/import_ctrader_excel.py \
  ../../example/cT_6023410_2025-12-04_12-41.xlsx \
  trader1
```

**Command Format:**
```bash
~/.local/bin/uv run python scripts/import_ctrader_excel.py <excel_file_path> <username>
```

**Arguments:**
- `<excel_file_path>`: Path to the cTrader Excel export file
- `<username>`: Username of the trader (e.g., `trader1`, `trader2`, `admin`)

### Step 3: Verify Import

The script will output progress information:

```
📄 Parsing cTrader Excel file: ../../example/cT_6023410_2025-12-04_12-41.xlsx
📊 Reading Excel file: ../../example/cT_6023410_2025-12-04_12-41.xlsx
✅ Found 111 rows
📋 Columns: ID, Symbol, Opening direction, Opening time, ...
✅ Parsed 111 trades

🔄 Importing to journal for user 'trader1'...
  📝 Imported 10 trades...
  📝 Imported 20 trades...
  ...
✅ Successfully imported 111 trades
```

## What Gets Imported

For each trade, the import script creates:

### 1. **Journal Entry**
- Symbol (e.g., XAU/USD)
- Direction (LONG/SHORT)
- Entry and exit prices
- P&L amount and pips
- Trading session (ASIAN/LONDON/NY)
- Game level (A/B/C based on performance)
- Timestamps (opening and closing times)

### 2. **Mental State**
Automatically generated based on trade outcome:
- **Winning trades**: Higher confidence, lower fear
- **Losing trades**: Lower confidence, higher fear
- **Stop-outs**: High tilt level

### 3. **Timeline Events**
- Entry event with opening price
- Exit event with closing price and P&L

### 4. **Root Cause Analysis** (for stop-outs only)
- Problem identification
- Root cause analysis
- Correction suggestions

## Game Level Classification

Trades are automatically classified:
- **A-Game**: Net P&L > $20
- **B-Game**: Net P&L > $5
- **C-Game**: Net P&L ≤ $5

## Trading Session Detection

Based on opening time (UTC+7):
- **ASIAN**: 01:00 - 09:00
- **LONDON**: 09:00 - 13:00
- **NY**: 13:00 - 21:00

## Duplicate Handling

The script checks for duplicates based on:
- User ID
- Symbol
- P&L amount

Duplicate trades are skipped automatically.

## Viewing Imported Data

After import, you can view your trades:

### Frontend (Web UI)
1. Navigate to `http://localhost:3000/login`
2. Login with your credentials (e.g., `trader1` / `password123`)
3. Go to `/journal` to see all imported trades
4. Go to `/dashboard` to see your equity curve and stats

### API (Direct)
```bash
# Get authentication token
TOKEN=$(curl -X POST http://localhost/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=trader1&password=password123" | jq -r '.auth.access_token')

# Get journal entries
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/journal/?page=1&per_page=10"
```

## Troubleshooting

### Error: "User not found"
Make sure the username exists in the database. Create a user first:
```bash
cd services/api-gateway
~/.local/bin/uv run python scripts/seed_test_data.py
```

### Error: "File not found"
Check the file path is correct and the file exists:
```bash
ls -lh /path/to/your/file.xlsx
```

### Warning: "Skipped X duplicate trades"
This is normal if you've already imported this data before. The script prevents duplicate entries.

## Script Location

The import script is located at:
```
services/api-gateway/scripts/import_ctrader_excel.py
```

## Dependencies

The script requires:
- `pandas` - Data manipulation
- `openpyxl` - Excel file reading
- `sqlalchemy` - Database operations

These are automatically installed when using `uv`.
