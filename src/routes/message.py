from flask import Blueprint, jsonify, request, session
from src.models.message import Message, MessageTemplate
from src.models.user import User, db
from src.routes.auth import login_required, admin_required
from datetime import datetime
import dateutil.parser

message_bp = Blueprint('message', __name__)

@message_bp.route('/messages/send', methods=['POST'])
@admin_required
def send_message():
    try:
        data = request.json
        user = User.query.get(session['user_id'])
        
        # Validate required fields
        required_fields = ['content', 'message_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Handle bulk messaging
        if 'recipient_ids' in data:
            messages = []
            for recipient_id in data['recipient_ids']:
                message = Message(
                    sender_id=user.id,
                    recipient_id=recipient_id,
                    message_type=data['message_type'],
                    content=data['content'],
                    template_id=data.get('template_id'),
                    scheduled_time=dateutil.parser.parse(data['scheduled_time']) if data.get('scheduled_time') else None
                )
                db.session.add(message)
                messages.append(message)
            
            db.session.commit()
            return jsonify([msg.to_dict() for msg in messages]), 201
        
        # Handle individual messaging
        elif 'recipient_id' in data or 'recipient_phone' in data:
            message = Message(
                sender_id=user.id,
                recipient_id=data.get('recipient_id'),
                recipient_phone=data.get('recipient_phone'),
                message_type=data['message_type'],
                content=data['content'],
                template_id=data.get('template_id'),
                scheduled_time=dateutil.parser.parse(data['scheduled_time']) if data.get('scheduled_time') else None
            )
            
            db.session.add(message)
            db.session.commit()
            return jsonify(message.to_dict()), 201
        
        else:
            return jsonify({'error': 'Either recipient_id, recipient_phone, or recipient_ids is required'}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@message_bp.route('/calls/initiate', methods=['POST'])
@admin_required
def initiate_call():
    try:
        data = request.json
        user = User.query.get(session['user_id'])
        
        # Validate required fields
        if 'recipient_id' not in data and 'recipient_phone' not in data:
            return jsonify({'error': 'Either recipient_id or recipient_phone is required'}), 400
        
        # Create call record
        call_record = Message(
            sender_id=user.id,
            recipient_id=data.get('recipient_id'),
            recipient_phone=data.get('recipient_phone'),
            message_type='Call',
            content=data.get('notes', 'Call initiated'),
            status='initiated'
        )
        
        db.session.add(call_record)
        db.session.commit()
        
        # In a real implementation, this would integrate with Twilio or similar service
        # For now, we'll just return the call record
        return jsonify({
            'message': 'Call initiated successfully',
            'call_record': call_record.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@message_bp.route('/communications/logs', methods=['GET'])
@login_required
def get_communication_logs():
    try:
        user = User.query.get(session['user_id'])
        
        # Get query parameters for filtering
        message_type = request.args.get('message_type')
        recipient_type = request.args.get('recipient_type')
        date_range = request.args.get('date_range')
        status = request.args.get('status')
        
        # Base query
        if user.role == 'Admin':
            query = Message.query
        else:
            # Non-admin users can only see their own messages
            query = Message.query.filter(
                (Message.sender_id == user.id) | (Message.recipient_id == user.id)
            )
        
        # Apply filters
        if message_type:
            query = query.filter_by(message_type=message_type)
        
        if status:
            query = query.filter_by(status=status)
        
        if date_range:
            # Simple date range filtering (last 7 days, 30 days, etc.)
            if date_range == 'week':
                start_date = datetime.now() - timedelta(days=7)
                query = query.filter(Message.created_at >= start_date)
            elif date_range == 'month':
                start_date = datetime.now() - timedelta(days=30)
                query = query.filter(Message.created_at >= start_date)
        
        messages = query.order_by(Message.created_at.desc()).all()
        return jsonify([message.to_dict() for message in messages])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/messages/schedule', methods=['POST'])
@admin_required
def schedule_message():
    try:
        data = request.json
        user = User.query.get(session['user_id'])
        
        # Validate required fields
        required_fields = ['content', 'message_type', 'scheduled_time']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        scheduled_time = dateutil.parser.parse(data['scheduled_time'])
        
        # Validate that scheduled time is in the future
        if scheduled_time <= datetime.now():
            return jsonify({'error': 'Scheduled time must be in the future'}), 400
        
        # Handle bulk scheduling
        if 'recipient_ids' in data:
            messages = []
            for recipient_id in data['recipient_ids']:
                message = Message(
                    sender_id=user.id,
                    recipient_id=recipient_id,
                    message_type=data['message_type'],
                    content=data['content'],
                    scheduled_time=scheduled_time,
                    template_id=data.get('template_id'),
                    status='scheduled'
                )
                db.session.add(message)
                messages.append(message)
            
            db.session.commit()
            return jsonify([msg.to_dict() for msg in messages]), 201
        
        # Handle individual scheduling
        elif 'recipient_id' in data or 'recipient_phone' in data:
            message = Message(
                sender_id=user.id,
                recipient_id=data.get('recipient_id'),
                recipient_phone=data.get('recipient_phone'),
                message_type=data['message_type'],
                content=data['content'],
                scheduled_time=scheduled_time,
                template_id=data.get('template_id'),
                status='scheduled'
            )
            
            db.session.add(message)
            db.session.commit()
            return jsonify(message.to_dict()), 201
        
        else:
            return jsonify({'error': 'Either recipient_id, recipient_phone, or recipient_ids is required'}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Message Templates
@message_bp.route('/templates', methods=['GET'])
@login_required
def get_templates():
    try:
        templates = MessageTemplate.query.filter_by(is_active=True).all()
        return jsonify([template.to_dict() for template in templates])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/templates', methods=['POST'])
@admin_required
def create_template():
    try:
        data = request.json
        user = User.query.get(session['user_id'])
        
        # Validate required fields
        required_fields = ['name', 'content']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        template = MessageTemplate(
            name=data['name'],
            content=data['content'],
            category=data.get('category', ''),
            created_by=user.id
        )
        
        db.session.add(template)
        db.session.commit()
        return jsonify(template.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@message_bp.route('/templates/<int:template_id>', methods=['PUT'])
@admin_required
def update_template(template_id):
    try:
        template = MessageTemplate.query.get_or_404(template_id)
        data = request.json
        
        # Update template fields
        template.name = data.get('name', template.name)
        template.content = data.get('content', template.content)
        template.category = data.get('category', template.category)
        template.is_active = data.get('is_active', template.is_active)
        
        db.session.commit()
        return jsonify(template.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@message_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@admin_required
def delete_template(template_id):
    try:
        template = MessageTemplate.query.get_or_404(template_id)
        # Soft delete - mark as inactive
        template.is_active = False
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

