import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("DatabaseConnection")

def get_db_connection():
    """Returns a direct psycopg2 connection using DATABASE_URL."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is missing.")
    return psycopg2.connect(db_url, connect_timeout=5)

# -------------------------------------------------------------
# Jobs CRUD
# -------------------------------------------------------------

def create_job(job_id: str, portfolio_id: str, job_type: str = "portfolio_analysis") -> dict:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO jobs (id, status, portfolio_id, job_type, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *;
            """, (job_id, "submitted", portfolio_id, job_type, datetime.now(timezone.utc)))
            job = dict(cur.fetchone())
            conn.commit()
            return job
    finally:
        conn.close()

def update_job_status(job_id: str, status: str, completed: bool = False) -> None:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if completed:
                cur.execute("""
                    UPDATE jobs 
                    SET status = %s, completed_at = %s 
                    WHERE id = %s;
                """, (status, datetime.now(timezone.utc), job_id))
            else:
                cur.execute("""
                    UPDATE jobs 
                    SET status = %s 
                    WHERE id = %s;
                """, (status, job_id))
            conn.commit()
    finally:
        conn.close()

def get_job(job_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM jobs WHERE id = %s;", (job_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def save_kite_session(
    user_id: str,
    environment: str,
    encrypted_access_token: str,
    expires_at: datetime,
) -> None:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id)
                VALUES (%s)
                ON CONFLICT (id) DO NOTHING;
                """,
                (user_id,),
            )
            cur.execute(
                """
                INSERT INTO kite_sessions (
                    user_id, environment, encrypted_access_token, expires_at
                )
                VALUES (%s, %s, %s, %s);
                """,
                (user_id, environment, encrypted_access_token, expires_at),
            )
        conn.commit()
    finally:
        conn.close()


def get_kite_session(user_id: str, environment: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT user_id, environment, encrypted_access_token, expires_at
                FROM kite_sessions
                WHERE user_id = %s AND environment = %s
                ORDER BY connected_at DESC, id DESC
                LIMIT 1;
                """,
                (user_id, environment),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def get_recommendation_card_job(card_id: int) -> Optional[dict]:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT rc.id, rc.job_id, j.portfolio_id, j.job_type
                FROM recommendation_cards rc
                LEFT JOIN jobs j ON j.id = rc.job_id
                WHERE rc.id = %s;
                """,
                (card_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()

def record_audit_event(
    event_type: str,
    parameters: dict,
    status: str,
    description: str,
    tool_name: Optional[str] = None,
    latency_ms: Optional[float] = None,
    error_message: Optional[str] = None
) -> dict:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO audit_events (
                    event_type, tool_name, parameters, latency_ms, status, error_message, description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *;
            """, (
                event_type,
                tool_name,
                json.dumps(parameters),
                latency_ms,
                status,
                error_message,
                description
            ))
            event = dict(cur.fetchone())
            conn.commit()
            return event
    finally:
        conn.close()

# -------------------------------------------------------------
# Insights Log CRUD
# -------------------------------------------------------------

def save_insight_log(
    job_id: str,
    user_id: str,
    category: str,
    title: str,
    confidence_score: float,
    is_validated: bool,
    validation_reason: str,
    raw_json: dict
) -> int:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Ensure user exists in users table to satisfy foreign key
            cur.execute("""
                INSERT INTO users (id, risk_tolerance) 
                VALUES (%s, 'moderate')
                ON CONFLICT (id) DO NOTHING;
            """, (user_id,))
            
            cur.execute("""
                INSERT INTO insights_log (
                    job_id, user_id, category, title, confidence_score, is_validated, validation_reason, raw_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (
                job_id,
                user_id,
                category,
                title,
                confidence_score,
                is_validated,
                validation_reason,
                json.dumps(raw_json)
            ))
            insight_id = cur.fetchone()[0]
            conn.commit()
            return insight_id
    finally:
        conn.close()

def get_insight_by_job(job_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM insights_log WHERE job_id = %s ORDER BY created_at DESC LIMIT 1;", (job_id,))
            row = cur.fetchone()
            if row:
                res = dict(row)
                if isinstance(res.get("raw_json"), str):
                    res["raw_json"] = json.loads(res["raw_json"])
                return res
            return None
    finally:
        conn.close()

# -------------------------------------------------------------
# Recommendation Cards CRUD
# -------------------------------------------------------------

def save_recommendation_cards(job_id: Optional[str], cards: list[dict]) -> list[dict]:
    if not cards:
        return []

    conn = get_db_connection()
    saved_cards = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for card in cards:
                cur.execute("""
                    INSERT INTO recommendation_cards (
                        job_id, category, title, rationale, confidence, freshness_ts, disclaimer, metrics_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *;
                """, (
                    job_id,
                    card.get("category", "General"),
                    card.get("title", "Portfolio Recommendation"),
                    card.get("rationale", ""),
                    card.get("confidence", 0.9),
                    card.get("freshness_ts") or card.get("freshness_timestamp") or datetime.now(timezone.utc),
                    card.get("disclaimer", ""),
                    json.dumps(card.get("metrics_json", card.get("supporting_metrics", [])))
                ))
                saved_cards.append(dict(cur.fetchone()))
            conn.commit()
            return saved_cards
    finally:
        conn.close()

def get_recommendation_cards_by_job(job_id: str) -> list[dict]:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM recommendation_cards 
                WHERE job_id = %s 
                ORDER BY id ASC;
            """, (job_id,))
            rows = cur.fetchall()
            cards = []
            for r in rows:
                c = dict(r)
                if isinstance(c.get("metrics_json"), str):
                    c["metrics_json"] = json.loads(c["metrics_json"])
                cards.append(c)
            return cards
    finally:
        conn.close()

# -------------------------------------------------------------
# Feedback CRUD
# -------------------------------------------------------------

def record_feedback(card_id: int, action: str, note: Optional[str] = None) -> dict:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO feedback (card_id, action, note)
                VALUES (%s, %s, %s)
                RETURNING *;
            """, (card_id, action, note))
            fb = dict(cur.fetchone())
            conn.commit()
            return fb
    except psycopg2.errors.ForeignKeyViolation as exc:
        raise LookupError(f"Recommendation card '{card_id}' was not found.") from exc
    finally:
        conn.close()

# -------------------------------------------------------------
# Audit Logs
# -------------------------------------------------------------

def get_audit_trail_for_job(job_id: str) -> list[dict]:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM audit_events 
                WHERE parameters->>'job_id' = %s
                ORDER BY created_at DESC 
                LIMIT 100;
            """, (job_id,))
            events = [dict(r) for r in cur.fetchall()]
            return events
    finally:
        conn.close()

# -------------------------------------------------------------
# Vector Embeddings (Supabase pgvector)
# -------------------------------------------------------------

def store_insight_embedding(insight_id: int, embedding_vector: list[float]) -> None:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            embedding_str = "[" + ",".join(str(x) for x in embedding_vector) + "]"
            cur.execute("""
                INSERT INTO insight_embeddings (insight_id, embedding)
                VALUES (%s, %s::vector);
            """, (insight_id, embedding_str))
            conn.commit()
    finally:
        conn.close()

def find_similar_insights(
    embedding_vector: list[float],
    portfolio_id: str,
    limit: int = 3
) -> list[dict]:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            embedding_str = "[" + ",".join(str(x) for x in embedding_vector) + "]"
            cur.execute("""
                SELECT 
                    il.id, il.title, il.category, il.confidence_score, il.raw_json,
                    1 - (ie.embedding <=> %s::vector) AS similarity
                FROM insight_embeddings ie
                JOIN insights_log il ON il.id = ie.insight_id
                JOIN jobs j ON j.id = il.job_id
                WHERE j.portfolio_id = %s
                ORDER BY ie.embedding <=> %s::vector
                LIMIT %s;
            """, (embedding_str, portfolio_id, embedding_str, limit))
            rows = [dict(r) for r in cur.fetchall()]
            return rows
    finally:
        conn.close()
