# Database Setup Guide

This guide explains how to set up and manage the database schema for the MTF Trading System.

## Overview

The database schema is defined in [specs/01_data_model.yaml](../../specs/01_data_model.yaml), following the Spec-Driven Development (SDD) methodology. All database entities are designed to support the MVP requirements defined in the PRD.

## Database Architecture

### Entities

| Entity | Purpose | Key Features |
|--------|---------|--------------|
| **Candle** | OHLCV market data with MTF indicators | Non-look-ahead indicators, multi-timeframe alignment |
| **Trade** | Individual trade records | Risk tracking, REJECTED status for violations, MAE/MFE |
| **StrategyRun** | Backtest run results | Performance metrics (Sharpe, MDD, Win Rate) |
| **RiskRule** | Configurable risk guardrails | F2.2-F2.4 enforcement, centralized thresholds |

### Key Design Features

1. **Risk Guardrails (G1 Priority)**
   - Database-level CHECK constraints enforce:
     - `risk_usd <= 10.00` (F2.2)
     - `lot_size >= 0.01` (F2.3)
     - `atr_pips <= 100.0` (F2.4)
     - `rr_ratio >= 2.0`

2. **REJECTED Trade Tracking**
   - `Trade.status` includes `REJECTED` enum value
   - `Trade.rejection_reason` stores violation details
   - Critical for auditing risk compliance (US3)

3. **Performance Metrics**
   - `StrategyRun` stores Sharpe, MDD, Win Rate (G2 success criteria)
   - MAE/MFE tracking in `Trade` table (F3.3)

4. **Vector Store Integration**
   - Qdrant collection: `candle_embeddings`
   - Purpose: Pattern matching, LLM retrieval (future AI Analyst)

## Prerequisites

1. PostgreSQL 15+ with pgvector extension
2. Qdrant vector database
3. Python 3.13+ with dependencies installed

## Setup Instructions

### 1. Environment Configuration

Create a `.env` file in the `services/api-gateway` directory:

```bash
# Database Configuration
DATABASE_URL=postgresql://trader:trader@localhost:5432/mtf_db
POSTGRES_USER=trader
POSTGRES_PASSWORD=trader
POSTGRES_DB=mtf_db

# Qdrant Configuration
QDRANT_URL=http://localhost:6333

# Risk Guardrails (ENV overrides for testing)
MAX_RISK_PER_TRADE=10.00
MIN_LOT_SIZE=0.01
MAX_ATR_PIPS_SL=100.0

# Debug
DEBUG=false
```

### 2. Install Dependencies

```bash
cd services/api-gateway
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Database Migrations

Apply the initial schema migration:

```bash
# From services/api-gateway directory
source venv/bin/activate
alembic upgrade head
```

This will create all four tables:
- `candles`
- `trades`
- `strategy_runs`
- `risk_rules`

### 4. Seed Default Risk Rules

Populate the risk_rules table with MVP defaults:

```bash
python scripts/seed_risk_rules.py
```

This creates:
- `MAX_RISK_PER_TRADE`: $10 USD (F2.2)
- `MIN_LOT_SIZE`: 0.01 LOT (F2.3)
- `MAX_ATR_PIPS_SL`: 100 PIPS (F2.4)
- `MIN_RR_RATIO`: 2.00 RATIO

### 5. Initialize Qdrant Collections

Create the vector database collection:

```bash
# Ensure Qdrant is running first (docker-compose up qdrant)
python scripts/init_qdrant.py
```

This creates the `candle_embeddings` collection with:
- Vector size: 768 (sentence-transformers default)
- Distance metric: COSINE

## Verification

### Check PostgreSQL Tables

```bash
psql postgresql://lab:lab1234@localhost:5432/mtf_trading

-- List all tables
\dt

-- Verify risk_rules seeding
SELECT rule_name, threshold_value, threshold_unit, is_active FROM risk_rules;

-- Check table constraints
SELECT conname, contype, consrc
FROM pg_constraint
WHERE conrelid = 'trades'::regclass;
```

### Check Qdrant Collection

```bash
curl http://localhost:6333/collections/candle_embeddings
```

## Schema Management

### Creating New Migrations

When modifying models in `app/models/`:

1. Update the corresponding SQLAlchemy model
2. Update `specs/01_data_model.yaml` (source of truth)
3. Generate migration:

```bash
alembic revision --autogenerate -m "Description of changes"
```

4. Review the generated migration in `alembic/versions/`
5. Apply migration:

```bash
alembic upgrade head
```

### Rollback Migrations

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

### View Migration History

```bash
# Show current version
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic show
```

## Data Model Validation

The database schema enforces the following validation rules from `specs/01_data_model.yaml`:

### Trade Validations
- ✅ `risk_usd <= 10.00` (CHECK constraint)
- ✅ `lot_size >= 0.01` (CHECK constraint)
- ✅ `atr_pips <= 100.0 OR atr_pips IS NULL` (CHECK constraint)
- ✅ `rr_ratio >= 2.0 OR rr_ratio IS NULL` (CHECK constraint)

### StrategyRun Validations
- ✅ `end_date >= start_date` (CHECK constraint)

### Unique Constraints
- ✅ `candles(symbol, timeframe, timestamp)` - Prevents duplicate candle data
- ✅ `risk_rules(rule_name)` - Prevents duplicate rule names

## Testing Risk Guardrails

Test that database constraints work correctly:

```sql
-- This should FAIL (violates $10 risk cap)
INSERT INTO trades (
    trade_id, symbol, strategy_name, signal_timestamp,
    status, direction, entry_price, sl_price, tp_price,
    lot_size, risk_usd
) VALUES (
    gen_random_uuid(), 'XAU/USD', 'test_strategy', NOW(),
    'OPEN', 'LONG', 1950.00, 1940.00, 1970.00,
    0.10, 15.00  -- risk_usd > 10.00 should FAIL
);

-- This should SUCCEED
INSERT INTO trades (
    trade_id, symbol, strategy_name, signal_timestamp,
    status, direction, entry_price, sl_price, tp_price,
    lot_size, risk_usd
) VALUES (
    gen_random_uuid(), 'XAU/USD', 'test_strategy', NOW(),
    'OPEN', 'LONG', 1950.00, 1940.00, 1970.00,
    0.10, 10.00  -- risk_usd = 10.00 should SUCCEED
);
```

## Troubleshooting

### "relation does not exist" error
- Ensure migrations have been run: `alembic upgrade head`
- Check database connection in `.env` file

### "no such table: alembic_version"
- Alembic has not been initialized properly
- Re-run: `alembic upgrade head`

### Qdrant connection refused
- Ensure Qdrant is running: `docker-compose up qdrant`
- Check `QDRANT_URL` in `.env`

### Risk rule seed script reports "already seeded"
- This is normal if you've run the script before
- To re-seed, manually delete rows: `DELETE FROM risk_rules;`

## Next Steps

After completing database setup:

1. ✅ Implement Risk Engine (F2.1-F2.4) using `risk_rules` table
2. ✅ Build API endpoints using Pydantic schemas in `app/schemas/`
3. ✅ Implement signal generation logic (F1.1-F1.4)
4. ✅ Set up Vectorbt backtesting harness (F3.1-F3.3)

## References

- Source of Truth: [specs/01_data_model.yaml](../../specs/01_data_model.yaml)
- PRD: [specs/00_PRD.md](../../specs/00_PRD.md)
- SQLAlchemy Models: [app/models/](./app/models/)
- Pydantic Schemas: [app/schemas/](./app/schemas/)
