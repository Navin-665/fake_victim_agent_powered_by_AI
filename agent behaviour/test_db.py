import asyncio
import uuid

from database.service import create_database_pool, DatabaseService
from database.models import (
    SessionCreate,
    Channel,
    PersonaType
)

async def main():
    pool = await create_database_pool()
    db = DatabaseService(pool)

    # 1️⃣ Create unique session
    session_key = f"metrics-test-{uuid.uuid4()}"
    session = await db.create_session(
        SessionCreate(
            session_id=session_key,
            channel=Channel.SMS,
            persona=PersonaType.ELDERLY_UNCLE
        )
    )

    print("\nSession created:")
    print(session.session_id)

    # 2️⃣ Insert evaluation metrics (CORRECT acquire usage)
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO evaluation_metrics (
                session_id,
                engagement_depth_score,
                conversation_naturalness_score,
                extraction_efficiency,
                scam_detection_confidence,
                false_positive_risk,
                average_response_delay,
                tone_drift_smoothness,
                state_transition_count,
                premature_exits,
                unique_artifacts_extracted,
                confirmed_artifacts_extracted,
                high_confidence_artifacts,
                typo_count,
                message_truncations,
                repetitions,
                clarification_questions_asked,
                overall_quality_score
            )
            VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9, $10, $11, $12,
                $13, $14, $15, $16, $17, $18
            )
            RETURNING *
            """,
            session.id,
            3.8,    # engagement depth
            0.91,   # naturalness
            0.62,   # extraction efficiency
            0.94,   # detection confidence
            0.03,   # false positive risk
            14.6,   # avg response delay
            0.88,   # tone drift smoothness
            3,      # state transitions
            0,      # premature exits
            4,      # unique artifacts
            3,      # confirmed artifacts
            2,      # high confidence artifacts
            5,      # typos
            1,      # truncations
            0,      # repetitions
            4,      # clarification questions
            92.4    # overall quality
        )

    print("\nEvaluation metrics inserted:")
    print(dict(row))

    # 3️⃣ Hard guarantees (this is what matters)
    assert row["overall_quality_score"] > 90
    assert row["false_positive_risk"] < 0.1
    assert row["confirmed_artifacts_extracted"] <= row["unique_artifacts_extracted"]

    print("\n✅ Evaluation metrics verified")

    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
