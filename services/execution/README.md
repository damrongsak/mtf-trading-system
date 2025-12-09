# Execution Service

## Overview
The Execution Service is responsible for managing interactions with the OANDA trading platform. It acts as a bridge between the trading system's logic and the broker, handling account information retrieval, risk checks, and order execution.

## Key Features
- **Account Management**: Fetches real-time account details such as Net Asset Value (NAV), margin available, and open position/trade counts.
- **Order Execution**: Places market orders with integrated Stop Loss (SL) and Take Profit (TP) details.
- **Risk Management**: Provides a `/check` endpoint to validate trade parameters against pre-defined risk rules (e.g., maximum risk per trade, minimum lot size) before execution.
- **Traceability**: Tags orders with client-specific IDs (`trade_id`) for easy reconciliation with the system's database.

## Architecture
This service is built using **FastAPI** and utilizes the `oandapyV20` library for OANDA API communication.

### Directory Structure
```
services/execution/
├── app/
│   ├── adapters/
│   │   ├── oanda_account.py  # Adapter for Account-related API calls
│   │   └── oanda_order.py    # Adapter for Order-related API calls
│   ├── core/
│   │   └── config.py         # Configuration management (Environment variables)
│   ├── executor.py           # Risk calculation logic
│   └── main.py               # FastAPI application entry point and routes
├── Dockerfile                # Container definition
├── pyproject.toml            # Project dependencies (managed by uv)
└── README.md                 # Service documentation
```

## API Endpoints

### 1. Risk Check
*   **Endpoint**: `POST /check`
*   **Description**: Validates if a trade can be executed based on risk parameters.
*   **Request Body**:
    ```json
    {
      "risk_usd": 10.0,
      "sl_distance_usd": 50.0,
      "min_lot": 0.01
    }
    ```
*   **Response**:
    ```json
    {
      "can_execute": true,
      "lot": 0.2,
      "reason": "ok"
    }
    ```

### 2. Account Summary
*   **Endpoint**: `GET /account/summary`
*   **Description**: Retrieves current account metrics from OANDA.
*   **Response**:
    ```json
    {
      "balance": "10000.00",
      "NAV": "10000.00",
      "marginAvailable": "9900.00",
      "openTradeCount": 0,
      "openPositionCount": 0
    }
    ```

### 3. Place Order
*   **Endpoint**: `POST /orders`
*   **Description**: Places a market order on OANDA.
*   **Request Body**:
    ```json
    {
      "symbol": "XAU_USD",
      "units": 0.1,
      "sl_price": 1950.00,
      "tp_price": 2050.00,
      "trade_id": "unique-trade-id-123"
    }
    ```
*   **Response**:
    ```json
    {
      "id": "500",
      "instrument": "XAU_USD",
      "units": "0.1",
      "price": "2000.00",
      "time": "2023-10-27T10:00:00.000000000Z"
    }
    ```

## Configuration
The service requires the following environment variables (typically provided via `.env` file or Docker Compose):

*   `OANDA_API_KEY`: Your OANDA API access token.
*   `OANDA_ACCOUNT_ID`: Your OANDA account ID.
*   `OANDA_ENV`: Environment to connect to (`practice` or `live`).

## Development
This service uses `uv` for package management.

### Setup
1.  Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2.  Install dependencies:
    ```bash
    uv sync
    ```

### Running Locally
```bash
uv run uvicorn app.main:app --reload --port 8001
```

### Docker
Build and run via Docker Compose from the project root:
```bash
docker compose up --build execution
```
