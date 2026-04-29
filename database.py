"""SQLite-backed persistence for analyses, Bahrain data cache, and source cache.

Hardened for production:
- WAL journaling and NORMAL synchronous for concurrent SSE workers
- secrets.token_urlsafe for share tokens (256 bits)
- Encrypted requester_email at rest via Fernet (utils/crypto.py)
- Owner scoping by Supabase user_id
- Background cleanup of expired share tokens
"""
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

from config import Config
from utils.tokens import generate_share_token
from utils.crypto import encrypt_pii, decrypt_pii

DB_PATH = Config.DB_PATH

_init_lock = threading.Lock()
_initialized = False


def get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    global _initialized
    with _init_lock:
        if _initialized:
            return
        conn = get_connection()
        conn.execute("""
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
            )
        """)
        conn.commit()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS bahrain_data_cache (
                dataset_id TEXT PRIMARY KEY,
                dataset_name TEXT,
                data_json TEXT,
                record_count INTEGER DEFAULT 0,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                sector TEXT NOT NULL,
                cache_key TEXT NOT NULL UNIQUE,
                data_json TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)
        conn.commit()

        # Migrate legacy plaintext column → encrypted column.
        # The legacy column `requester_email` (plaintext) lives alongside the new
        # `requester_email_enc` until manual cleanup. Reads prefer the encrypted column.
        cursor = conn.execute("PRAGMA table_info(analyses)")
        columns = {row['name'] for row in cursor.fetchall()}
        for col, col_type in {
            'user_id': 'TEXT',
            'requester_email_enc': 'TEXT',
            'brokerage_models_analysis': 'TEXT',
        }.items():
            if col not in columns:
                conn.execute(f"ALTER TABLE analyses ADD COLUMN {col} {col_type}")
        conn.commit()

        # Index for owner queries and token lookups.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_id, created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_token ON analyses(share_token)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_valid_until ON analyses(valid_until)")
        conn.commit()
        conn.close()
        _initialized = True


def _generate_report_number(conn):
    year = datetime.now().year
    row = conn.execute(
        "SELECT COUNT(*) as c FROM analyses WHERE report_number IS NOT NULL AND report_number LIKE ?",
        (f"BSI-{year}-%",)
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
    conn = get_connection()
    report_number = _generate_report_number(conn)
    cursor = conn.execute(
        """INSERT INTO analyses (
            user_id, idea, sector, market_analysis, financial_analysis,
            competitive_analysis, legal_analysis, technical_analysis,
            brokerage_models_analysis, swot_analysis, action_plan,
            final_verdict, share_token, report_number,
            requester_name, requester_email_enc, requester_company, valid_until
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, idea, sector, market_analysis, financial_analysis,
         competitive_analysis, legal_analysis, technical_analysis,
         brokerage_models_analysis, swot_analysis, action_plan,
         final_verdict, share_token, report_number,
         requester_name, email_enc, requester_company, valid_until)
    )
    analysis_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return analysis_id


def _row_to_dict(row):
    if not row:
        return None
    d = dict(row)
    if 'requester_email_enc' in d:
        d['requester_email'] = decrypt_pii(d.pop('requester_email_enc'))
    return d


def list_analyses_for_user(user_id: str, limit: int = 50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, idea, sector, created_at, report_number, share_token, valid_until "
        "FROM analyses WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_analysis(analysis_id, user_id: str | None = None):
    """Get analysis by id. If user_id is provided, scope to that owner."""
    conn = get_connection()
    if user_id:
        row = conn.execute(
            "SELECT * FROM analyses WHERE id = ? AND user_id = ?",
            (analysis_id, user_id)
        ).fetchone()
    else:
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def get_analysis_by_token(token: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM analyses WHERE share_token = ?", (token,)).fetchone()
    conn.close()
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


def delete_analysis(analysis_id, user_id: str | None = None):
    conn = get_connection()
    if user_id:
        conn.execute("DELETE FROM analyses WHERE id = ? AND user_id = ?", (analysis_id, user_id))
    else:
        conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    conn.commit()
    conn.close()


def rate_analysis(analysis_id, rating, feedback='', user_id: str | None = None):
    conn = get_connection()
    if user_id:
        conn.execute(
            "UPDATE analyses SET user_rating = ?, user_feedback = ? WHERE id = ? AND user_id = ?",
            (rating, feedback, analysis_id, user_id)
        )
    else:
        conn.execute(
            "UPDATE analyses SET user_rating = ?, user_feedback = ? WHERE id = ?",
            (rating, feedback, analysis_id)
        )
    conn.commit()
    conn.close()


def cleanup_expired_analyses() -> int:
    """Delete analyses whose share token has expired. Returns count deleted."""
    conn = get_connection()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor = conn.execute(
        "DELETE FROM analyses WHERE valid_until IS NOT NULL AND valid_until < ?",
        (now,)
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def get_dashboard_stats(user_id: str | None = None):
    conn = get_connection()
    if user_id:
        total = conn.execute(
            "SELECT COUNT(*) as count FROM analyses WHERE user_id = ?", (user_id,)
        ).fetchone()['count']
        avg_rating = conn.execute(
            "SELECT AVG(user_rating) as avg FROM analyses WHERE user_rating IS NOT NULL AND user_id = ?",
            (user_id,)
        ).fetchone()['avg']
        recent_rows = conn.execute(
            "SELECT id, idea, final_verdict, created_at FROM analyses "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
            (user_id,)
        ).fetchall()
        verdict_rows = conn.execute(
            "SELECT final_verdict FROM analyses WHERE final_verdict IS NOT NULL AND user_id = ?",
            (user_id,)
        ).fetchall()
    else:
        total = conn.execute("SELECT COUNT(*) as count FROM analyses").fetchone()['count']
        avg_rating = conn.execute(
            "SELECT AVG(user_rating) as avg FROM analyses WHERE user_rating IS NOT NULL"
        ).fetchone()['avg']
        recent_rows = conn.execute(
            "SELECT id, idea, final_verdict, created_at FROM analyses ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
        verdict_rows = conn.execute(
            "SELECT final_verdict FROM analyses WHERE final_verdict IS NOT NULL"
        ).fetchall()

    verdicts = {}
    for row in verdict_rows:
        try:
            data = json.loads(row['final_verdict'])
            v = data.get('verdict', 'غير محدد')
            verdicts[v] = verdicts.get(v, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass

    recent_list = []
    for r in recent_rows:
        score = 0
        try:
            data = json.loads(r['final_verdict'])
            score = data.get('overall_score', 0)
        except (json.JSONDecodeError, TypeError):
            pass
        recent_list.append({
            'id': r['id'], 'idea': r['idea'][:80],
            'score': score, 'created_at': r['created_at']
        })

    conn.close()
    return {
        'total_analyses': total,
        'average_rating': round(avg_rating, 1) if avg_rating else 0,
        'verdict_distribution': verdicts,
        'recent': recent_list
    }


# ── Bahrain open data cache ────────────────────────────────────────────────

def save_bahrain_data(dataset_name, dataset_id, data_json, record_count):
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO bahrain_data_cache
        (dataset_id, dataset_name, data_json, record_count, fetched_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (dataset_name, dataset_id, data_json, record_count))
    conn.commit()
    conn.close()


def get_bahrain_data(dataset_name):
    conn = get_connection()
    row = conn.execute(
        "SELECT data_json FROM bahrain_data_cache WHERE dataset_id = ?",
        (dataset_name,)
    ).fetchone()
    conn.close()
    if row and row['data_json']:
        try:
            return json.loads(row['data_json'])
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def get_bahrain_data_status():
    conn = get_connection()
    rows = conn.execute(
        "SELECT dataset_id, dataset_name, record_count, fetched_at FROM bahrain_data_cache"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def has_bahrain_data():
    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) as c FROM bahrain_data_cache").fetchone()['c']
    except Exception:
        count = 0
    finally:
        conn.close()
    return count > 0


# ── Per-source TTL cache ───────────────────────────────────────────────────

def save_data_cache(source_name, sector, data_dict, ttl_seconds):
    cache_key = f"{source_name}:{sector}"
    expires_at = (datetime.now() + timedelta(seconds=ttl_seconds)).strftime('%Y-%m-%d %H:%M:%S')
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO data_cache
        (source_name, sector, cache_key, data_json, fetched_at, expires_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
    """, (source_name, sector, cache_key, json.dumps(data_dict, ensure_ascii=False), expires_at))
    conn.commit()
    conn.close()


def get_data_cache(source_name, sector):
    cache_key = f"{source_name}:{sector}"
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_connection()
    row = conn.execute(
        "SELECT data_json FROM data_cache WHERE cache_key = ? AND expires_at > ?",
        (cache_key, now)
    ).fetchone()
    conn.close()
    if row and row['data_json']:
        try:
            return json.loads(row['data_json'])
        except (json.JSONDecodeError, TypeError):
            return None
    return None
