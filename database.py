"""Persistence layer — Postgres (Supabase) in production, SQLite locally.

Selection: if Config.DATABASE_URL is set, all reads/writes go to Postgres
through psycopg. Otherwise falls back to SQLite at Config.DB_PATH for local
development. Schema lives in migrations/001_initial_schema.sql for Postgres
and is auto-created here for SQLite.

Hardened for production:
- secrets.token_urlsafe for share tokens (256 bits)
- Encrypted requester_email at rest via Fernet (utils/crypto.py)
- Owner scoping by Supabase user_id
- Background cleanup of expired share tokens
"""
import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

from config import Config
from utils.tokens import generate_share_token
from utils.crypto import encrypt_pii, decrypt_pii

logger = logging.getLogger(__name__)

DB_PATH = Config.DB_PATH
USE_POSTGRES = bool(Config.DATABASE_URL)

if USE_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row

_init_lock = threading.Lock()
_initialized = False


# ── Connection helpers ────────────────────────────────────────────────────

def get_connection():
    if USE_POSTGRES:
        # Each request gets its own connection. The Supabase pooler (Supavisor
        # in transaction mode) handles pooling on the server side, so a fresh
        # client connection per request is appropriate.
        return psycopg.connect(Config.DATABASE_URL, row_factory=dict_row)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _q(sql: str) -> str:
    """Translate `?` to `%s` for Postgres; pass through for SQLite."""
    return sql.replace('?', '%s') if USE_POSTGRES else sql


def _execute(conn, sql: str, params=()):
    """Run a query, returning the cursor. Always uses _q() to translate placeholders."""
    cur = conn.cursor() if USE_POSTGRES else conn
    cur.execute(_q(sql), params)
    return cur


def _execute_returning_id(conn, sql: str, params=()) -> int:
    """INSERT and return the new row's id, working across both backends."""
    if USE_POSTGRES:
        cur = conn.cursor()
        cur.execute(_q(sql) + " RETURNING id", params)
        row = cur.fetchone()
        return row['id']
    cursor = conn.execute(sql, params)
    return cursor.lastrowid


def _row_to_dict(row):
    if not row:
        return None
    d = dict(row) if not isinstance(row, dict) else row
    if 'requester_email_enc' in d:
        d['requester_email'] = decrypt_pii(d.pop('requester_email_enc'))
    # Normalize timestamps to ISO strings so consumers (PDF, JSON serializer)
    # don't have to handle datetime objects from Postgres vs strings from SQLite.
    for key in ('valid_until', 'created_at', 'fetched_at', 'expires_at'):
        if key in d and isinstance(d[key], datetime):
            d[key] = d[key].strftime('%Y-%m-%d %H:%M:%S')
    return d


# ── Schema initialization ─────────────────────────────────────────────────

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    user_rating INTEGER,
    user_feedback TEXT,
    requester_name TEXT,
    requester_email_enc TEXT,
    requester_company TEXT,
    valid_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_token ON analyses(share_token);
CREATE INDEX IF NOT EXISTS idx_analyses_valid_until ON analyses(valid_until);

CREATE TABLE IF NOT EXISTS bahrain_data_cache (
    dataset_id TEXT PRIMARY KEY,
    dataset_name TEXT,
    data_json TEXT,
    record_count INTEGER DEFAULT 0,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    sector TEXT NOT NULL,
    cache_key TEXT NOT NULL UNIQUE,
    data_json TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
"""


def init_db():
    """Create tables if missing.

    For Postgres we assume migrations/001_initial_schema.sql has already run
    in Supabase. We only verify connectivity here.
    For SQLite we create tables locally.
    """
    global _initialized
    with _init_lock:
        if _initialized:
            return
        if USE_POSTGRES:
            try:
                with get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                logger.info("✅ Connected to Postgres (Supabase) for persistence")
            except Exception as e:
                logger.error(f"❌ Postgres connection failed: {e}")
                raise
            _initialized = True
            return

        # SQLite path — create tables locally
        conn = get_connection()
        for stmt in _SQLITE_SCHEMA.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(s)
        conn.commit()
        conn.close()
        logger.info(f"✅ SQLite initialized at {DB_PATH}")
        _initialized = True


# ── Analyses ──────────────────────────────────────────────────────────────

def _generate_report_number(conn) -> str:
    year = datetime.now().year
    pattern = f"BSI-{year}-%"
    if USE_POSTGRES:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM analyses WHERE report_number LIKE %s", (pattern,))
        row = cur.fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM analyses WHERE report_number IS NOT NULL AND report_number LIKE ?",
            (pattern,)
        ).fetchone()
    seq = (row['c'] if row else 0) + 1
    return f"BSI-{year}-{seq:05d}"


def save_analysis(idea, market_analysis, financial_analysis, competitive_analysis,
                  final_verdict, legal_analysis='', technical_analysis='',
                  brokerage_models_analysis='', swot_analysis='', action_plan='',
                  sector='general', user_id='', requester_name='',
                  requester_email='', requester_company=''):
    share_token = generate_share_token()
    valid_until = (datetime.now() + timedelta(days=Config.SHARE_TOKEN_EXPIRY_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
    email_enc = encrypt_pii(requester_email)

    sql = """INSERT INTO analyses (
        user_id, idea, sector, market_analysis, financial_analysis,
        competitive_analysis, legal_analysis, technical_analysis,
        brokerage_models_analysis, swot_analysis, action_plan,
        final_verdict, share_token, report_number,
        requester_name, requester_email_enc, requester_company, valid_until
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    conn = get_connection()
    try:
        report_number = _generate_report_number(conn)
        params = (user_id, idea, sector, market_analysis, financial_analysis,
                  competitive_analysis, legal_analysis, technical_analysis,
                  brokerage_models_analysis, swot_analysis, action_plan,
                  final_verdict, share_token, report_number,
                  requester_name, email_enc, requester_company, valid_until)
        analysis_id = _execute_returning_id(conn, sql, params)
        conn.commit()
        return analysis_id
    finally:
        conn.close()


def list_analyses_for_user(user_id: str, limit: int = 50):
    sql = ("SELECT id, idea, sector, created_at, report_number, share_token, valid_until "
           "FROM analyses WHERE user_id = ? ORDER BY created_at DESC LIMIT ?")
    conn = get_connection()
    try:
        if USE_POSTGRES:
            cur = conn.cursor()
            cur.execute(_q(sql), (user_id, limit))
            rows = cur.fetchall()
        else:
            rows = conn.execute(sql, (user_id, limit)).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_analysis(analysis_id, user_id: str | None = None):
    """Get analysis by id. If user_id is provided, scope to that owner."""
    conn = get_connection()
    try:
        if user_id:
            sql = "SELECT * FROM analyses WHERE id = ? AND user_id = ?"
            params = (analysis_id, user_id)
        else:
            sql = "SELECT * FROM analyses WHERE id = ?"
            params = (analysis_id,)
        if USE_POSTGRES:
            cur = conn.cursor()
            cur.execute(_q(sql), params)
            row = cur.fetchone()
        else:
            row = conn.execute(sql, params).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_analysis_by_token(token: str):
    conn = get_connection()
    try:
        sql = "SELECT * FROM analyses WHERE share_token = ?"
        if USE_POSTGRES:
            cur = conn.cursor()
            cur.execute(_q(sql), (token,))
            row = cur.fetchone()
        else:
            row = conn.execute(sql, (token,)).fetchone()
        if not row:
            return None
        result = _row_to_dict(row)
        if result.get('valid_until'):
            try:
                expiry = datetime.strptime(result['valid_until'], '%Y-%m-%d %H:%M:%S')
                if datetime.now() > expiry:
                    return None
            except (ValueError, TypeError):
                pass
        return result
    finally:
        conn.close()


def delete_analysis(analysis_id, user_id: str | None = None):
    conn = get_connection()
    try:
        if user_id:
            sql = "DELETE FROM analyses WHERE id = ? AND user_id = ?"
            params = (analysis_id, user_id)
        else:
            sql = "DELETE FROM analyses WHERE id = ?"
            params = (analysis_id,)
        _execute(conn, sql, params)
        conn.commit()
    finally:
        conn.close()


def rate_analysis(analysis_id, rating, feedback='', user_id: str | None = None):
    conn = get_connection()
    try:
        if user_id:
            sql = "UPDATE analyses SET user_rating = ?, user_feedback = ? WHERE id = ? AND user_id = ?"
            params = (rating, feedback, analysis_id, user_id)
        else:
            sql = "UPDATE analyses SET user_rating = ?, user_feedback = ? WHERE id = ?"
            params = (rating, feedback, analysis_id)
        _execute(conn, sql, params)
        conn.commit()
    finally:
        conn.close()


def cleanup_expired_analyses() -> int:
    """Delete analyses whose share token has expired. Returns count deleted."""
    conn = get_connection()
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sql = "DELETE FROM analyses WHERE valid_until IS NOT NULL AND valid_until < ?"
        if USE_POSTGRES:
            cur = conn.cursor()
            cur.execute(_q(sql), (now,))
            deleted = cur.rowcount
        else:
            cursor = conn.execute(sql, (now,))
            deleted = cursor.rowcount
        conn.commit()
        return deleted
    finally:
        conn.close()


def get_dashboard_stats(user_id: str | None = None):
    conn = get_connection()
    try:
        if USE_POSTGRES:
            cur = conn.cursor()
            if user_id:
                cur.execute(_q("SELECT COUNT(*) AS count FROM analyses WHERE user_id = ?"), (user_id,))
                total = cur.fetchone()['count']
                cur.execute(_q("SELECT AVG(user_rating) AS avg FROM analyses WHERE user_rating IS NOT NULL AND user_id = ?"), (user_id,))
                avg_rating = cur.fetchone()['avg']
                cur.execute(_q("SELECT id, idea, final_verdict, created_at FROM analyses WHERE user_id = ? ORDER BY created_at DESC LIMIT 10"), (user_id,))
                recent_rows = cur.fetchall()
                cur.execute(_q("SELECT final_verdict FROM analyses WHERE final_verdict IS NOT NULL AND user_id = ?"), (user_id,))
                verdict_rows = cur.fetchall()
            else:
                cur.execute("SELECT COUNT(*) AS count FROM analyses")
                total = cur.fetchone()['count']
                cur.execute("SELECT AVG(user_rating) AS avg FROM analyses WHERE user_rating IS NOT NULL")
                avg_rating = cur.fetchone()['avg']
                cur.execute("SELECT id, idea, final_verdict, created_at FROM analyses ORDER BY created_at DESC LIMIT 10")
                recent_rows = cur.fetchall()
                cur.execute("SELECT final_verdict FROM analyses WHERE final_verdict IS NOT NULL")
                verdict_rows = cur.fetchall()
        else:
            if user_id:
                total = conn.execute("SELECT COUNT(*) as count FROM analyses WHERE user_id = ?", (user_id,)).fetchone()['count']
                avg_rating = conn.execute("SELECT AVG(user_rating) as avg FROM analyses WHERE user_rating IS NOT NULL AND user_id = ?", (user_id,)).fetchone()['avg']
                recent_rows = conn.execute("SELECT id, idea, final_verdict, created_at FROM analyses WHERE user_id = ? ORDER BY created_at DESC LIMIT 10", (user_id,)).fetchall()
                verdict_rows = conn.execute("SELECT final_verdict FROM analyses WHERE final_verdict IS NOT NULL AND user_id = ?", (user_id,)).fetchall()
            else:
                total = conn.execute("SELECT COUNT(*) as count FROM analyses").fetchone()['count']
                avg_rating = conn.execute("SELECT AVG(user_rating) as avg FROM analyses WHERE user_rating IS NOT NULL").fetchone()['avg']
                recent_rows = conn.execute("SELECT id, idea, final_verdict, created_at FROM analyses ORDER BY created_at DESC LIMIT 10").fetchall()
                verdict_rows = conn.execute("SELECT final_verdict FROM analyses WHERE final_verdict IS NOT NULL").fetchall()

        verdicts = {}
        for row in verdict_rows:
            try:
                fv = row['final_verdict'] if isinstance(row, dict) else row['final_verdict']
                data = json.loads(fv)
                v = data.get('verdict', 'غير محدد')
                verdicts[v] = verdicts.get(v, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass

        recent_list = []
        for r in recent_rows:
            score = 0
            try:
                fv = r['final_verdict'] if isinstance(r, dict) else r['final_verdict']
                data = json.loads(fv)
                score = data.get('overall_score', 0)
            except (json.JSONDecodeError, TypeError):
                pass
            created = r['created_at']
            if isinstance(created, datetime):
                created = created.strftime('%Y-%m-%d %H:%M:%S')
            recent_list.append({
                'id': r['id'], 'idea': r['idea'][:80],
                'score': score, 'created_at': created
            })

        return {
            'total_analyses': total or 0,
            'average_rating': round(float(avg_rating), 1) if avg_rating else 0,
            'verdict_distribution': verdicts,
            'recent': recent_list
        }
    finally:
        conn.close()


# ── Bahrain open data cache ────────────────────────────────────────────────

def save_bahrain_data(dataset_name, dataset_id, data_json, record_count):
    conn = get_connection()
    try:
        if USE_POSTGRES:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO bahrain_data_cache (dataset_id, dataset_name, data_json, record_count, fetched_at)
                   VALUES (%s, %s, %s, %s, NOW())
                   ON CONFLICT (dataset_id) DO UPDATE SET
                     dataset_name = EXCLUDED.dataset_name,
                     data_json = EXCLUDED.data_json,
                     record_count = EXCLUDED.record_count,
                     fetched_at = NOW()""",
                (dataset_name, dataset_id, data_json, record_count)
            )
        else:
            conn.execute(
                """INSERT OR REPLACE INTO bahrain_data_cache
                   (dataset_id, dataset_name, data_json, record_count, fetched_at)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (dataset_name, dataset_id, data_json, record_count)
            )
        conn.commit()
    finally:
        conn.close()


def get_bahrain_data(dataset_name):
    conn = get_connection()
    try:
        sql = "SELECT data_json FROM bahrain_data_cache WHERE dataset_id = ?"
        if USE_POSTGRES:
            cur = conn.cursor()
            cur.execute(_q(sql), (dataset_name,))
            row = cur.fetchone()
        else:
            row = conn.execute(sql, (dataset_name,)).fetchone()
        if row and row['data_json']:
            try:
                return json.loads(row['data_json'])
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    finally:
        conn.close()


def get_bahrain_data_status():
    conn = get_connection()
    try:
        sql = "SELECT dataset_id, dataset_name, record_count, fetched_at FROM bahrain_data_cache"
        if USE_POSTGRES:
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
        else:
            rows = conn.execute(sql).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def has_bahrain_data():
    conn = get_connection()
    try:
        sql = "SELECT COUNT(*) AS c FROM bahrain_data_cache"
        if USE_POSTGRES:
            cur = conn.cursor()
            cur.execute(sql)
            row = cur.fetchone()
        else:
            row = conn.execute(sql).fetchone()
        return (row['c'] or 0) > 0
    except Exception:
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── Per-source TTL cache ───────────────────────────────────────────────────

def save_data_cache(source_name, sector, data_dict, ttl_seconds):
    cache_key = f"{source_name}:{sector}"
    expires_at = (datetime.now() + timedelta(seconds=ttl_seconds)).strftime('%Y-%m-%d %H:%M:%S')
    payload = json.dumps(data_dict, ensure_ascii=False)
    conn = get_connection()
    try:
        if USE_POSTGRES:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO data_cache (source_name, sector, cache_key, data_json, fetched_at, expires_at)
                   VALUES (%s, %s, %s, %s, NOW(), %s)
                   ON CONFLICT (cache_key) DO UPDATE SET
                     source_name = EXCLUDED.source_name,
                     sector = EXCLUDED.sector,
                     data_json = EXCLUDED.data_json,
                     fetched_at = NOW(),
                     expires_at = EXCLUDED.expires_at""",
                (source_name, sector, cache_key, payload, expires_at)
            )
        else:
            conn.execute(
                """INSERT OR REPLACE INTO data_cache
                   (source_name, sector, cache_key, data_json, fetched_at, expires_at)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)""",
                (source_name, sector, cache_key, payload, expires_at)
            )
        conn.commit()
    finally:
        conn.close()


def get_data_cache(source_name, sector):
    cache_key = f"{source_name}:{sector}"
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_connection()
    try:
        sql = "SELECT data_json FROM data_cache WHERE cache_key = ? AND expires_at > ?"
        if USE_POSTGRES:
            cur = conn.cursor()
            cur.execute(_q(sql), (cache_key, now))
            row = cur.fetchone()
        else:
            row = conn.execute(sql, (cache_key, now)).fetchone()
        if row and row['data_json']:
            try:
                return json.loads(row['data_json'])
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    finally:
        conn.close()
