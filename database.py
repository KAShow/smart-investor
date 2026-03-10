import json
import sqlite3
import uuid
from pathlib import Path

DB_PATH = Path(__file__).parent / "analyses.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea TEXT NOT NULL,
            market_analysis TEXT,
            financial_analysis TEXT,
            competitive_analysis TEXT,
            legal_analysis TEXT,
            technical_analysis TEXT,
            swot_analysis TEXT,
            action_plan TEXT,
            final_verdict TEXT,
            share_token TEXT UNIQUE,
            user_rating INTEGER,
            user_feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # جدول تخزين بيانات البحرين المفتوحة محلياً
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

    # Migrate existing table if needed
    cursor = conn.execute("PRAGMA table_info(analyses)")
    columns = [row['name'] for row in cursor.fetchall()]
    new_columns = {
        'legal_analysis': 'TEXT',
        'technical_analysis': 'TEXT',
        'swot_analysis': 'TEXT',
        'action_plan': 'TEXT',
        'share_token': 'TEXT',
        'user_rating': 'INTEGER',
        'user_feedback': 'TEXT',
        'sector': 'TEXT DEFAULT \'general\'',
    }
    for col, col_type in new_columns.items():
        if col not in columns:
            conn.execute(f"ALTER TABLE analyses ADD COLUMN {col} {col_type}")
    conn.commit()
    conn.close()


def save_analysis(idea, market_analysis, financial_analysis, competitive_analysis,
                  final_verdict, legal_analysis='', technical_analysis='',
                  swot_analysis='', action_plan='', sector='general'):
    share_token = uuid.uuid4().hex[:12]
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO analyses (idea, market_analysis, financial_analysis, competitive_analysis,
           legal_analysis, technical_analysis, swot_analysis, action_plan, final_verdict, share_token, sector)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (idea, market_analysis, financial_analysis, competitive_analysis,
         legal_analysis, technical_analysis, swot_analysis, action_plan, final_verdict, share_token, sector)
    )
    analysis_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return analysis_id


def get_all_analyses():
    conn = get_connection()
    rows = conn.execute("SELECT id, idea, created_at FROM analyses ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_analysis(analysis_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_analysis_by_token(token):
    conn = get_connection()
    row = conn.execute("SELECT * FROM analyses WHERE share_token = ?", (token,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_analysis(analysis_id):
    conn = get_connection()
    conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    conn.commit()
    conn.close()


def rate_analysis(analysis_id, rating, feedback=''):
    conn = get_connection()
    conn.execute("UPDATE analyses SET user_rating = ?, user_feedback = ? WHERE id = ?",
                 (rating, feedback, analysis_id))
    conn.commit()
    conn.close()


def get_dashboard_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as count FROM analyses").fetchone()['count']
    avg_rating = conn.execute("SELECT AVG(user_rating) as avg FROM analyses WHERE user_rating IS NOT NULL").fetchone()['avg']

    # Verdict distribution
    verdicts = {}
    rows = conn.execute("SELECT final_verdict FROM analyses WHERE final_verdict IS NOT NULL").fetchall()
    for row in rows:
        try:
            data = json.loads(row['final_verdict'])
            v = data.get('verdict', 'غير محدد')
            verdicts[v] = verdicts.get(v, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass

    # Recent analyses with scores
    recent = conn.execute(
        "SELECT id, idea, final_verdict, created_at FROM analyses ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    recent_list = []
    for r in recent:
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


# ─── دوال بيانات البحرين المفتوحة ───

def save_bahrain_data(dataset_name, dataset_id, data_json, record_count):
    """حفظ/تحديث بيانات dataset في الكاش المحلي."""
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO bahrain_data_cache
        (dataset_id, dataset_name, data_json, record_count, fetched_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (dataset_name, dataset_id, data_json, record_count))
    conn.commit()
    conn.close()


def get_bahrain_data(dataset_name):
    """جلب بيانات dataset من الكاش المحلي."""
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
    """حالة آخر تحديث لكل dataset."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT dataset_id, dataset_name, record_count, fetched_at FROM bahrain_data_cache"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def has_bahrain_data():
    """هل توجد بيانات بحرينية مخزنة محلياً؟"""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) as c FROM bahrain_data_cache").fetchone()['c']
    conn.close()
    return count > 0
