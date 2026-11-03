CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(50) PRIMARY KEY,
    risk_tolerance VARCHAR(20) DEFAULT 'moderate',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS insights_log (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id),
    category VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    confidence_score NUMERIC(3, 2),
    is_validated BOOLEAN DEFAULT FALSE,
    raw_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    description TEXT,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);