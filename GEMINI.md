# GEMINI.md

## 🚀 Project Overview
**MTF Trading System** is a sophisticated algorithmic trading platform designed for XAU/USD (Gold) trading. It utilizes a **Multi-Timeframe (MTF)** analysis approach combined with **Smart Money Concepts (SMC)**.

The project distinguishes itself through:
1.  **Spec-Driven Development (SDD):** Architecture and data contracts are defined in YAML/Markdown specs *before* implementation.
2.  **AI-First Design:** Integrates Google Gemini (via Vertex AI) for semantic market analysis and reasoning.
3.  **Microservices Architecture:** Modular Python services for strategy, execution, and AI analysis, fronted by a Next.js dashboard.

## 🏗️ Architecture & Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | Next.js 16 (React 19) | Dashboard for signals, trade logs, and backtest visualization. |
| **API Gateway** | Python (FastAPI) | Entry point for all backend operations; routes to internal logic. |
| **Strategy Core** | Python (Vectorbt, Pandas, Quantreo) | Implements MTF/SMC logic, signal generation, and backtesting. |
| **Execution Service** | Python (FastAPI, PyPortfolioOpt) | Handles trade execution and Risk Parity sizing. |
| **Database** | PostgreSQL 15 + pgvector | Stores relational trade data and vector embeddings. |
| **Vector Store** | Qdrant | Handles similarity search for pattern recognition and RAG. |
| **Infrastructure** | Docker Compose, Nginx | Container orchestration and reverse proxying. |
| **Cloud Target** | GCP (Cloud Run, SQL) | Production environment (Project: `line-bot-2b383`). |

### 📂 Directory Structure
*   `specs/`: **Source of Truth**. Contains Architecture (`01`), Data Models (`03`), API Contracts (`04`), and Logic Rules (`08`).
*   `services/`: Backend microservices (`api-gateway`, `strategy-core`, `ai-analyst`, `execution`).
*   `frontend/`: Next.js web application.
*   `infra/`: Infrastructure configurations (Nginx, etc.).
*   `docker-compose.yml`: Orchestration for local development.

## 🛠️ Development Workflow

### 1. The SDD Process (Crucial)
**Do not write code without checking specs first.**
1.  **Read Specs:** Check `specs/` for defining behavior.
2.  **Update Specs:** If a new feature is needed, modify `03_data_model.yaml` or `04_api_spec.yaml` first.
3.  **Generate Code:**
    *   **Backend Models:** `services/api-gateway/scripts/gen_backend.sh`
    *   **Frontend Client:** `cd frontend && pnpm run gen:api`
4.  **Implement:** Scaffold code based on the updated specs and generated types.

### 2. Running the System
**Prerequisites:** Docker & Docker Compose, Node.js (pnpm), `uv` (for backend development).

*   **Install uv (first time only):**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

*   **Environment Setup Notes (WSL/Local):**
    *   **uv:** If `uv` is not in PATH, add `export PATH="$HOME/.local/bin:$PATH"` or run via `~/.local/bin/uv`.
    *   **Node/pnpm:** Managed via `nvm`. If commands are missing, run: `source ~/.nvm/nvm.sh`.

*   **Full Stack (Recommended):**
    ```bash
    docker compose up --build
    ```
    *   Frontend: `http://localhost:3000`
    *   API Docs: `http://localhost:8000/docs`
    *   Qdrant Dashboard: `http://localhost:6333/dashboard`

*   **Command Execution Strategy (Important):**
    *   **Prefer Docker:** For consistency, use `docker compose exec <service> <command>` for backend/database tasks.
        *   Example: `docker compose exec api-gateway uv run pytest`
    *   **Local Shell:** The environment uses `zsh` with `nvm` (Node v22) and `conda`.
        *   Frontend: Ensure Node v22 is active (`nvm use 22`).
        *   Tools: `uv` is in `~/.local/bin`.

*   **Frontend Only:**
    ```bash
    nvm use 22
    pnpm install
    pnpm --filter frontend dev
    # Or: pnpm --filter frontend build / test
    ```

*   **Backend Service (Standalone):**
    ```bash
    cd services/api-gateway
    # Install dependencies (first time or when dependencies change)
    uv sync
    # Run the server
    uv run uvicorn app.main:app --reload
    ```

### 3. Testing
*   **Backend:** `uv run pytest` (Contract tests derived from specs).
*   **Backtesting:** `vectorbt` based simulations.

### 4. Database Migration (Alembic)
To apply schema changes to the database:

1.  **Connect to the API Gateway service:**
    ```bash
    cd services/api-gateway
    ```

2.  **Set the Database URL (if running locally against Docker DB):**
    ```bash
    export DATABASE_URL=postgresql://trader:trader@localhost:5432/mtf_db
    ```

3.  **Create a new migration (after modifying models):**
    ```bash
    ./venv/bin/alembic revision --autogenerate -m "Description of changes"
    ```

4.  **Apply migrations:**
    ```bash
    ./venv/bin/alembic upgrade head
    ```
### 5. Git Flow & Version Control
**Strictly follow this workflow for all changes:**
1.  **Checkout `dev` branch:** `git checkout dev`
2.  **Pull latest changes:** `git pull origin dev`
3.  **Create a feature branch:** `git checkout -b feature/your-feature-name`
4.  **Implement changes:** Follow SDD and Clean Code principles.
5.  **Commit changes:** Use descriptive commit messages (e.g., `feat: add user auth`, `fix: resolve db connection`).
6.  **Merge to `dev`:**
    ```bash
    git checkout dev
    git merge feature/your-feature-name
    git push origin dev
    ```

### 6. Frontend Clean Code Guidelines
Adhere to these principles for a scalable and maintainable frontend:
*   **Modularization:** Break down the app into small, independent components.
*   **Directory Structure:** Use a clear layout (e.g., `src/components`, `src/hooks`, `src/context`).
*   **Naming Conventions:**
    *   **Components:** `UpperCamelCase` (e.g., `SignalCard.tsx`)
    *   **Functions/Hooks:** `camelCase` (e.g., `useAuth`, `fetchSignals`)
*   **State Management:**
    *   Use `useContext` + `useReducer` for global state (Auth, Theme).
    *   Keep form/toggle state local to components.
    *   Avoid overusing global state libraries unless necessary.
*   **Performance:**
    *   Implement **Code-Splitting** and **Lazy-Loading** for routes.
    *   Optimize images and assets.
*   **Design Consistency:** Always use the design system tokens (colors, spacing) defined in `globals.css` / Tailwind config.

### 7. Frontend API Client Architecture
**All API calls MUST use the centralized axios client in `frontend/lib/api/`.** Do not use `fetch()` directly.

#### 📂 lib/ Structure
```
frontend/lib/
├── api/
│   ├── client.ts       # Axios instance with interceptors (NEVER modify directly)
│   ├── types.ts        # Shared TypeScript interfaces
│   ├── auth.ts         # Auth endpoints
│   ├── journal.ts      # Journal endpoints
│   └── index.ts        # Barrel export
├── hooks/
│   ├── useJournalEntries.ts
│   ├── useAsync.ts     # Generic async handler
│   └── index.ts
└── utils.ts            # Formatting, storage, helpers
```

#### ✅ Adding New API Endpoints

**Step 1: Add Types** (`lib/api/types.ts`)
```typescript
export interface Signal {
  id: string;
  symbol: string;
  direction: 'BULLISH' | 'BEARISH';
  confidence: number;
}

export interface CreateSignalDto {
  symbol: string;
  direction: string;
  reasoning?: string;
}
```

**Step 2: Create Service File** (`lib/api/signals.ts`)
```typescript
import { apiClient } from './client';
import { Signal, CreateSignalDto } from './types';

export async function getSignals(): Promise<Signal[]> {
  const response = await apiClient.get<Signal[]>('/api/v1/signals');
  return response.data;
}

export async function createSignal(data: CreateSignalDto): Promise<Signal> {
  const response = await apiClient.post<Signal>('/api/v1/signals', data);
  return response.data;
}
```

**Step 3: Export in Barrel** (`lib/api/index.ts`)
```typescript
export * from './signals';
```

**Step 4: Use in Components**
```typescript
import { getSignals } from '@/lib/api';

const signals = await getSignals();
```

#### 🎣 Creating Custom Hooks

**For Auto-Fetch on Mount:**
```typescript
// lib/hooks/useSignals.ts
import { useState, useEffect } from 'react';
import { getSignals } from '../api/signals';
import { Signal, ApiError } from '../api/types';

export function useSignals() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSignals = async () => {
    try {
      setLoading(true);
      const data = await getSignals();
      setSignals(data);
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSignals();
  }, []);

  return { signals, loading, error, refetch: fetchSignals };
}
```

**For Manual Operations (Forms):**
```typescript
import { useAsync } from '@/lib/hooks';
import { createSignal } from '@/lib/api';

const { execute: submitSignal, loading, error } = useAsync(createSignal);

await submitSignal({ symbol: 'XAU/USD', direction: 'BULLISH' });
```

#### ⚠️ Error Handling

**Client-Side (Automatic via Interceptor):**
- ✅ Token injection: Auto-adds `Authorization: Bearer {token}`
- ✅ Error transformation: Converts axios errors to `ApiError`
- ✅ Status code handling: 401, 403, 404, 422, 500
- ✅ Dev logging: Console logs in development mode

**Component-Level:**
```typescript
try {
  const data = await createJournalEntry(payload);
  alert('Success!');
} catch (error) {
  const apiError = error as ApiError;
  alert(`Error: ${apiError.message}`);
  // apiError.status - HTTP status code
  // apiError.details - Backend error details
}
```

#### 🔐 Authentication Flow

1. **Login:** Call `login(username, password)` from `lib/api/auth`
2. **Token Storage:** AuthContext stores token in localStorage
3. **Auto-Injection:** Request interceptor reads token and adds to headers
4. **401 Handling:** Response interceptor logs warnings (future: auto-logout)

**DO NOT:**
- ❌ Use `fetch()` directly
- ❌ Manually add `Authorization` headers (interceptor handles this)
- ❌ Access `localStorage` directly for tokens (use AuthContext)
- ❌ Create axios instances outside `lib/api/client.ts`

**Environment Variables:**
- `NEXT_PUBLIC_API_BASE_URL`: Set to `''` (empty) for Nginx routing, or `http://localhost:8000` for direct dev
## 🔑 Key Logic & Constraints (from PRD)
*   **Risk Management:** Strict **$10 max risk per trade**. Minimum lot **0.01**.
*   **Strategy:**
    *   **Macro Bias:** 4H/Daily Price vs EMA200.
    *   **Setup:** 4H/1H Fibo (50-61.8%) + SMC Order Block.
    *   **Trigger:** 15m Candle with high Body-to-Wick ratio.
*   **Status:** The project is evolving. While the PRD defines a strict MVP, the codebase includes "Future" features like the AI Analyst and Frontend, indicating active expansion.

## � Inspiration & Examples
*   **Gridbot AI Volatility Harvester:** Check `example/gridbot-ai-volatility-harvester` for frontend UI/UX inspiration (Vite + React).

## �📝 Common Commands
| Action | Command |
| :--- | :--- |
| **Start Full Stack** | `docker compose up --build` |
| **Start Backend Only** | `docker compose up api execution` |
| **Start Frontend Only** | `docker compose up frontend` |
| **Rebuild Specific** | `docker compose up --build <service_name>` |
| **Stop All** | `docker compose down` |
| **Deploy** | `./deploy.sh` |
| **Connect to DB** | `docker exec -it pgvector psql -U trader -d mtf_db` |
