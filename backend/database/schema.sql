-- Ensure pgvector extension is present
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(50) PRIMARY KEY,
    risk_tolerance VARCHAR(20) DEFAULT 'moderate',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Jobs Table
CREATE TABLE IF NOT EXISTS jobs (
    id VARCHAR(100) PRIMARY KEY,
    status VARCHAR(50) NOT NULL DEFAULT 'submitted', -- 'submitted', 'fetching_data', 'mcp_tools', 'running_analytics', 'llm_analysis', 'validating', 'completed', 'failed'
    portfolio_id VARCHAR(100),
    job_type VARCHAR(50) DEFAULT 'portfolio_analysis',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 3. Insights Log Table (Preserved & Extended)
CREATE TABLE IF NOT EXISTS insights_log (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) REFERENCES jobs(id) ON DELETE SET NULL,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    confidence_score NUMERIC(3, 2),
    is_validated BOOLEAN DEFAULT FALSE,
    validation_reason TEXT,
    raw_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Audit Events Table (Preserved & Extended for MCP & System Telemetry)
CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL, -- 'mcp_tool_call', 'compliance_flag', 'system_event'
    tool_name VARCHAR(100),
    parameters JSONB,
    latency_ms NUMERIC,
    status VARCHAR(20), -- 'success', 'error'
    error_message TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Recommendation Cards Table
CREATE TABLE IF NOT EXISTS recommendation_cards (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) REFERENCES jobs(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL, -- 'Risk Alert', 'Diversification Review', 'Watchlist Monitoring', 'Summary Follow-up'
    title VARCHAR(255),
    rationale TEXT NOT NULL,
    confidence NUMERIC(3, 2),
    freshness_ts TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    disclaimer TEXT,
    metrics_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Feedback Table
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES recommendation_cards(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL CHECK (action IN ('thumbs_up', 'thumbs_down', 'accepted', 'dismissed')),
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Insight Embeddings Table (Vector Retrieval via pgvector - 768 dimensions for Gemini text-embedding-004)
CREATE TABLE IF NOT EXISTS insight_embeddings (
    id SERIAL PRIMARY KEY,
    insight_id INTEGER REFERENCES insights_log(id) ON DELETE CASCADE,
    embedding vector(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Kite Sessions Table
CREATE TABLE IF NOT EXISTS kite_sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    environment VARCHAR(20) NOT NULL CHECK (environment IN ('sandbox', 'live')),
    encrypted_access_token TEXT NOT NULL,
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Indexing for performance
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_insights_user ON insights_log(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_job ON recommendation_cards(job_id);
CREATE INDEX IF NOT EXISTS idx_feedback_card ON feedback(card_id);
CREATE INDEX IF NOT EXISTS idx_kite_sessions_user_env ON kite_sessions(user_id, environment);
