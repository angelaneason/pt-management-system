from flask import Blueprint, jsonify, request
from src.models.client import Client
from src.models.user import db
from src.routes.auth import login_required, admin_required

client_bp = Blueprint('client', __name__)

@client_bp.route('/clients', methods=['GET'])
@login_required
def get_clients():
    try:
        clients = Client.query.filter_by(is_active=True).all()
        return jsonify([client.to_dict() for client in clients])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@client_bp.route('/clients', methods=['POST'])
@login_required
def create_client():
    try:
        data = request.json
        
        # Validate required fields
        if 'name' not in data:
            return jsonify({'error': 'Name is required'}), 400
        
        client = Client(
            name=data['name'],
            contact_info=data.get('contact_info', ''),
            color_code=data.get('color_code', '#3B82F6')
        )
        
        db.session.add(client)
        db.session.commit()
        return jsonify(client.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@client_bp.route('/clients/<int:client_id>', methods=['GET'])
@login_required
def get_client(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        return jsonify(client.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@client_bp.route('/clients/<int:client_id>', methods=['PUT'])
@login_required
def update_client(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        data = request.json
        
        # Update client fields
        client.name = data.get('name', client.name)
        client.contact_info = data.get('contact_info', client.contact_info)
        client.color_code = data.get('color_code', client.color_code)
        client.is_active = data.get('is_active', client.is_active)
        
        db.session.commit()
        return jsonify(client.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@client_bp.route('/clients/<int:client_id>', methods=['DELETE'])
@admin_required
def delete_client(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        # Soft delete - mark as inactive instead of deleting
        client.is_active = False
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@client_bp.route('/clients/<int:client_id>/color', methods=['PUT'])
@admin_required
def update_client_color(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        data = request.json
        
        if 'color_code' not in data:
            return jsonify({'error': 'Color code is required'}), 400
        
        # Validate color code format (hex color)
        color_code = data['color_code']
        if not color_code.startswith('#') or len(color_code) != 7:
            return jsonify({'error': 'Invalid color code format. Use #RRGGBB format'}), 400
        
        client.color_code = color_code
        db.session.commit()
        
        return jsonify(client.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

