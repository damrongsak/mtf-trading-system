# Olympus User Registration & Onboarding Guide

Welcome to **MTF Olympus**, your Wealth Operating System. This guide outlines the steps to register a new user and configure a broker account, specifically for **OANDA** test users.

## 🚀 1. User Registration

To register a new user on the platform, follow the standard authentication flow:

1.  **Access the Dashboard**: Navigate to `http://localhost:3000`.
2.  **Sign Up**: Enter your details (Username, Email, Password).
    *   *Example Test User*: `trader2` / `password123`.
3.  **Authentication**: The system uses JWT-based authentication. Upon login, you will receive an access token.

## 🏦 2. Setting Up a Broker (OANDA)

Once registered, you need to link your OANDA account to start trading XAU/USD or EUR_USD.

1.  **Navigate to Broker Settings**: Go to the "Accounts" or "Broker" section in the dashboard.
2.  **Add New Broker**:
    *   **Broker**: Select `OANDA`.
    *   **Account Name**: Give your account a nickname (e.g., "OANDA Test Alpha").
    *   **Environment**: Choose `Practice` (for demo) or `Live`.
3.  **Enter Credentials**:
    *   **API Key**: Your OANDA v20 API Token.
    *   **Account ID**: Your OANDA Account Number (e.g., `101-001-XXXXXXX-001`).
4.  **Encryption Policy**: All credentials are encrypted using **AES-256-GCM** before being stored in the database.

## 📈 3. Configuring Symbols

The system currently supports the following symbols for OANDA:
*   **XAU/USD** (Gold)
*   **EUR/USD** (Euro/Dollar)

These must be enabled in your **Fund** settings to allow the strategy to generate signals.

## 🛡️ 4. Risk Management Setup

Every broker account must be linked to a **Fund**.
1.  **Create a Fund**: Define your strategy type (e.g., `MTF_SMC_BASIC`).
2.  **Set Constraints**:
    *   **Max Risk per Trade**: E.g., $10.
    *   **Default Lot Size**: E.g., 0.01.
    *   **Risk Percentage**: E.g., 1% of NAV.

## 🛠️ 5. Troubleshooting

*   **Connection Error**: Verify your API Key and Account ID. Ensure the OANDA server status is `Online`.
*   **Symbol Missing**: Check if the symbol is supported by your account type (e.g., Hebding vs Non-Hedging).
*   **Signal Rejected**: Check the System Drift Monitor for risk violations.

---
*Created by Antigravity AI Agent*
