# MTF Trading System - Data Model Specification (v2.0 - Olympus)
# Last Updated: 2025-12-24
# Status: Draft (Expansion for Quant Platform)

# I've generated the updated 03_data_model.yaml. This aligns your data layer with the "Olympus" spec, laying the groundwork for:
# AI Coach: via MentalHandHistory
# Marketplace: via StrategyConfig & StrategyValidation
# Risk Citadel: via PortfolioAllocation

entities:
  User:
    description: "System users (Traders, Quants, Admins)"
    table_name: "users"
    fields:
      - name: id
        type: uuid
        primary_key: true
      - name: username
        type: string
        required: true
        unique: true
        max_length: 50
      - name: email
        type: string
        required: true
        unique: true
        max_length: 100
      - name: password_hash
        type: string
        required: true
      - name: is_active
        type: boolean
        default: true
      - name: is_superuser
        type: boolean
        default: false
      - name: created_at
        type: datetime
        default: "now()"
      - name: avatar_url
        type: string
        nullable: true
        description: "URL to user profile picture"
      # Community Features
      - name: reputation_score
        type: integer
        default: 0
        description: "Gamified score based on strategy robustness and community contribution"
      - name: is_verified_quant
        type: boolean
        default: false
        description: "Badge for users who have passed the Walk-Forward Gauntlet"

  Fund:
    description: "Quant Fund or Trading Group"
    table_name: "funds"
    fields:
      - name: id
        type: uuid
        primary_key: true
      - name: name
        type: string
        required: true
        max_length: 100
      - name: description
        type: text
        nullable: true
      - name: created_at
        type: datetime
        default: "now()"

  UserFund:
    description: "Many-to-Many relationship between Users and Funds with Roles"
    table_name: "user_funds"
    indexes:
      - fields: ["user_id", "fund_id"]
        unique: true
    fields:
      - name: id
        type: uuid
        primary_key: true
      - name: user_id
        type: uuid
        foreign_key: "users.id"
        required: true
      - name: fund_id
        type: uuid
        foreign_key: "funds.id"
        required: true
      - name: role
        type: enum
        enum_values: ["OWNER", "MANAGER", "TRADER", "VIEWER"]
        required: true

  # --- Module 1: The Strategy Foundry ---
  StrategyConfig:
    description: "Standardized Configuration for Strategy Logic (Portable/Shareable)"
    table_name: "strategy_configs"
    fields:
      - name: id
        type: uuid
        primary_key: true
      - name: author_id
        type: uuid
        foreign_key: "users.id"
        required: true
      - name: name
        type: string
        required: true
        max_length: 100
      - name: version
        type: string
        required: true
        default: "1.0.0"
      - name: description
        type: text
        nullable: true
      - name: logic_modules
        type: jsonb
        required: true
        description: "Array of Kaufman modules used (e.g., [{'type': 'Trend', 'params': {...}}])"
      - name: risk_params
        type: jsonb
        required: true
        description: "Default risk settings (e.g., ATR multiplier, Max Drawdown)"
      - name: is_public
        type: boolean
        default: false
        description: "If true, visible in the Alpha Marketplace (requires validation)"
      - name: created_at
        type: datetime
        default: "now()"

  # --- Module 2: The Proving Ground ---
  StrategyValidation:
    description: "Result of the Walk-Forward Validation Gauntlet"
    table_name: "strategy_validations"
    indexes:
      - fields: ["config_id"]
    fields:
      - name: id
        type: uuid
        primary_key: true
      - name: config_id
        type: uuid
        foreign_key: "strategy_configs.id"
        required: true
      - name: robustness_score
        type: integer
        required: true
        description: "0-100 Score based on AI-Trader 2025 metrics"
      - name: walk_forward_result
        type: jsonb
        required: true
        description: "Detailed metrics for Train vs Test periods (Sharpe, Drawdown)"
      - name: is_passed
        type: boolean
        default: false
        description: "True if robustness_score > 80 and deviation < 20%"
      - name: validated_at
        type: datetime
        default: "now()"

  # --- Module 3: The Risk Citadel ---
  PortfolioAllocation:
    description: "Risk Parity Settings for a Fund"
    table_name: "portfolio_allocations"
    fields:
      - name: id
        type: uuid
        primary_key: true
      - name: fund_id
        type: uuid
        foreign_key: "funds.id"
        required: true
      - name: strategy_weights
        type: jsonb
        required: true
        description: "Target weight for each active strategy (e.g., {'strat_id_1': 0.4, 'strat_id_2': 0.6})"
      - name: algorithm
        type: enum
        enum_values: ["EQUAL_WEIGHT", "RISK_PARITY", "MINIMAX"]
        default: "RISK_PARITY"
      - name: rebalance_frequency
        type: string
        default: "WEEKLY"
      - name: updated_at
        type: datetime
        default: "now()"

  Strategy:
    description: "Active Instance of a Strategy Config"
    table_name: "strategies"
    fields:
      - name: id
        type: uuid
        primary_key: true
      - name: fund_id
        type: uuid
        foreign_key: "funds.id"
        required: true
      - name: config_id
        type: uuid
        foreign_key: "strategy_configs.id"
        nullable: true
        description: "Link to the standardized config (if applicable)"
      - name: name
        type: string
        required: true
        max_length: 100
      - name: broker_account_id
        type: uuid
        foreign_key: "broker_accounts.id"
        required: true
      - name: instance_params
        type: jsonb
        required: true
        description: "Overrides for the config parameters (specific to this instance)"
      - name: is_active
        type: boolean
        default: false
      - name: created_at
        type: datetime
        default: "now()"

  # --- Module 5: The AI Coach ---
  JournalEntry:
    description: "Trading Journal Entry with Mental Hand History"
    table_name: "journal_entries"
    indexes:
      - fields: ["user_id", "created_at"]
      - fields: ["game_level"]
    fields:
      - name: id
        type: uuid
        primary_key: true
      - name: user_id
        type: uuid
        foreign_key: "users.id"
        required: true
      - name: symbol
        type: string
        required: true
        max_length: 20
      - name: direction
        type: enum
        enum_values: ["LONG", "SHORT"]
        required: true
      - name: entry_price
        type: decimal
        precision: 18
        scale: 8
        nullable: true
      - name: exit_price
        type: decimal
        precision: 18
        scale: 8
        nullable: true
      - name: pnl_amount
        type: decimal
        precision: 10
        scale: 2
        nullable: true
      - name: pnl_r
        type: decimal
        precision: 5
        scale: 2
        nullable: true
      - name: risk_amount
        type: decimal
        precision: 10
        scale: 2
        nullable: true
      - name: session
        type: string
        max_length: 20
        nullable: true
      - name: context_score
        type: integer
        nullable: true
      - name: game_level
        type: enum
        enum_values: ["A_GAME", "B_GAME", "C_GAME"]
        nullable: true
        description: "Performance quality categorization (Tendler)"
      - name: created_at
        type: datetime
        default: "now()"
      - name: updated_at
        type: datetime
        default: "now()"
        on_update: "now()"

  MentalHandHistory:
    description: "Structured Mental Correction (Tendler Method)"
    table_name: "mental_hand_histories"
    indexes:
      - fields: ["journal_entry_id"]
    fields:
      - name: id
        type: uuid
        primary_key: true
      - name: journal_entry_id
        type: uuid
        foreign_key: "journal_entries.id"
        required: true
      - name: trigger_event
        type: text
        required: true
        description: "What happened? (e.g., Price hit SL)"
      - name: flawed_thought
        type: text
        required: true
        description: "What did you think? (e.g., They are hunting me)"
      - name: emotion
        type: string
        required: true
        description: "What did you feel? (e.g., Anger)"
      - name: intensity
        type: integer
        required: true
        description: "Intensity 1-10"
      - name: reality_correction
        type: text
        required: true
        description: "The logic that corrects the flaw"
      - name: created_at
        type: datetime
        default: "now()"

  # --- Existing Legacy Entities (Retained) ---
  DataSource:
    table_name: "data_sources"
    fields:
      - name: id
        type: uuid
        primary_key: true
      - name: name
        type: string
        required: true
      - name: type
        type: string
        required: true
      - name: config_json
        type: jsonb
        required: true
      - name: schema_json
        type: jsonb
        nullable: true
      - name: is_active
        type: boolean
        default: true

  Candle:
    table_name: "candles"
    indexes:
      - fields: ["symbol", "timeframe", "timestamp"]
        unique: true
      - fields: ["timestamp"]
    fields:
      - name: id
        type: uuid
        primary_key: true
      - name: symbol
        type: string
        required: true
      - name: timeframe
        type: string
        required: true
      - name: timestamp
        type: datetime
        required: true
      - name: open
        type: decimal
        required: true
      - name: high
        type: decimal
        required: true
      - name: low
        type: decimal
        required: true
      - name: close
        type: decimal
        required: true
      - name: volume
        type: decimal
        required: true
      - name: is_complete
        type: boolean
        default: true
      - name: created_at
        type: datetime
        default: "now()"
      - name: updated_at
        type: datetime
        default: "now()"

  BrokerAccount:
    table_name: "broker_accounts"
    fields:
      - name: id
        type: uuid
        primary_key: true
      - name: user_id
        type: uuid
        foreign_key: "users.id"
        required: true
      - name: broker_name
        type: string
        required: true
      - name: account_name
        type: string
        required: true
      - name: account_number
        type: string
        nullable: true
      - name: credentials_encrypted
        type: jsonb
        required: true
      - name: is_active
        type: boolean
        default: true
      - name: is_live
        type: boolean
        default: false
      - name: created_at
        type: datetime
        default: "now()"
      - name: updated_at
        type: datetime
        default: "now()"

  Trade:
    table_name: "trades"
    fields:
      - name: trade_id
        type: uuid
        primary_key: true
      - name: strategy_run_id
        type: uuid
        nullable: true
      - name: broker_account_id
        type: uuid
        nullable: true
        foreign_key: "broker_accounts.id"
      - name: symbol
        type: string
        required: true
      - name: strategy_name
        type: string
        required: true
      - name: signal_timestamp
        type: datetime
        required: true
      - name: status
        type: enum
        enum_values: ["OPEN", "CLOSED", "REJECTED"]
        required: true
      - name: rejection_reason
        type: string
        nullable: true
      - name: direction
        type: enum
        enum_values: ["LONG", "SHORT"]
        required: true
      - name: entry_price
        type: decimal
        required: true
      - name: sl_price
        type: decimal
        required: true
      - name: tp_price
        type: decimal
        required: true
      - name: lot_size
        type: decimal
        required: true
      - name: risk_usd
        type: decimal
        required: true
      - name: atr_pips
        type: decimal
        nullable: true
      - name: rr_ratio
        type: decimal
        nullable: true
      - name: pnl_usd
        type: decimal
        nullable: true
      - name: exit_price
        type: decimal
        nullable: true
      - name: exit_timestamp
        type: datetime
        nullable: true
      - name: created_at
        type: datetime
        default: "now()"
      - name: updated_at
        type: datetime
        default: "now()"

  StrategyRun:
    table_name: "strategy_runs"
    fields:
      - name: run_id
        type: uuid
        primary_key: true
      - name: strategy_name
        type: string
        required: true
      - name: start_date
        type: date
        required: true
      - name: end_date
        type: date
        required: true
      - name: parameters_json
        type: jsonb
        required: true
      - name: sharpe_ratio
        type: decimal
        nullable: true
      - name: max_drawdown
        type: decimal
        nullable: true
      - name: win_rate
        type: decimal
        nullable: true
      - name: total_trades
        type: integer
        nullable: true
      - name: status
        type: enum
        enum_values: ["RUNNING", "COMPLETED", "FAILED"]
        default: "RUNNING"
      - name: created_at
        type: datetime
        default: "now()"
      - name: completed_at
        type: datetime
        nullable: true

  RiskRule:
    table_name: "risk_rules"
    fields:
      - name: rule_id
        type: uuid
        primary_key: true
      - name: rule_name
        type: string
        required: true
      - name: rule_type
        type: enum
        enum_values: ["RISK_CAP", "LOT_SIZE", "VOLATILITY", "RR_RATIO"]
        required: true
      - name: threshold_value
        type: decimal
        required: true
      - name: threshold_unit
        type: string
        required: true
      - name: is_active
        type: boolean
        default: true
      - name: created_at
        type: datetime
        default: "now()"
      - name: updated_at
        type: datetime
        default: "now()"

  Transaction:
    table_name: "transactions"
    fields:
      - name: id
        type: uuid
        primary_key: true
      - name: fund_id
        type: uuid
        foreign_key: "funds.id"
        required: true
      - name: transaction_date
        type: datetime
        required: true
      - name: type
        type: enum
        enum_values: ["DEPOSIT", "WITHDRAWAL"]
        required: true
      - name: amount
        type: decimal
        required: true
      - name: currency
        type: string
        default: "USD"
        required: true
      - name: status
        type: string
        default: "COMPLETED"
      - name: created_at
        type: datetime
        default: "now()"
      - name: updated_at
        type: datetime
        default: "now()"

  UserPreferences:
    table_name: "user_preferences"
    fields:
      - name: id
        type: uuid
        primary_key: true
      - name: user_id
        type: uuid
        foreign_key: "users.id"
        required: true
      - name: default_fund_id
        type: uuid
        foreign_key: "funds.id"
        nullable: true
      - name: strategy_type
        type: enum
        enum_values: ["MTF_SMC_BASIC", "LONG_SHORT_EQUITY", "MACRO_TACTICAL", "MULTI_ASSET"]
        default: "MTF_SMC_BASIC"
      - name: max_risk_per_trade
        type: decimal
        default: 10.00
      - name: default_lot_size
        type: decimal
        default: 0.01
      - name: created_at
        type: datetime
        default: "now()"
      - name: updated_at
        type: datetime
        default: "now()"

relationships:
  - from: StrategyValidation
    to: StrategyConfig
    type: many_to_one
    foreign_key: config_id

  - from: MentalHandHistory
    to: JournalEntry
    type: many_to_one
    foreign_key: journal_entry_id

  - from: PortfolioAllocation
    to: Fund
    type: many_to_one
    foreign_key: fund_id

validation_rules:
  Trade:
    - field: risk_usd
      rule: "risk_usd <= 10.00"
      error: "Risk per trade must not exceed $10 (F2.2)"
    - field: lot_size
      rule: "lot_size >= 0.01"
      error: "Lot size must be at least 0.01 (F2.3)"

  StrategyValidation:
    - field: is_passed
      rule: "is_passed == (robustness_score > 80)"
      error: "Strategy requires score > 80 to pass validation"