from src.models.user import db
from datetime import datetime

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_phone = db.Column(db.String(20))  # For external recipients
    message_type = db.Column(db.String(10), default='SMS')  # SMS, Call
    content = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, sent, delivered, failed
    scheduled_time = db.Column(db.DateTime)
    sent_time = db.Column(db.DateTime)
    template_id = db.Column(db.Integer, db.ForeignKey('message_template.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
    template = db.relationship('MessageTemplate', backref='template_messages')

    def __repr__(self):
        return f'<Message {self.id} - {self.message_type}>'

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.username if self.sender else None,
            'recipient_id': self.recipient_id,
            'recipient_name': self.recipient.username if self.recipient else None,
            'recipient_phone': self.recipient_phone,
            'message_type': self.message_type,
            'content': self.content,
            'status': self.status,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'sent_time': self.sent_time.isoformat() if self.sent_time else None,
            'template_id': self.template_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class MessageTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))  # reminder, follow-up, etc.
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationship
    creator = db.relationship('User', backref='created_message_templates')

    def __repr__(self):
        return f'<MessageTemplate {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'category': self.category,
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }

