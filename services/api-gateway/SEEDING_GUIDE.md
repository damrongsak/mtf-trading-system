# Seeding Test Data Guide

This guide explains how to populate your MTF Trading System database with test/example data for development and testing.

## 📋 Available Seed Scripts

| Script | Purpose | What It Creates |
|--------|---------|-----------------|
| [`seed_risk_rules.py`](file:///home/dan/workspace/mtf-trading-system/services/api-gateway/scripts/seed_risk_rules.py) | Risk guardrails | 4 risk rules (MAX_RISK, MIN_LOT, MAX_ATR, MIN_RR) |
| [`seed_test_data.py`](file:///home/dan/workspace/mtf-trading-system/services/api-gateway/scripts/seed_test_data.py) | **Test users & data** | Users, funds, journal entries |
| [`init_qdrant.py`](file:///home/dan/workspace/mtf-trading-system/services/api-gateway/scripts/init_qdrant.py) | Vector database | Qdrant collections |

## 🚀 Quick Start

### 1. Prerequisites

Make sure your database is running:

```bash
# Start PostgreSQL and Qdrant via Docker
docker compose up -d postgres qdrant

# Or start full stack
docker compose up -d
```

### 2. Run Database Migrations

```bash
cd services/api-gateway
source venv/bin/activate  # Or: ./venv/bin/activate

# Apply all migrations
alembic upgrade head
```

### 3. Seed Risk Rules (Required)

```bash
python scripts/seed_risk_rules.py
```

**Creates:**
- `MAX_RISK_PER_TRADE`: $10 USD
- `MIN_LOT_SIZE`: 0.01 LOT
- `MAX_ATR_PIPS_SL`: 100 PIPS
- `MIN_RR_RATIO`: 2.00 RATIO

### 4. Seed Test Data (Recommended for Development)

```bash
python scripts/seed_test_data.py
```

**Creates:**
- **3 Test Users:**
  - `trader1` / `password123` (Regular trader)
  - `trader2` / `password123` (Regular trader)
  - `admin` / `admin123` (Superuser)
  
- **2 Funds:**
  - Alpha Trading Fund
  - Beta Testing Fund
  
- **15 Journal Entries:**
  - Realistic trading scenarios
  - Mix of winning and losing trades
  - Mental states, timeline events, root cause analysis

### 5. Initialize Qdrant (Optional)

```bash
python scripts/init_qdrant.py
```

**Creates:**
- `candle_embeddings` collection (for AI pattern matching)

## 🔑 Test Credentials

After seeding, you can login with:

| Username | Password | Role | Description |
|----------|----------|------|-------------|
| `trader1` | `password123` | Trader | Regular trading account |
| `trader2` | `password123` | Trader | Second trader account |
| `admin` | `admin123` | Admin | Superuser with full access |

## 📊 Verify Seeded Data

### Check Users

```bash
# Connect to database
docker exec -it mtf-trading-system-postgres-1 psql -U trader -d mtf_db

# List all users
SELECT username, email, is_active, is_superuser FROM users;

# Exit
\q
```

### Check Journal Entries

```bash
# Via API (requires backend running)
curl http://localhost:8000/api/v1/journal/entries

# Or via database
docker exec -it mtf-trading-system-postgres-1 psql -U trader -d mtf_db -c \
  "SELECT symbol, direction, pnl_amount, game_level FROM journal_entries LIMIT 5;"
```

### Check Risk Rules

```bash
docker exec -it mtf-trading-system-postgres-1 psql -U trader -d mtf_db -c \
  "SELECT rule_name, threshold_value, threshold_unit FROM risk_rules;"
```

## 🔄 Re-seeding Data

### Clear All Data (Dangerous!)

```bash
# Drop all tables and re-migrate
cd services/api-gateway
alembic downgrade base
alembic upgrade head

# Then re-run seed scripts
python scripts/seed_risk_rules.py
python scripts/seed_test_data.py
```

### Clear Specific Data

```sql
-- Connect to database
docker exec -it mtf-trading-system-postgres-1 psql -U trader -d mtf_db

-- Clear journal entries only
DELETE FROM timeline_events;
DELETE FROM journal_entries;
DELETE FROM mental_states;
DELETE FROM root_cause_analyses;

-- Clear users and funds
DELETE FROM user_funds;
DELETE FROM users;
DELETE FROM funds;

-- Clear risk rules
DELETE FROM risk_rules;
```

## 🛠️ Customizing Seed Data

### Modify User Count

Edit [`seed_test_data.py`](file:///home/dan/workspace/mtf-trading-system/services/api-gateway/scripts/seed_test_data.py):

```python
# In main() function, change:
users = seed_users(db, count=5)  # Create 5 users instead of 3
```

### Add Custom Users

Add to `users_data` array in `seed_users()`:

```python
{
    "username": "myuser",
    "email": "myuser@example.com",
    "password": "mypassword",
    "is_superuser": False
}
```

### Modify Journal Entry Count

```python
# In main() function, change:
entries = seed_journal_entries(db, users, count=50)  # Create 50 entries
```

## 🧪 Testing the Seeded Data

### 1. Login via Frontend

```bash
# Start backend
cd services/api-gateway
uvicorn app.main:app --reload

# Start frontend (in another terminal)
cd frontend
pnpm dev

# Navigate to http://localhost:3000/login
# Login with: trader1 / password123
```

### 2. Test API Endpoints

```bash
# Register new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"newuser","email":"new@example.com","password":"pass123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=trader1&password=password123"

# Get journal entries (requires token)
curl http://localhost:8000/api/v1/journal/entries \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 🐛 Troubleshooting

### "Table does not exist"
**Solution:** Run migrations first
```bash
alembic upgrade head
```

### "User already exists"
**Solution:** This is normal if you've run the script before. The script will skip existing users.

### "Connection refused"
**Solution:** Make sure PostgreSQL is running
```bash
docker compose up -d postgres
```

### "Module not found"
**Solution:** Activate virtual environment
```bash
cd services/api-gateway
source venv/bin/activate
pip install -r requirements.txt
```

## 📚 Related Documentation

- [Database Setup Guide](file:///home/dan/workspace/mtf-trading-system/services/api-gateway/DATABASE_SETUP.md)
- [GEMINI.md - Development Workflow](file:///home/dan/workspace/mtf-trading-system/GEMINI.md)
- [Data Model Specification](file:///home/dan/workspace/mtf-trading-system/specs/01_data_model.yaml)

## 🎯 Next Steps

After seeding data:

1. ✅ Test login with seeded credentials
2. ✅ Verify journal entries display in frontend
3. ✅ Test creating new journal entries
4. ✅ Explore the trading journal UI
5. ✅ Test risk rule enforcement

---

**Pro Tip:** Run `seed_test_data.py` whenever you reset your development database to quickly get back to a working state with realistic test data!
