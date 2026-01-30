"""
Database Service Layer
Handles all PostgreSQL and Redis operations
"""

import asyncpg
import redis.asyncio as redis
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import os

from database.models import (
    Session, SessionCreate, SessionUpdate,
    Message, MessageCreate,
    StateEvolution, StateEvolutionCreate,
    ExtractedIntelligence, IntelligenceCreate, IntelligenceUpdate,
    ScammerTactic, TacticCreate,
    SystemLog, SystemLogCreate,
    ConversationState, SessionStatus, PersonaType
)


class DatabaseService:
    """PostgreSQL database operations"""
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
    
    # ========================================================================
    # SESSION OPERATIONS
    # ========================================================================
    
    async def create_session(self, session_data: SessionCreate) -> Session:
        """Create new conversation session"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO sessions (
                    session_id, channel, language, locale, persona
                )
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                session_data.session_id,
                session_data.channel.value,
                session_data.language,
                session_data.locale,
                session_data.persona.value
            )
            return Session(**dict(row))
    
    async def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """Get session by session_id"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM sessions WHERE session_id = $1",
                session_id
            )
            return Session(**dict(row)) if row else None
    
    async def get_session_by_uuid(self, uuid: UUID) -> Optional[Session]:
        """Get session by UUID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM sessions WHERE id = $1",
                uuid
            )
            return Session(**dict(row)) if row else None
    
    async def update_session(self, session_id: str, updates: SessionUpdate) -> Session:
        """Update session fields"""
        update_dict = updates.dict(exclude_unset=True)
        
        if not update_dict:
            return await self.get_session_by_id(session_id)
        
        # Build dynamic UPDATE query
        set_clauses = []
        values = []
        param_num = 1
        
        for field, value in update_dict.items():
            set_clauses.append(f"{field} = ${param_num}")
            values.append(value.value if hasattr(value, 'value') else value)
            param_num += 1
        
        values.append(session_id)
        
        query = f"""
            UPDATE sessions 
            SET {', '.join(set_clauses)}
            WHERE session_id = ${param_num}
            RETURNING *
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            return Session(**dict(row))
    
    async def get_active_sessions(self) -> List[Session]:
        """Get all active sessions"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM sessions WHERE status = 'active' ORDER BY created_at DESC"
            )
            return [Session(**dict(row)) for row in rows]
    
    # ========================================================================
    # MESSAGE OPERATIONS
    # ========================================================================
    
    async def create_message(self, message_data: MessageCreate) -> Message:
        """Insert new message"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO messages (
                    session_id, sender, text, turn_number, timestamp,
                    response_delay_seconds, raw_llm_response, final_response,
                    state_at_message, confidence_at_message, exposure_risk_at_message
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING *
                """,
                message_data.session_id,
                message_data.sender.value,
                message_data.text,
                message_data.turn_number,
                message_data.timestamp,
                message_data.response_delay_seconds,
                message_data.raw_llm_response,
                message_data.final_response,
                message_data.state_at_message.value if message_data.state_at_message else None,
                message_data.confidence_at_message,
                message_data.exposure_risk_at_message
            )
            return Message(**dict(row))
    
    async def get_conversation_history(self, session_uuid: UUID, limit: int = 50) -> List[Message]:
        """Get message history for session"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM messages 
                WHERE session_id = $1 
                ORDER BY turn_number ASC
                LIMIT $2
                """,
                session_uuid,
                limit
            )
            return [Message(**dict(row)) for row in rows]
    
    async def get_last_agent_message(self, session_uuid: UUID) -> Optional[Message]:
        """Get most recent agent message"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM messages 
                WHERE session_id = $1 AND sender = 'agent'
                ORDER BY turn_number DESC
                LIMIT 1
                """,
                session_uuid
            )
            return Message(**dict(row)) if row else None
    
    # ========================================================================
    # STATE EVOLUTION OPERATIONS
    # ========================================================================
    
    async def record_state_evolution(self, evolution_data: StateEvolutionCreate) -> StateEvolution:
        """Record state evolution snapshot"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO state_evolution (
                    session_id, message_id, turn_number,
                    previous_state, current_state, state_transition_occurred,
                    turns_in_current_state,
                    previous_confidence, current_confidence, confidence_delta, confidence_trend,
                    exposure_risk, exposure_delta,
                    tone_confusion, tone_anxiety, tone_urgency, tone_compliance, tone_cognitive_load,
                    drift_rate, initiative, signals_detected
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
                RETURNING *
                """,
                evolution_data.session_id,
                evolution_data.message_id,
                evolution_data.turn_number,
                evolution_data.previous_state.value if evolution_data.previous_state else None,
                evolution_data.current_state.value,
                evolution_data.state_transition_occurred,
                evolution_data.turns_in_current_state,
                evolution_data.previous_confidence,
                evolution_data.current_confidence,
                evolution_data.confidence_delta,
                evolution_data.confidence_trend,
                evolution_data.exposure_risk,
                evolution_data.exposure_delta,
                evolution_data.tone_confusion,
                evolution_data.tone_anxiety,
                evolution_data.tone_urgency,
                evolution_data.tone_compliance,
                evolution_data.tone_cognitive_load,
                evolution_data.drift_rate,
                evolution_data.initiative,
                json.dumps(evolution_data.signals_detected)
                if evolution_data.signals_detected is not None
                else json.dumps([])

            )
            data = dict(row)

            if data.get("signals_detected"):
                data["signals_detected"] = json.loads(data["signals_detected"])

            return StateEvolution(**data)

    
    async def get_state_history(self, session_uuid: UUID) -> List[StateEvolution]:
        """Get full state evolution history"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM state_evolution 
                WHERE session_id = $1 
                ORDER BY turn_number ASC
                """,
                session_uuid
            )
            return [StateEvolution(**dict(row)) for row in rows]
    
    # ========================================================================
    # INTELLIGENCE OPERATIONS
    # ========================================================================
    
    async def extract_intelligence(self, intel_data: IntelligenceCreate) -> Optional[ExtractedIntelligence]:
        """
        Extract intelligence artifact.
        Handles duplicates by updating confirmation count.
        """
        async with self.pool.acquire() as conn:
            # Try to insert, on conflict update confirmation
            row = await conn.fetchrow(
                """
                INSERT INTO extracted_intelligence (
                    session_id, artifact_type, artifact_value,
                    extracted_from_message_id, extracted_at_turn,
                    extraction_method, confirmed, confirmation_count,
                    confidence_score, context_snippet, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (session_id, artifact_type, artifact_value) 
                DO UPDATE SET
                    confirmation_count = extracted_intelligence.confirmation_count + 1,
                    confirmed = true,
                    last_seen_at = CURRENT_TIMESTAMP
                RETURNING *
                """,
                intel_data.session_id,
                intel_data.artifact_type.value,
                intel_data.artifact_value,
                intel_data.extracted_from_message_id,
                intel_data.extracted_at_turn,
                intel_data.extraction_method,
                intel_data.confirmed,
                intel_data.confirmation_count,
                intel_data.confidence_score,
                intel_data.context_snippet,
                json.dumps(intel_data.metadata) if intel_data.metadata else None
            )
            return ExtractedIntelligence(**dict(row)) if row else None
    
    async def get_session_intelligence(self, session_uuid: UUID) -> List[ExtractedIntelligence]:
        """Get all intelligence for session"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM extracted_intelligence 
                WHERE session_id = $1 
                ORDER BY first_seen_at ASC
                """,
                session_uuid
            )
            return [ExtractedIntelligence(**dict(row)) for row in rows]
    
    async def get_confirmed_intelligence(self, session_uuid: UUID) -> List[ExtractedIntelligence]:
        """Get only confirmed intelligence"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM extracted_intelligence 
                WHERE session_id = $1 AND confirmed = true
                ORDER BY confirmation_count DESC
                """,
                session_uuid
            )
            return [ExtractedIntelligence(**dict(row)) for row in rows]
    
    # ========================================================================
    # TACTICS OPERATIONS
    # ========================================================================
    
    async def record_tactic(self, tactic_data: TacticCreate) -> ScammerTactic:
        """Record scammer tactic"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO scammer_tactics (
                    session_id, tactic_type, tactic_description,
                    detected_at_turn, message_text, keywords_used, threat_level
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
                """,
                tactic_data.session_id,
                tactic_data.tactic_type.value,
                tactic_data.tactic_description,
                tactic_data.detected_at_turn,
                tactic_data.message_text,
                json.dumps(tactic_data.keywords_used) if tactic_data.keywords_used else None,

                tactic_data.threat_level,
            )
            data = dict(row)

            if data.get("keywords_used"):
                data["keywords_used"] = json.loads(data["keywords_used"])

            return ScammerTactic(**data) 

    
    # ========================================================================
    # LOGGING OPERATIONS
    # ========================================================================
    
    async def log(self, log_data: SystemLogCreate):
        """Create system log"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO system_logs (
                    session_id, log_level, component, event_type, message, details
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                log_data.session_id,
                log_data.log_level.value,
                log_data.component,
                log_data.event_type,
                log_data.message,
                json.dumps(log_data.details) if log_data.details else None
            )


class RedisCache:
    """Redis operations for session caching"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.session_ttl = 3600  # 1 hour
    
    def _session_key(self, session_id: str) -> str:
        return f"session:{session_id}"
    
    def _state_key(self, session_id: str) -> str:
        return f"state:{session_id}"
    
    async def cache_session(self, session_id: str, session_data: Dict[str, Any]):
        """Cache session data"""
        key = self._session_key(session_id)
        await self.redis.setex(
            key,
            self.session_ttl,
            json.dumps(session_data)
        )
    
    async def get_cached_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached session"""
        key = self._session_key(session_id)
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def cache_state(self, session_id: str, state_data: Dict[str, Any]):
        """Cache current conversation state"""
        key = self._state_key(session_id)
        await self.redis.setex(
            key,
            self.session_ttl,
            json.dumps(state_data)
        )
    
    async def get_cached_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached state"""
        key = self._state_key(session_id)
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def invalidate_session(self, session_id: str):
        """Remove session from cache"""
        session_key = self._session_key(session_id)
        state_key = self._state_key(session_id)
        await self.redis.delete(session_key, state_key)
    
    async def extend_session_ttl(self, session_id: str):
        """Extend TTL when session is active"""
        session_key = self._session_key(session_id)
        state_key = self._state_key(session_id)
        await self.redis.expire(session_key, self.session_ttl)
        await self.redis.expire(state_key, self.session_ttl)


# ============================================================================
# DATABASE CONNECTION MANAGEMENT
# ============================================================================

async def create_database_pool(
    host: str = None,
    port: int = None,
    database: str = None,
    user: str = None,
    password: str = None
) -> asyncpg.Pool:
    """Create PostgreSQL connection pool"""
    
    # Get from environment if not provided
    host = host or os.getenv('POSTGRES_HOST', 'localhost')
    port = port or int(os.getenv('POSTGRES_PORT', 5432))
    database = database or os.getenv('POSTGRES_DB', 'honeypot')
    user = user or os.getenv('POSTGRES_USER', 'postgres')
    password = password or os.getenv('POSTGRES_PASSWORD', '12345')
    
    pool = await asyncpg.create_pool(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        min_size=5,
        max_size=20,
        command_timeout=60
    )
    
    return pool


async def create_redis_client(
    host: str = None,
    port: int = None,
    db: int = 0
) -> redis.Redis:
    """Create Redis client"""
    
    host = host or os.getenv('REDIS_HOST', 'localhost')
    port = port or int(os.getenv('REDIS_PORT', 6379))
    
    client = redis.Redis(
        host=host,
        port=port,
        db=db,
        decode_responses=True
    )
    
    return client