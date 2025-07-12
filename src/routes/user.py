from flask import Blueprint, jsonify, request
from src.models.user import User, db
from src.routes.auth import login_required, admin_required

user_bp = Blueprint('user', __name__)

@user_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    try:
        users = User.query.all()
        return jsonify([user.to_dict() for user in users])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users', methods=['POST'])
@admin_required
def create_user():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if user already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Validate role
        valid_roles = ['Admin', 'Clinician', 'Office Staff']
        if data['role'] not in valid_roles:
            return jsonify({'error': 'Invalid role'}), 400
        
        user = User(
            username=data['username'], 
            email=data['email'],
            role=data['role'],
            phone=data.get('phone', '')
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        return jsonify(user.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        data = request.json
        
        # Check for unique constraints
        if 'username' in data and data['username'] != user.username:
            if User.query.filter_by(username=data['username']).first():
                return jsonify({'error': 'Username already exists'}), 400
        
        if 'email' in data and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'Email already exists'}), 400
        
        # Validate role if provided
        if 'role' in data:
            valid_roles = ['Admin', 'Clinician', 'Office Staff']
            if data['role'] not in valid_roles:
                return jsonify({'error': 'Invalid role'}), 400
        
        # Update user fields
        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        user.role = data.get('role', user.role)
        user.phone = data.get('phone', user.phone)
        user.is_active = data.get('is_active', user.is_active)
        
        # Update password if provided
        if 'password' in data:
            user.set_password(data['password'])
        
        db.session.commit()
        return jsonify(user.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@admin_required
def update_user_role(user_id):
    try:
        user = User.query.get_or_404(user_id)
        data = request.json
        
        if 'role' not in data:
            return jsonify({'error': 'Role is required'}), 400
        
        valid_roles = ['Admin', 'Clinician', 'Office Staff']
        if data['role'] not in valid_roles:
            return jsonify({'error': 'Invalid role'}), 400
        
        user.role = data['role']
        db.session.commit()
        
        return jsonify(user.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/clinicians', methods=['GET'])
@login_required
def get_clinicians():
    try:
        clinicians = User.query.filter_by(role='Clinician', is_active=True).all()
        return jsonify([user.to_dict() for user in clinicians])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

