from flask import Blueprint, request, jsonify

admin_settings = Blueprint('admin_settings', __name__)

@admin_settings.route('/api/admin/settings', methods=['GET'])
def get_settings():
    return jsonify({'message': 'Admin settings API endpoint'})