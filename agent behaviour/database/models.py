"""
Database Models for Agentic Honeypot
Pydantic models matching PostgreSQL schema
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from uuid import UUID, uuid4
from pydantic import field_validator



# ============================================================================
# ENUMS
# ============================================================================

class Channel(str, Enum):
    SMS = "SMS"
    WHATSAPP = "WhatsApp"
    EMAIL = "Email"
    CHAT = "Chat"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    BURNED = "burned"


class ConversationState(str, Enum):
    UNKNOWN = "UNKNOWN"
    PROBING = "PROBING"
    ENGAGING = "ENGAGING"
    DRAINING = "DRAINING"
    EXITING = "EXITING"
    TERMINATED = "TERMINATED"


class PersonaType(str, Enum):
    ELDERLY_UNCLE = "ELDERLY_UNCLE"
    BUSY_PROFESSIONAL = "BUSY_PROFESSIONAL"


class Sender(str, Enum):
    SCAMMER = "scammer"
    AGENT = "agent"


class ArtifactType(str, Enum):
    UPI_ID = "upi_id"
    BANK_ACCOUNT = "bank_account"
    PHONE_NUMBER = "phone_number"
    PHISHING_LINK = "phishing_link"
    SUSPICIOUS_KEYWORD = "suspicious_keyword"


class TacticType(str, Enum):
    URGENCY_PRESSURE = "urgency_pressure"
    AUTHORITY_CLAIM = "authority_claim"
    PAYMENT_REDIRECT = "payment_redirect"
    ACCOUNT_THREAT = "account_threat"
    VERIFICATION_SCAM = "verification_scam"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ============================================================================
# SESSION MODELS
# ============================================================================

class SessionCreate(BaseModel):
    """Request to create new session"""
    session_id: str
    channel: Channel = Channel.SMS
    language: str = "en"
    locale: str = "IN"
    persona: PersonaType = PersonaType.ELDERLY_UNCLE


class SessionUpdate(BaseModel):
    """Update session state"""
    current_state: Optional[ConversationState] = None
    status: Optional[SessionStatus] = None
    scam_detected: Optional[bool] = None
    final_confidence: Optional[float] = None
    exposure_risk: Optional[float] = None
    engagement_duration_seconds: Optional[int] = None
    completed_at: Optional[datetime] = None
    callback_sent: Optional[bool] = None
    callback_sent_at: Optional[datetime] = None
    callback_response: Optional[Dict[str, Any]] = None


class Session(BaseModel):
    """Full session record"""
    id: UUID
    session_id: str
    channel: Channel
    language: str
    locale: str
    persona: PersonaType
    initial_confidence: float
    status: SessionStatus
    current_state: ConversationState
    scam_detected: bool
    final_confidence: Optional[float] = None
    exposure_risk: Optional[float] = None
    total_messages_exchanged: int
    engagement_duration_seconds: int
    intelligence_extracted_count: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    callback_sent: bool
    callback_sent_at: Optional[datetime] = None
    callback_response: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# MESSAGE MODELS
# ============================================================================

class MessageCreate(BaseModel):
    """Create new message"""
    session_id: UUID
    sender: Sender
    text: str
    turn_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    response_delay_seconds: Optional[int] = None
    raw_llm_response: Optional[str] = None
    final_response: Optional[str] = None
    state_at_message: Optional[ConversationState] = None
    confidence_at_message: Optional[float] = None
    exposure_risk_at_message: Optional[float] = None


class Message(BaseModel):
    """Full message record"""
    id: UUID
    session_id: UUID
    sender: Sender
    text: str
    turn_number: int
    timestamp: datetime
    response_delay_seconds: Optional[int] = None
    raw_llm_response: Optional[str] = None
    final_response: Optional[str] = None
    state_at_message: Optional[ConversationState] = None
    confidence_at_message: Optional[float] = None
    exposure_risk_at_message: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# STATE EVOLUTION MODELS
# ============================================================================

class StateEvolutionCreate(BaseModel):
    """Record state evolution"""
    session_id: UUID
    message_id: UUID
    turn_number: int
    previous_state: Optional[ConversationState] = None
    current_state: ConversationState
    state_transition_occurred: bool = False
    turns_in_current_state: int
    previous_confidence: Optional[float] = None
    current_confidence: float
    confidence_delta: Optional[float] = None
    confidence_trend: Optional[str] = None
    exposure_risk: float
    exposure_delta: Optional[float] = None
    tone_confusion: Optional[float] = None
    tone_anxiety: Optional[float] = None
    tone_urgency: Optional[float] = None
    tone_compliance: Optional[float] = None
    tone_cognitive_load: Optional[float] = None
    drift_rate: Optional[float] = None
    initiative: Optional[float] = None
    signals_detected: Optional[List[str]] = None



class StateEvolution(BaseModel):
    id: UUID
    session_id: UUID
    message_id: UUID
    turn_number: int
    previous_state: Optional[ConversationState] = None
    current_state: ConversationState
    state_transition_occurred: bool
    turns_in_current_state: int
    previous_confidence: Optional[float] = None
    current_confidence: float
    confidence_delta: Optional[float] = None
    confidence_trend: Optional[str] = None
    exposure_risk: float
    exposure_delta: Optional[float] = None

    tone_confusion: Optional[float] = None
    tone_anxiety: Optional[float] = None
    tone_urgency: Optional[float] = None
    tone_compliance: Optional[float] = None
    tone_cognitive_load: Optional[float] = None

    drift_rate: Optional[float] = None
    initiative: Optional[float] = None

    signals_detected: Optional[List[str]] = None
    timestamp: datetime

    @field_validator("signals_detected", mode="before")
    @classmethod
    def parse_signals(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return json.loads(v)
        return v

    class Config:
        from_attributes = True



# ============================================================================
# INTELLIGENCE MODELS
# ============================================================================

class IntelligenceCreate(BaseModel):
    """Extract intelligence artifact"""
    session_id: UUID
    artifact_type: ArtifactType
    artifact_value: str
    extracted_from_message_id: UUID
    extracted_at_turn: int
    extraction_method: str = "regex"
    confirmed: bool = False
    confirmation_count: int = 1
    confidence_score: float = 0.5
    context_snippet: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IntelligenceUpdate(BaseModel):
    """Update intelligence (e.g., confirmation)"""
    confirmed: Optional[bool] = None
    confirmation_count: Optional[int] = None
    confidence_score: Optional[float] = None
    last_seen_at: Optional[datetime] = None


class ExtractedIntelligence(BaseModel):
    """Full intelligence record"""
    id: UUID
    session_id: UUID
    artifact_type: ArtifactType
    artifact_value: str
    extracted_from_message_id: UUID
    extracted_at_turn: int
    extraction_method: str
    confirmed: bool
    confirmation_count: int
    confidence_score: float
    first_seen_at: datetime
    last_seen_at: datetime
    context_snippet: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# TACTICS MODELS
# ============================================================================

class TacticCreate(BaseModel):
    """Record scammer tactic"""
    session_id: UUID
    tactic_type: TacticType
    tactic_description: Optional[str] = None
    detected_at_turn: int
    message_text: str
    keywords_used: Optional[List[str]] = None
    threat_level: str = "medium"


class ScammerTactic(BaseModel):
    """Full tactic record"""
    id: UUID
    session_id: UUID
    tactic_type: TacticType
    tactic_description: Optional[str] = None
    detected_at_turn: int
    message_text: str
    keywords_used: Optional[List[str]] = None
    threat_level: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# EVALUATION METRICS MODELS
# ============================================================================

class EvaluationMetricsCreate(BaseModel):
    """Calculate evaluation metrics"""
    session_id: UUID
    engagement_depth_score: float
    conversation_naturalness_score: float
    extraction_efficiency: float
    scam_detection_confidence: float
    false_positive_risk: float
    average_response_delay: float
    tone_drift_smoothness: float
    state_transition_count: int
    premature_exits: int
    unique_artifacts_extracted: int
    confirmed_artifacts_extracted: int
    high_confidence_artifacts: int
    typo_count: int
    message_truncations: int
    repetitions: int
    clarification_questions_asked: int
    overall_quality_score: float


class EvaluationMetrics(BaseModel):
    """Full metrics record"""
    id: UUID
    session_id: UUID
    engagement_depth_score: float
    conversation_naturalness_score: float
    extraction_efficiency: float
    scam_detection_confidence: float
    false_positive_risk: float
    average_response_delay: float
    tone_drift_smoothness: float
    state_transition_count: int
    premature_exits: int
    unique_artifacts_extracted: int
    confirmed_artifacts_extracted: int
    high_confidence_artifacts: int
    typo_count: int
    message_truncations: int
    repetitions: int
    clarification_questions_asked: int
    overall_quality_score: float
    calculated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# SYSTEM LOGS MODELS
# ============================================================================

class SystemLogCreate(BaseModel):
    """Create system log"""
    session_id: Optional[UUID] = None
    log_level: LogLevel
    component: str
    event_type: str
    message: str
    details: Optional[Dict[str, Any]] = None


class SystemLog(BaseModel):
    """Full log record"""
    id: UUID
    session_id: Optional[UUID] = None
    log_level: LogLevel
    component: str
    event_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# API RESPONSE MODELS
# ============================================================================

class ConversationHistoryItem(BaseModel):
    """Single message in conversation history"""
    sender: str
    text: str
    timestamp: str


class IncomingMessageRequest(BaseModel):
    """API request format from GUVI platform"""
    sessionId: str
    message: Dict[str, Any]  # sender, text, timestamp
    conversationHistory: List[Dict[str, Any]] = []
    metadata: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    """API response format"""
    status: str = "success"
    scamDetected: bool
    agentMessage: Optional[str] = None
    shouldContinue: bool = True
    extractedIntelligence: Optional[Dict[str, List[str]]] = None
    agentNotes: Optional[str] = None


class FinalCallbackPayload(BaseModel):
    """Final result callback to GUVI"""
    sessionId: str
    scamDetected: bool
    totalMessagesExchanged: int
    extractedIntelligence: Dict[str, List[str]]
    agentNotes: str
    
    class Config:
        # Use camelCase for API
        populate_by_name = True