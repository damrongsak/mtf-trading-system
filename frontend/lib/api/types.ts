// ========================================
// Backend Standard Response Types
// ========================================

export enum ResponseStatus {
    SUCCESS = 'success',
    ERROR = 'error',
    FAIL = 'fail',
}

export type ErrorCode =
    // Authentication & Authorization (1xxx)
    | 'AUTH_1001' // UNAUTHORIZED
    | 'AUTH_1002' // FORBIDDEN
    | 'AUTH_1003' // TOKEN_EXPIRED
    | 'AUTH_1004' // TOKEN_INVALID
    | 'AUTH_1005' // INSUFFICIENT_PERMISSIONS
    // Validation Errors (2xxx)
    | 'VAL_2001' // VALIDATION_ERROR
    | 'VAL_2002' // REQUIRED_FIELD
    | 'VAL_2003' // INVALID_FORMAT
    | 'VAL_2004' // INVALID_EMAIL
    | 'VAL_2005' // INVALID_PHONE
    | 'VAL_2006' // INVALID_DATE
    | 'VAL_2007' // OUT_OF_RANGE
    // Resource Errors (3xxx)
    | 'RES_3001' // NOT_FOUND
    | 'RES_3002' // ALREADY_EXISTS
    | 'RES_3003' // CONFLICT
    // Business Logic Errors (4xxx)
    | 'BIZ_4001' // INSUFFICIENT_BALANCE
    | 'BIZ_4002' // OPERATION_NOT_ALLOWED
    | 'BIZ_4003' // QUOTA_EXCEEDED
    | 'BIZ_4004' // INVALID_STATE
    // Rate Limiting (5xxx)
    | 'RATE_5001' // RATE_LIMIT_EXCEEDED
    | 'RATE_5002' // TOO_MANY_REQUESTS
    // Server Errors (9xxx)
    | 'SRV_9001' // INTERNAL_ERROR
    | 'SRV_9002' // SERVICE_UNAVAILABLE
    | 'SRV_9003' // DATABASE_ERROR
    | 'SRV_9004'; // EXTERNAL_SERVICE_ERROR

export interface ErrorDetail {
    field?: string;
    message: string;
    code?: ErrorCode;
}

export interface Meta {
    page?: number;
    per_page?: number;
    total?: number;
    total_pages?: number;
    [key: string]: unknown; // Allow additional metadata
}

export interface AuthTokens {
    access_token: string;
    refresh_token?: string;
    token_type: string;
    expires_in: number;
    expires_at: string;
}

export interface RateLimitInfo {
    limit: number;
    remaining: number;
    reset: string;
    reset_in_seconds: number;
}

export interface APIResponse<T> {
    status: ResponseStatus;
    data?: T;
    message?: string;
    errors?: ErrorDetail[];
    meta?: Meta;
    auth?: AuthTokens;
    rate_limit?: RateLimitInfo;
    timestamp: string;
}

export interface PaginatedResponse<T> {
    status: ResponseStatus;
    data: T[];
    message?: string;
    meta: Meta;
    rate_limit?: RateLimitInfo;
    timestamp: string;
}

// ========================================
// Auth Types
// ========================================

export interface UserResponse {
    id: string;
    username: string;
    email: string;
    is_active: boolean;
    avatar_url?: string;
}

export interface User {
    id?: string;
    username: string;
    email: string;
    is_active: boolean;
}

export interface LoginResult {
    user: UserResponse;
    auth: AuthTokens;
}

export interface UserUpdateDto {
    username?: string;
    email?: string;
}

export interface PasswordChangeDto {
    old_password: string;
    new_password: string;
}

// Journal Types
export interface JournalEntry {
    id: string;
    user_id: string;
    symbol: string;
    direction: 'LONG' | 'SHORT';
    entry_price?: number;
    exit_price?: number;
    pnl_amount?: number;
    pnl_r?: number;
    risk_amount?: number;
    stop_loss_price?: number;
    take_profit_price?: number;
    session?: string;
    context_score?: number;
    game_level?: 'A_GAME' | 'B_GAME' | 'C_GAME';
    created_at: string;
    updated_at: string;
}

export interface JournalStatsResponse {
    total_trades: number;
    win_rate: number;
    profit_factor: number;
    net_pnl: number;
    avg_win: number;
    avg_loss: number;
    max_drawdown: number;
}

export interface EquityCurvePoint {
    timestamp: string;
    balance: number;
    pnl: number;
}

export interface PatternItem {
    name: string;
    count: number;
    avg_pnl: number;
}

export interface PatternAnalysisResponse {
    game_levels: PatternItem[];
    top_emotions: PatternItem[];
    top_mistakes: PatternItem[];
}

export interface CreateJournalEntryDto {
    symbol: string;
    direction: string;
    session?: string | null;
    entry_price?: number | null;
    exit_price?: number | null;
    pnl_amount?: number | null;
    stop_loss_price?: number | null;
    take_profit_price?: number | null;
    risk_amount?: number | null;
    context_score: number;
    game_level?: string | null;
    mental_state: MentalState;
    timeline_events: TimelineEvent[];
    root_cause: RootCauseAnalysis;
}

export interface MentalState {
    greed_level: number;
    fear_level: number;
    tilt_level: number;
    confidence_level: number;
    discipline_level: number;
}

export interface TimelineEvent {
    type: string;
    description: string;
    order_index: number;
    timestamp?: string;
    event?: string;
    emotion?: string;
}

export interface RootCauseAnalysis {
    problem?: string | null;
    why_exist?: string | null;
    flaw?: string | null;
    correction?: string | null;
    logic?: string | null;
}

// Signal Types
export interface Signal {
    symbol: string;
    direction: 'BULLISH' | 'BEARISH' | 'NEUTRAL' | 'LONG' | 'SHORT';
    timeframe: string;
    confidence?: number;
    timestamp: string;
    reason?: string;
    reasoning?: string; // Legacy/Compability
    entry_price?: number;
    sl_price?: number;
    tp_price?: number;
}

// ========================================
// Signal Types
// ========================================

// Dashboard Types
export interface DashboardStats {
    total_pnl: number;
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: number;
    open_positions: number;
    avg_win: number;
    avg_loss: number;
}

export interface RecentSignal {
    id: string;
    symbol: string;
    direction: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
    confidence: number;
    timeframe: string;
    timestamp: string;
    entry_price?: number;
    sl_price?: number;
    tp_price?: number;
    reason?: string;
}

// ========================================
// Settings & Funds Types
// ========================================

export type StrategyType = 'MTF_SMC_BASIC' | 'LONG_SHORT_EQUITY' | 'MACRO_TACTICAL' | 'MULTI_ASSET';
export type AssetClass = 'EQUITY' | 'FX' | 'COMMODITIES' | 'FIXED_INCOME';

export interface Fund {
    id: string;
    name: string;
    description: string | null;
    role: string | null;

    // Risk Settings
    strategy_type: StrategyType;
    asset_classes: AssetClass[];
    max_risk_per_trade: number;
    default_lot_size: number;
    max_drawdown_threshold: number | null;
    max_portfolio_beta: number | null;
    gross_exposure_limit: number | null;
    net_exposure_limit: number | null;
    position_limit_single: number | null;
    position_limit_sector: number | null;
}

export interface UserPreferences {
    id: string;
    user_id: string;
    default_fund_id: string | null;

    // Trading Preferences
    preferred_timeframes: string[];
    default_symbol: string;
    session_preferences: string[] | null;
}
preferred_timeframes: string[];
default_symbol: string;
session_preferences: string[] | null;
supported_symbols: string[] | null;
}

export interface UpdatePreferencesDto {
    default_fund_id?: string | null;
    preferred_timeframes?: string[];
    default_symbol?: string;
    session_preferences?: string[] | null;
}
default_symbol ?: string;
session_preferences ?: string[] | null;
supported_symbols ?: string[] | null;
}

// ========================================
// Transaction Types
// ========================================

export enum TransactionType {
    DEPOSIT = 'DEPOSIT',
    WITHDRAWAL = 'WITHDRAWAL',
}

export interface Transaction {
    id: string;
    fund_id: string;
    transaction_date: string;
    type: TransactionType;
    amount: number;
    currency: string;
    status: string;
    reference?: string | null;
    description?: string | null;
    payment_method?: string | null;
    trading_account?: string | null;
    created_at: string;
    updated_at: string;
}

export interface CreateTransactionDto {
    fund_id: string;
    transaction_date: string;
    type: TransactionType;
    amount: number;
    currency?: string;
    status?: string;
    reference?: string;
    description?: string;
    payment_method?: string;
    trading_account?: string;
}

export interface BalanceResponse {
    balance: number;
    currency: string;
}

// ========================================
// Simulation Lab Types
// ========================================

export interface MarketRegime {
    trend: 'NO_TREND' | 'UPTREND' | 'DOWNTREND';
    volatility: number; // 1-10
    noise: 'GAUSSIAN' | 'FAT_TAIL';
}

export interface GridConfig {
    step_size: number;
    grid_levels: number;
    initial_lot: number;
    use_compound: boolean;
    stop_loss_pct: number;
}

export interface SimulationConfig {
    regime: MarketRegime;
    grid: GridConfig;
    iterations: number; // Monte Carlo runs
}

export interface SimulationResult {
    id: string;
    config: SimulationConfig;
    metrics: {
        total_pnl: number;
        win_rate: number;
        max_drawdown: number;
        sharpe_ratio: number;
        profit_factor: number;
    };
    equity_curve: { timestamp: string; value: number }[];
    status: 'COMPLETED' | 'FAILED' | 'RUNNING';
    created_at: string;
}

// ========================================
// Backtest Types
// ========================================

export interface ParameterRange {
    start: number;
    stop: number;
    step: number;
}

export interface OptimizationConfig {
    method: 'GRID' | 'RANDOM' | 'BAYESIAN';
    target_metric: string;
    max_iterations?: number;
    early_stopping_rounds?: number;
    param_grid: Record<string, ParameterRange | { values: unknown[] } | unknown[]>;
}

export interface BacktestRequest {
    symbol: string;
    timeframe: string;
    strategy_params?: Record<string, unknown>;
    start_date: string;
    end_date: string;
    initial_capital: number;
    fees?: number;
    slippage?: number;
    size?: number;
    size_type?: 'amount' | 'value' | 'percent';

    // Profile References
    strategy_id?: string;
    fund_id?: string;
    trading_config_id?: string;

    // Optimization
    optimization?: OptimizationConfig;
}

export interface BacktestTrade {
    entry_time: string;
    exit_time: string;
    direction: 'LONG' | 'SHORT';
    entry_price: number;
    exit_price: number;
    pnl: number;
    pnl_percent: number;
    size: number;
}

export interface BacktestMetrics {
    total_return: number;
    total_return_percent: number;
    max_drawdown: number;
    max_drawdown_percent: number;
    win_rate: number;
    sharpe_ratio?: number;
    benchmark_return?: number;
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    candle_count?: number;
}

export interface OptimizationResult {
    params: Record<string, unknown>;
    metrics: BacktestMetrics;
}

export interface OptimizationResponse {
    results: OptimizationResult[];
}



export interface BacktestConfig {
    id: string;
    name: string;
    description?: string;
    config: BacktestRequest;
    created_at: string;
}

export interface BacktestHistorySummary {
    id: string;
    status: string;
    created_at: string;
    metrics?: BacktestMetrics;
    best_params?: Record<string, unknown>;
    execution_config: BacktestRequest;
}

export interface BacktestResponse {
    id: string;
    status: string;
    metrics: BacktestMetrics;
    trades: BacktestTrade[];
    equity_curve?: { timestamp: string; value: number }[];
    best_params?: Record<string, unknown>;
    all_results?: unknown[];
    plot_json?: string;
    created_at?: string;
}

export interface PriceUpdate {
    type: string;
    instrument: string;
    time: string;
    bid: number;
    ask: number;
    status: string;
}

// ========================================
// Broker Account Types
// ========================================

export interface BrokerAccount {
    id: string;
    fund_id: string;
    broker_name: string;
    account_name: string;
    account_number?: string;
    is_active: boolean;
    is_live: boolean;
    created_at: string;
    supported_symbols?: string[];
    risk_settings?: Record<string, unknown>;
}

export interface BrokerAccountCreate {
    fund_id?: string;
    broker_name: string;
    account_name: string;
    account_number?: string;
    credentials: Record<string, unknown>;
    supported_symbols?: string[];
    risk_settings?: Record<string, unknown>;
    is_live: boolean;
}

export interface BrokerAccountUpdate {
    account_name?: string;
    account_number?: string;
    credentials?: Record<string, unknown>;
    supported_symbols?: string[];
    risk_settings?: Record<string, unknown>;
    is_active?: boolean;
    is_live?: boolean;
}

// ========================================
// Strategy Types
// ========================================

export interface BaseStrategyConfig extends Record<string, unknown> {
    symbol?: string;
    timeframe?: string;
}

export interface StrategyResponse {
    id: string;
    name: string;
    // type: string; // Deprecated
    template_id: string;
    broker_account_id?: string;
    config_json: BaseStrategyConfig; // Parameter overrides
    risk_settings: Record<string, unknown> & { max_risk_usd?: number };
    is_active: boolean;
    custom_code?: string;
}

export interface StrategyCreate {
    name: string;
    fund_id: string;
    template_id: string;
    broker_account_id: string;
    config_json: Record<string, unknown>;
    risk_settings: Record<string, unknown>;
    custom_code?: string;
}

export interface StrategyBacktestRequest {
    code: string;
    symbol: string;
    timeframe: string;
    start_date?: string;
    end_date?: string;
    initial_capital?: number;
    fees?: number;
    slippage?: number;
    size?: number;
    size_type?: 'amount' | 'value' | 'percent';
    optimization?: OptimizationConfig;
    strategy_id?: string;
}

export interface StrategyBacktestResponse {
    logs: string[];
    metrics?: BacktestMetrics;
    trades?: BacktestTrade[];
}

export interface LogicTemplate {
    id: string;
    name: string;
    description: string;
    default_config: Record<string, unknown>;
    default_risk_settings: Record<string, unknown>;
}
// ========================================
// Saved Strategy (Library) Types
// ========================================

export interface SavedStrategy {
    id: string;
    user_id: string;
    name: string;
    description?: string;
    code: string;
    parameters: Record<string, unknown>;
    last_results?: {
        metrics: unknown;
        plot_json: string;
        trades?: BacktestTrade[];
    };
    last_optimization_result?: OptimizationResult[];
    last_simulation_result?: MonteCarloResponse;
    is_public: boolean;
    created_at: string;
    updated_at: string;
}

export interface SavedStrategyCreate {
    name: string;
    description?: string;
    code: string;
    parameters?: Record<string, unknown>;
    last_results?: unknown;
    is_public?: boolean;
}

export interface SavedStrategyUpdate {
    name?: string;
    description?: string;
    code?: string;
    parameters?: Record<string, unknown>;
    last_results?: unknown;
    is_public?: boolean;
}

// ========================================
// Monte Carlo Types
// ========================================

export interface SensitivityMetrics {
    p95: number;
    median: number;
    worst: number;
    best?: number;
}

export interface MonteCarloResponse {
    iterations: number;
    max_drawdown: SensitivityMetrics;
    total_return: SensitivityMetrics;
    sharpe_ratio: SensitivityMetrics;
    ruin_probability: number;
    equity_curves?: number[][];
}

export interface MonteCarloRequest {
    trades: BacktestTrade[];
    iterations?: number;
    strategy_id?: string;
}

export interface Deployment {
    id: string;
    strategy_id: string;
    stock_symbol: string;
    timeframe: string;
    status: 'ACTIVE' | 'STOPPED' | 'ERROR' | 'STARTING' | 'STOPPING';
    is_live: boolean;
    started_at: string;
    stopped_at?: string;
    last_error?: string;
    config_snapshot: Record<string, unknown>;
}

export interface DeploymentCreate {
    strategy_id: string;
    stock_symbol: string;
    timeframe: string;
    config_snapshot: Record<string, unknown>;
    is_live: boolean;
}

// ========================================
// AI Chat Types
// ========================================

export interface ChatSession {
    id: string;
    user_id: string;
    strategy_id?: string;
    title: string;
    created_at: string;
    updated_at: string;
}

export interface ChatMessage {
    id: string;
    session_id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    context_snapshot?: Record<string, unknown>;
    created_at: string;
}

export interface CreateChatSessionDto {
    strategy_id?: string;
    initial_message?: string;
}

export interface CreateChatMessageDto {
    content: string;
    context_snapshot?: {
        strategy_code?: string;
        market_data?: Record<string, unknown>;
        image_b64?: string;
        [key: string]: unknown;
    };
}
