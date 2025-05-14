from flask import Blueprint, request, jsonify, session
from app.database.connection import get_connection
from functools import wraps

credit_redemption = Blueprint('credit_redemption', __name__)

def check_redemption_enabled():
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM platform_settings WHERE key = 'enable_credit_redemption'")
        result = cursor.fetchone()
        return result and result[0] == 'true'
    except Exception:
        return False
    finally:
        cursor.close()
        conn.close()

@credit_redemption.route('/api/redemption/request', methods=['POST'])
def request_redemption():
    if not check_redemption_enabled():
        return jsonify({
            'error': 'Credit redemption is currently disabled by the administrator.'
        }), 403
    
    # ... rest of your existing redemption code ...
// ... existing code ... 