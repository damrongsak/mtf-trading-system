# Database Schema (ERD)

This document visualizes the data model defined in `specs/03_data_model.yaml`.

```mermaid
erDiagram
    %% Entities
    User {
        uuid id PK
        string username
        string email
        string password_hash
        boolean is_active
        boolean is_superuser
        string avatar_url
    }
    Fund {
        uuid id PK
        string name
        enum strategy_type
        decimal max_risk_per_trade
        decimal default_lot_size
        jsonb asset_classes
    }
    UserFund {
        uuid id PK
        uuid user_id FK
        uuid fund_id FK
        enum role
    }
    Strategy {
        uuid id PK
        uuid fund_id FK
        string name
        string template_id
        uuid config_id FK
        uuid broker_account_id FK
        jsonb config_json
        jsonb risk_settings
        boolean is_active
    }
    StrategyConfig {
        uuid id PK
        string name
        uuid author_id FK
        string logic_schema_version
        jsonb logic_blocks
        jsonb parameters
        jsonb timeframe_settings
        boolean is_public
    }
    StrategyValidation {
        uuid id PK
        uuid config_id FK
        integer robustness_score
        decimal sharpe_train
        decimal sharpe_test
        boolean is_passed
    }
    PortfolioAllocation {
        uuid id PK
        uuid fund_id FK
        uuid strategy_id FK
        decimal weight
        decimal volatility_target
    }
    MentalHandHistory {
        uuid id PK
        uuid user_id FK
        uuid journal_entry_id FK
        string pre_trade_emotion
        string correction_logic
    }
    DataSource {
        uuid id PK
        string name
        string type
        jsonb config_json
        jsonb schema_json
    }
    Candle {
        uuid id PK
        string symbol
        string timeframe
        datetime timestamp
        decimal open
        decimal high
        decimal low
        decimal close
        decimal volume
        boolean is_complete
        decimal ema_9_4h
        decimal ema_200_4h
        decimal ema_200_d
        decimal atr_14_15m
        decimal body_to_wick_ratio
    }
    BrokerAccount {
        uuid id PK
        uuid fund_id FK
        string broker_name
        string account_name
        string account_number
        jsonb credentials_encrypted
        boolean is_live
        jsonb supported_symbols
        jsonb risk_settings
    }
    Trade {
        uuid trade_id PK
        uuid strategy_run_id FK
        uuid broker_account_id FK
        string symbol
        string strategy_name
        datetime signal_timestamp
        enum status
        string rejection_reason
        enum direction
        decimal entry_price
        decimal sl_price
        decimal tp_price
        decimal lot_size
        decimal risk_usd
        decimal atr_pips
        decimal rr_ratio
        decimal pnl_usd
        decimal mae_usd
        decimal mfe_usd
        decimal exit_price
        datetime exit_timestamp
        jsonb metadata_json
    }
    StrategyRun {
        uuid run_id PK
        string strategy_name
        date start_date
        date end_date
        jsonb parameters_json
        decimal sharpe_ratio
        decimal max_drawdown
        decimal win_rate
        integer total_trades
        integer winning_trades
        integer losing_trades
        decimal total_pnl_usd
        decimal avg_win_usd
        decimal avg_loss_usd
        integer max_consecutive_wins
        integer max_consecutive_losses
        enum status
        text error_message
    }
    RiskRule {
        uuid rule_id PK
        string rule_name
        enum rule_type
        decimal threshold_value
        string threshold_unit
        boolean is_active
        text description
    }
    JournalEntry {
        uuid id PK
        uuid user_id FK
        string symbol
        enum direction
        decimal entry_price
        decimal exit_price
        decimal pnl_amount
        decimal pnl_r
        decimal risk_amount
        decimal stop_loss_price
        decimal take_profit_price
        string session
        integer context_score
        enum game_level
    }
    MentalState {
        uuid id PK
        uuid journal_entry_id FK
        integer greed_level
        integer fear_level
        integer tilt_level
        integer confidence_level
        integer discipline_level
    }
    TimelineEvent {
        uuid id PK
        uuid journal_entry_id FK
        string type
        text description
        datetime timestamp
        integer order_index
    }
    RootCauseAnalysis {
        uuid id PK
        uuid journal_entry_id FK
        text problem
        text why_exist
        text flaw
        text correction
        text logic
    }
    Transaction {
        uuid id PK
        uuid fund_id FK
        datetime transaction_date
        enum type
        decimal amount
        string currency
        string status
        string reference
        text description
    }
    SavedStrategy {
        uuid id PK
        uuid user_id FK
        string name
        text description
        text code
        jsonb parameters
        boolean is_public
    }
    UserPreferences {
        uuid id PK
        uuid user_id FK
        uuid default_fund_id FK
        jsonb preferred_timeframes
        string default_symbol
        jsonb session_preferences
    }
    BacktestConfig {
        uuid id PK
        uuid user_id FK
        string name
        string description
        jsonb config_json
    }
    BacktestHistory {
        uuid id PK
        uuid config_id FK
        uuid strategy_id FK
        jsonb execution_config
        string status
        jsonb metrics
        jsonb best_params
    }
    Deployment {
        uuid id PK
        uuid user_id FK
        uuid strategy_id FK
        string stock_symbol
        string timeframe
        enum status
        boolean is_live
        jsonb config_snapshot
        text last_error
        datetime started_at
        datetime stopped_at
        datetime last_signal_at
    }
    ChatSession {
        uuid id PK
        uuid user_id FK
        uuid strategy_id FK
        string title
    }
    ChatMessage {
        uuid id PK
        uuid session_id FK
        enum role
        text content
        jsonb context_snapshot
    }
    SignalLog {
        uuid id PK
        datetime timestamp
        string symbol
        string timeframe
        string direction
        string strategy_name
        uuid deployment_id FK
        decimal confidence
        decimal price
        text reason
        jsonb meta_data
    }

    %% Relationships
    User ||--o{ StrategyConfig : "authors"
    StrategyConfig ||--o{ Strategy : "configures"
    StrategyConfig ||--o{ StrategyValidation : "validated by"
    Fund ||--o{ PortfolioAllocation : "allocates"
    Strategy ||--o{ PortfolioAllocation : "receives"
    
    User ||--o{ UserFund : "has access"
    Fund ||--o{ UserFund : "has members"
    Fund ||--o{ Strategy : "runs"
    Fund ||--o{ BrokerAccount : "owns"
    Fund ||--o{ Transaction : "logs"
    
    BrokerAccount ||--o{ Strategy : "executes for"
    BrokerAccount ||--o{ Trade : "executes"
    
    StrategyRun ||--o{ Trade : "generates"
    
    User ||--o{ JournalEntry : "records"
    JournalEntry ||--o| MentalState : "has"
    JournalEntry ||--o{ TimelineEvent : "includes"
    JournalEntry ||--o{ RootCauseAnalysis : "analyzes"
    
    User ||--|| UserPreferences : "configures"
    UserPreferences }o--|| Fund : "defaults to"
    
    User ||--o{ SavedStrategy : "authors"
    User ||--o{ BacktestConfig : "creates"
    User ||--o{ Deployment : "manages"
    User ||--o{ ChatSession : "chats in"
    
    SavedStrategy ||--o{ Deployment : "instantiates"
    SavedStrategy ||--o{ ChatSession : "discusses"
    SavedStrategy ||--o{ BacktestHistory : "tested in"
    
    BacktestConfig ||--o{ BacktestHistory : "history"
    
    ChatSession ||--o{ ChatMessage : "contains"
    
    Deployment ||--o{ SignalLog : "generates"
```

### strategy_configs
*Standardized Strategy Logic (The Blueprint)*

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| id | UUID | PK | |
| name | VARCHAR(100) | NN | |
| logic_blocks | JSONB | NN | Trend, Structure, Momentum blocks |
| parameters | JSONB | NN | Global params |
| timeframe_settings| JSONB | NN | e.g. {"exec": "15m"} |

### strategy_validations
*Walk-Forward Analysis Results*

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| id | UUID | PK | |
| config_id | UUID | FK | |
| robustness_score | INTEGER | NN | 0-100 Score |
| is_passed | BOOLEAN | | Validated status |

### portfolio_allocations
*Risk Parity Weightings*

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| id | UUID | PK | |
| fund_id | UUID | FK | |
| strategy_id | UUID | FK | |
| weight | DECIMAL | NN | 0.0 - 1.0 |
| volatility_target| DECIMAL | | Annualized Vol Target |

### mental_hand_histories
*Psychological Reflections*

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| id | UUID | PK | |
| user_id | UUID | FK | |
| journal_entry_id | UUID | FK | |
| pre_trade_emotion| VARCHAR | | |
| correction_logic | TEXT | | CBT Logic |
