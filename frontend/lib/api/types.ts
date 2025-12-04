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
    direction: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
    timeframe: string;
    confidence: number;
    timestamp: string;
    reasoning?: string;
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
}

export interface UserPreferences {
    id: string;
    user_id: string;
    default_fund_id: string | null;

    // Strategy Configuration
    strategy_type: StrategyType;
    asset_classes: AssetClass[];

    // Basic Risk Parameters
    max_risk_per_trade: number;
    default_lot_size: number;
    max_drawdown_threshold: number | null;

    // Advanced Risk Parameters
    max_portfolio_beta: number | null;
    gross_exposure_limit: number | null;
    net_exposure_limit: number | null;
    position_limit_single: number | null;
    position_limit_sector: number | null;

    // Trading Preferences
    preferred_timeframes: string[];
    default_symbol: string;
    session_preferences: string[] | null;
    supported_symbols: string[] | null;
}

export interface UpdatePreferencesDto {
    default_fund_id?: string | null;
    strategy_type?: StrategyType;
    asset_classes?: AssetClass[];
    max_risk_per_trade?: number;
    default_lot_size?: number;
    max_drawdown_threshold?: number | null;
    max_portfolio_beta?: number | null;
    gross_exposure_limit?: number | null;
    net_exposure_limit?: number | null;
    position_limit_single?: number | null;
    position_limit_sector?: number | null;
    preferred_timeframes?: string[];
    default_symbol?: string;
    session_preferences?: string[] | null;
    supported_symbols?: string[] | null;
}
