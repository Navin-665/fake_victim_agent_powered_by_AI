-- Agentic Honeypot Database Schema
-- PostgreSQL 14+

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- SESSIONS TABLE
-- Tracks each unique conversation with a scammer
-- ============================================================================
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) UNIQUE NOT NULL, -- From API request
    
    -- Session metadata
    channel VARCHAR(50) NOT NULL, -- SMS, WhatsApp, Email, Chat
    language VARCHAR(10) DEFAULT 'en',
    locale VARCHAR(10) DEFAULT 'IN',
    
    -- Persona & initial state
    persona VARCHAR(50) NOT NULL, -- ELDERLY_UNCLE, BUSY_PROFESSIONAL
    initial_confidence DECIMAL(3,2) DEFAULT 0.35,
    
    -- Session lifecycle
    status VARCHAR(50) DEFAULT 'active', -- active, completed, terminated, burned
    current_state VARCHAR(50) DEFAULT 'UNKNOWN', -- UNKNOWN, PROBING, ENGAGING, DRAINING, EXITING
    
    -- Final results
    scam_detected BOOLEAN DEFAULT false,
    final_confidence DECIMAL(3,2),
    exposure_risk DECIMAL(3,2),
    
    -- Metrics
    total_messages_exchanged INTEGER DEFAULT 0,
    engagement_duration_seconds INTEGER DEFAULT 0,
    intelligence_extracted_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Callback tracking
    callback_sent BOOLEAN DEFAULT false,
    callback_sent_at TIMESTAMP,
    callback_response JSONB
);

-- Indexes for fast lookups
CREATE INDEX idx_sessions_session_id ON sessions(session_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
CREATE INDEX idx_sessions_scam_detected ON sessions(scam_detected);


-- ============================================================================
-- MESSAGES TABLE
-- Every message in every conversation
-- ============================================================================
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    
    -- Message content
    sender VARCHAR(20) NOT NULL, -- 'scammer' or 'agent'
    text TEXT NOT NULL,
    
    -- Message context
    turn_number INTEGER NOT NULL, -- Sequential within session
    timestamp TIMESTAMP NOT NULL,
    
    -- Agent response metadata (only for agent messages)
    response_delay_seconds INTEGER, -- How long agent "took" to respond
    raw_llm_response TEXT, -- Before linguistic effects
    final_response TEXT, -- After typos, truncation, etc.
    
    -- State at time of message
    state_at_message VARCHAR(50),
    confidence_at_message DECIMAL(3,2),
    exposure_risk_at_message DECIMAL(3,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_sender ON messages(sender);
CREATE INDEX idx_messages_turn_number ON messages(session_id, turn_number);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);


-- ============================================================================
-- STATE_EVOLUTION TABLE
-- Time-series tracking of state, confidence, and tone changes
-- ============================================================================
CREATE TABLE state_evolution (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    
    -- Turn context
    turn_number INTEGER NOT NULL,
    
    -- State tracking
    previous_state VARCHAR(50),
    current_state VARCHAR(50) NOT NULL,
    state_transition_occurred BOOLEAN DEFAULT false,
    turns_in_current_state INTEGER DEFAULT 0,
    
    -- Confidence tracking
    previous_confidence DECIMAL(3,2),
    current_confidence DECIMAL(3,2) NOT NULL,
    confidence_delta DECIMAL(3,2),
    confidence_trend VARCHAR(20), -- increasing, decreasing, stable
    
    -- Exposure risk tracking
    exposure_risk DECIMAL(3,2) NOT NULL,
    exposure_delta DECIMAL(3,2),
    
    -- Tone vector (all values 0.0 - 1.0)
    tone_confusion DECIMAL(3,2),
    tone_anxiety DECIMAL(3,2),
    tone_urgency DECIMAL(3,2),
    tone_compliance DECIMAL(3,2),
    tone_cognitive_load DECIMAL(3,2),
    
    -- Drift metadata
    drift_rate DECIMAL(3,2), -- Effective drift rate used
    initiative DECIMAL(3,2), -- Hidden initiative value
    
    -- Evidence signals detected
    signals_detected JSONB, -- Array of signal types
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_state_evolution_session_id ON state_evolution(session_id);
CREATE INDEX idx_state_evolution_turn_number ON state_evolution(session_id, turn_number);
CREATE INDEX idx_state_evolution_state_transitions ON state_evolution(state_transition_occurred);


-- ============================================================================
-- EXTRACTED_INTELLIGENCE TABLE
-- All intelligence artifacts extracted during conversation
-- ============================================================================
CREATE TABLE extracted_intelligence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    
    -- Artifact details
    artifact_type VARCHAR(50) NOT NULL, -- upi_id, bank_account, phone_number, phishing_link, keyword
    artifact_value TEXT NOT NULL,
    
    -- Extraction context
    extracted_from_message_id UUID REFERENCES messages(id),
    extracted_at_turn INTEGER,
    extraction_method VARCHAR(50), -- regex, pattern_match, llm_extraction
    
    -- Verification
    confirmed BOOLEAN DEFAULT false, -- Mentioned multiple times
    confirmation_count INTEGER DEFAULT 1,
    confidence_score DECIMAL(3,2) DEFAULT 0.5, -- How sure we are it's valid
    
    -- Metadata
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Additional context
    context_snippet TEXT, -- Surrounding text where found
    metadata JSONB -- Flexible storage for type-specific data
);

-- Indexes
CREATE INDEX idx_intelligence_session_id ON extracted_intelligence(session_id);
CREATE INDEX idx_intelligence_type ON extracted_intelligence(artifact_type);
CREATE INDEX idx_intelligence_confirmed ON extracted_intelligence(confirmed);
CREATE INDEX idx_intelligence_value ON extracted_intelligence(artifact_value);

-- Unique constraint: Same artifact value can't be duplicated in same session
CREATE UNIQUE INDEX idx_intelligence_unique_per_session 
    ON extracted_intelligence(session_id, artifact_type, artifact_value);


-- ============================================================================
-- SCAMMER_TACTICS TABLE
-- Patterns and tactics used by scammers (cross-session analysis)
-- ============================================================================
CREATE TABLE scammer_tactics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    
    -- Tactic identification
    tactic_type VARCHAR(100) NOT NULL, -- urgency_pressure, authority_claim, payment_redirect, etc.
    tactic_description TEXT,
    
    -- Detection
    detected_at_turn INTEGER,
    message_text TEXT, -- The message that triggered detection
    
    -- Pattern data
    keywords_used JSONB, -- Array of keywords
    threat_level VARCHAR(20), -- low, medium, high
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_tactics_session_id ON scammer_tactics(session_id);
CREATE INDEX idx_tactics_type ON scammer_tactics(tactic_type);
CREATE INDEX idx_tactics_threat_level ON scammer_tactics(threat_level);


-- ============================================================================
-- EVALUATION_METRICS TABLE
-- Metrics for hackathon evaluation and performance analysis
-- ============================================================================
CREATE TABLE evaluation_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    
    -- Engagement quality
    engagement_depth_score DECIMAL(5,2), -- Custom metric: intelligence_count / turns_to_detection
    conversation_naturalness_score DECIMAL(3,2), -- 0-1, based on tone continuity
    extraction_efficiency DECIMAL(3,2), -- Intelligence per turn
    
    -- Detection metrics
    scam_detection_confidence DECIMAL(3,2),
    false_positive_risk DECIMAL(3,2),
    
    -- Realism metrics
    average_response_delay DECIMAL(6,2), -- Seconds
    tone_drift_smoothness DECIMAL(3,2), -- How gradual tone changes were
    state_transition_count INTEGER,
    premature_exits INTEGER, -- How many times almost exited early
    
    -- Intelligence quality
    unique_artifacts_extracted INTEGER,
    confirmed_artifacts_extracted INTEGER,
    high_confidence_artifacts INTEGER,
    
    -- Behavioral metrics
    typo_count INTEGER,
    message_truncations INTEGER,
    repetitions INTEGER,
    clarification_questions_asked INTEGER,
    
    -- Final scores
    overall_quality_score DECIMAL(5,2), -- Weighted combination
    
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index
CREATE INDEX idx_metrics_session_id ON evaluation_metrics(session_id);


-- ============================================================================
-- SYSTEM_LOGS TABLE
-- Debug and audit trail
-- ============================================================================
CREATE TABLE system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    
    -- Log details
    log_level VARCHAR(20) NOT NULL, -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    component VARCHAR(100), -- confidence_tracker, state_engine, tone_engine, etc.
    event_type VARCHAR(100), -- state_transition, confidence_update, exposure_alert, etc.
    
    message TEXT NOT NULL,
    details JSONB, -- Structured log data
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_logs_session_id ON system_logs(session_id);
CREATE INDEX idx_logs_level ON system_logs(log_level);
CREATE INDEX idx_logs_timestamp ON system_logs(timestamp);
CREATE INDEX idx_logs_component ON system_logs(component);


-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Active sessions overview
CREATE VIEW v_active_sessions AS
SELECT 
    s.id,
    s.session_id,
    s.persona,
    s.current_state,
    s.total_messages_exchanged,
    s.scam_detected,
    s.final_confidence,
    s.created_at,
    COUNT(DISTINCT ei.id) as intelligence_count,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - s.created_at)) as session_duration_seconds
FROM sessions s
LEFT JOIN extracted_intelligence ei ON s.id = ei.session_id
WHERE s.status = 'active'
GROUP BY s.id;

-- Intelligence summary per session
CREATE VIEW v_intelligence_summary AS
SELECT 
    s.session_id,
    COUNT(DISTINCT ei.id) as total_artifacts,
    COUNT(DISTINCT CASE WHEN ei.confirmed THEN ei.id END) as confirmed_artifacts,
    COUNT(DISTINCT CASE WHEN ei.artifact_type = 'upi_id' THEN ei.id END) as upi_ids,
    COUNT(DISTINCT CASE WHEN ei.artifact_type = 'bank_account' THEN ei.id END) as bank_accounts,
    COUNT(DISTINCT CASE WHEN ei.artifact_type = 'phone_number' THEN ei.id END) as phone_numbers,
    COUNT(DISTINCT CASE WHEN ei.artifact_type = 'phishing_link' THEN ei.id END) as phishing_links
FROM sessions s
LEFT JOIN extracted_intelligence ei ON s.id = ei.session_id
GROUP BY s.session_id;

-- State transition timeline
CREATE VIEW v_state_timeline AS
SELECT 
    s.session_id,
    se.turn_number,
    se.current_state,
    se.current_confidence,
    se.exposure_risk,
    se.tone_anxiety,
    se.tone_confusion,
    se.tone_urgency,
    se.timestamp
FROM sessions s
JOIN state_evolution se ON s.id = se.session_id
WHERE se.state_transition_occurred = true
ORDER BY s.session_id, se.turn_number;


-- ============================================================================
-- TRIGGERS FOR AUTO-UPDATE
-- ============================================================================

-- Update sessions.updated_at on any change
CREATE OR REPLACE FUNCTION update_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_session_timestamp
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_session_timestamp();


-- Auto-increment total_messages_exchanged when new message added
CREATE OR REPLACE FUNCTION increment_message_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE sessions 
    SET total_messages_exchanged = total_messages_exchanged + 1
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_increment_message_count
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION increment_message_count();


-- Auto-increment intelligence_extracted_count
CREATE OR REPLACE FUNCTION increment_intelligence_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE sessions 
    SET intelligence_extracted_count = intelligence_extracted_count + 1
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_increment_intelligence_count
    AFTER INSERT ON extracted_intelligence
    FOR EACH ROW
    EXECUTE FUNCTION increment_intelligence_count();


-- ============================================================================
-- SEED DATA (for testing)
-- ============================================================================

-- Insert test session
INSERT INTO sessions (session_id, channel, language, locale, persona, status, current_state)
VALUES 
    ('test-session-001', 'SMS', 'en', 'IN', 'ELDERLY_UNCLE', 'active', 'PROBING'),
    ('test-session-002', 'WhatsApp', 'en', 'IN', 'BUSY_PROFESSIONAL', 'completed', 'EXITING');

-- Sample messages
INSERT INTO messages (session_id, sender, text, turn_number, timestamp, state_at_message, confidence_at_message)
VALUES 
    (
        (SELECT id FROM sessions WHERE session_id = 'test-session-001'),
        'scammer',
        'Your bank account will be blocked today. Verify immediately.',
        1,
        CURRENT_TIMESTAMP,
        'UNKNOWN',
        0.35
    ),
    (
        (SELECT id FROM sessions WHERE session_id = 'test-session-001'),
        'agent',
        'Beta what happened to my account? Why it will be blocked?',
        2,
        CURRENT_TIMESTAMP + INTERVAL '45 seconds',
        'PROBING',
        0.58
    );

-- Sample extracted intelligence
INSERT INTO extracted_intelligence (session_id, artifact_type, artifact_value, extracted_at_turn, extraction_method, confirmed)
VALUES
    (
        (SELECT id FROM sessions WHERE session_id = 'test-session-001'),
        'upi_id',
        'scammer@paytm',
        5,
        'regex',
        true
    );

COMMENT ON TABLE sessions IS 'Unique conversation sessions with scammers';
COMMENT ON TABLE messages IS 'Turn-by-turn message history';
COMMENT ON TABLE state_evolution IS 'Time-series tracking of state, confidence, and tone';
COMMENT ON TABLE extracted_intelligence IS 'Intelligence artifacts extracted from conversations';
COMMENT ON TABLE scammer_tactics IS 'Scammer tactics and patterns detected';
COMMENT ON TABLE evaluation_metrics IS 'Performance metrics for evaluation';
COMMENT ON TABLE system_logs IS 'System debug and audit logs';