-- Migration: Add COT Records table
CREATE TABLE cot_records (
    id UUID PRIMARY KEY,
    report_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    commercials_long NUMERIC(18, 2) NOT NULL,
    commercials_short NUMERIC(18, 2) NOT NULL,
    non_commercials_long NUMERIC(18, 2) NOT NULL,
    non_commercials_short NUMERIC(18, 2) NOT NULL,
    managed_money_long NUMERIC(18, 2),
    managed_money_short NUMERIC(18, 2),
    non_reportable_long NUMERIC(18, 2),
    non_reportable_short NUMERIC(18, 2),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX uq_cot_records_symbol_report_date ON cot_records (symbol, report_date);
CREATE INDEX ix_cot_records_report_date ON cot_records (report_date);
CREATE INDEX ix_cot_records_symbol ON cot_records (symbol);
