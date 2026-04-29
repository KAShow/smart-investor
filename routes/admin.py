"""Admin endpoints — restricted to ADMIN_USER_IDS."""
import logging

from flask import Blueprint, jsonify

from auth import require_admin
from bahrain_data import BahrainDataService, refresh_sectors_cache
from database import cleanup_expired_analyses, get_bahrain_data_status

logger = logging.getLogger(__name__)
bp = Blueprint('admin', __name__)
_bahrain_service = BahrainDataService()


@bp.route('/sync-data', methods=['POST'])
@require_admin
def sync_data():
    try:
        count = _bahrain_service.sync_all_data()
        return jsonify({'success': True, 'message': f'تم تحديث {count} مجموعة بيانات'})
    except Exception as e:
        logger.error(f"Data sync failed: {e}")
        return jsonify({'error': 'فشل تحديث البيانات'}), 500


@bp.route('/data-status', methods=['GET'])
@require_admin
def data_status():
    return jsonify(get_bahrain_data_status())


@bp.route('/sectors/refresh', methods=['POST'])
@require_admin
def refresh_sectors():
    sectors = refresh_sectors_cache()
    return jsonify({'success': True, 'count': len(sectors)})


@bp.route('/cleanup-expired', methods=['POST'])
@require_admin
def cleanup_expired():
    deleted = cleanup_expired_analyses()
    return jsonify({'success': True, 'deleted': deleted})
