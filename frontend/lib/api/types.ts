// API Response Types
export interface ApiError {
    message: string;
    status?: number;
    details?: unknown;
}

// Auth Types
export interface LoginResponse {
    access_token: string;
    token_type: string;
}

export interface User {
    username: string;
    email: string;
    is_active: boolean;
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

// Pagination
export interface PaginatedResponse<T> {
    data: T[];
    total: number;
    page: number;
    limit: number;
}

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
