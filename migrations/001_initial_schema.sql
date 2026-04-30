-- Smart Investor — Initial Postgres schema for Supabase project hzendlfcpmibmgfqphln
-- Run this once in Supabase Dashboard → SQL Editor → New query.
--
-- Idempotent: safe to re-run.
-- Mirrors the SQLite schema in database.py for a like-for-like migration.

CREATE TABLE IF NOT EXISTS analyses (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT,
    idea TEXT NOT NULL,
    sector TEXT DEFAULT 'general',
    market_analysis TEXT,
    financial_analysis TEXT,
    competitive_analysis TEXT,
    legal_analysis TEXT,
    technical_analysis TEXT,
    brokerage_models_analysis TEXT,
    swot_analysis TEXT,
    action_plan TEXT,
    final_verdict TEXT,
    share_token TEXT UNIQUE,
    report_number TEXT,
    user_rating INT,
    user_feedback TEXT,
    requester_name TEXT,
    requester_email_enc TEXT,
    requester_company TEXT,
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_token ON analyses (share_token);
CREATE INDEX IF NOT EXISTS idx_analyses_valid_until ON analyses (valid_until);

CREATE TABLE IF NOT EXISTS bahrain_data_cache (
    dataset_id TEXT PRIMARY KEY,
    dataset_name TEXT,
    data_json TEXT,
    record_count INT DEFAULT 0,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS data_cache (
    id BIGSERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    sector TEXT NOT NULL,
    cache_key TEXT NOT NULL UNIQUE,
    data_json TEXT,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_data_cache_expires ON data_cache (expires_at);
