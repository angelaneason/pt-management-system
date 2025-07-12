"""
Tenant-specific user models for the Physical Therapy Management System.

This module contains user-related models that exist within tenant schemas,
providing tenant-specific user profiles and preferences while maintaining
global authentication in the public schema.
"""

from src.models.public import db
from datetime import datetime

class TenantUserProfile(db.Model):
    """
    Tenant-specific user profile information.
    This model exists in each tenant schema and contains
    organization-specific user data and preferences.
    """
    __tablename__ = 'user_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # References public.user.id
    
    # Professional information
    title = db.Column(db.String(50))  # Dr., PT, PTA, etc.
    license_number = db.Column(db.String(50))
    license_state = db.Column(db.String(50))
    license_expiry = db.Column(db.Date)
    
    # Employment information
    employee_id = db.Column(db.String(50))
    department = db.Column(db.String(100))
    hire_date = db.Column(db.Date)
    employment_status = db.Column(db.String(20), default='active')  # active, inactive, terminated
    
    # Practice-specific role and permissions
    practice_role = db.Column(db.String(50), default='Clinician')
    specializations = db.Column(db.JSON)  # Array of specialization areas
    certifications = db.Column(db.JSON)  # Array of certifications
    
    # Scheduling preferences
    default_appointment_duration = db.Column(db.Integer, default=60)  # minutes
    max_daily_appointments = db.Column(db.Integer, default=8)
    preferred_start_time = db.Column(db.Time)
    preferred_end_time = db.Column(db.Time)
    working_days = db.Column(db.JSON)  # Array of working days
    
    # Communication preferences
    email_notifications = db.Column(db.Boolean, default=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    notification_preferences = db.Column(db.JSON)
    
    # UI preferences
    theme = db.Column(db.String(20), default='light')
    language = db.Column(db.String(10), default='en')
    timezone = db.Column(db.String(50))
    date_format = db.Column(db.String(20))
    time_format = db.Column(db.String(10))
    
    # Performance metrics
    total_patients_treated = db.Column(db.Integer, default=0)
    total_appointments_completed = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float)
    
    # Status and metadata
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<TenantUserProfile {self.user_id}>'
    
    def get_full_title(self):
        """Get the user's full professional title"""
        if self.title:
            return self.title
        return self.practice_role
    
    def is_licensed_professional(self):
        """Check if user is a licensed healthcare professional"""
        licensed_roles = ['Physical Therapist', 'PT', 'Occupational Therapist', 'OT']
        return self.practice_role in licensed_roles or (self.license_number is not None)
    
    def get_working_days_list(self):
        """Get working days as a list"""
        if self.working_days:
            return self.working_days
        return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']  # Default
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'license_number': self.license_number,
            'license_state': self.license_state,
            'license_expiry': self.license_expiry.isoformat() if self.license_expiry else None,
            'employee_id': self.employee_id,
            'department': self.department,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'employment_status': self.employment_status,
            'practice_role': self.practice_role,
            'specializations': self.specializations,
            'certifications': self.certifications,
            'default_appointment_duration': self.default_appointment_duration,
            'max_daily_appointments': self.max_daily_appointments,
            'preferred_start_time': self.preferred_start_time.isoformat() if self.preferred_start_time else None,
            'preferred_end_time': self.preferred_end_time.isoformat() if self.preferred_end_time else None,
            'working_days': self.working_days,
            'email_notifications': self.email_notifications,
            'sms_notifications': self.sms_notifications,
            'notification_preferences': self.notification_preferences,
            'theme': self.theme,
            'language': self.language,
            'timezone': self.timezone,
            'date_format': self.date_format,
            'time_format': self.time_format,
            'total_patients_treated': self.total_patients_treated,
            'total_appointments_completed': self.total_appointments_completed,
            'average_rating': self.average_rating,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UserSession(db.Model):
    """
    Track user sessions within a tenant context.
    """
    __tablename__ = 'user_session'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # References public.user.id
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    
    # Session information
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.Text)
    device_type = db.Column(db.String(50))  # desktop, mobile, tablet
    browser = db.Column(db.String(100))
    
    # Session status
    is_active = db.Column(db.Boolean, default=True)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    
    # Security
    login_method = db.Column(db.String(50), default='password')  # password, sso, api_key
    two_factor_verified = db.Column(db.Boolean, default=False)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<UserSession {self.user_id}:{self.session_token[:8]}>'
    
    def is_expired(self):
        """Check if session is expired"""
        if self.expires_at and self.expires_at < datetime.utcnow():
            return True
        return False
    
    def extend_session(self, hours=24):
        """Extend session expiry time"""
        from datetime import timedelta
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.last_activity = datetime.utcnow()
    
    def end_session(self):
        """End the session"""
        self.is_active = False
        self.ended_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_token': self.session_token,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'device_type': self.device_type,
            'browser': self.browser,
            'is_active': self.is_active,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'login_method': self.login_method,
            'two_factor_verified': self.two_factor_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None
        }


class AuditLog(db.Model):
    """
    Audit log for tracking user actions within a tenant.
    """
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # References public.user.id
    
    # Action information
    action = db.Column(db.String(100), nullable=False)  # create, update, delete, view, etc.
    resource_type = db.Column(db.String(50), nullable=False)  # patient, appointment, note, etc.
    resource_id = db.Column(db.Integer)
    
    # Details
    description = db.Column(db.Text)
    old_values = db.Column(db.JSON)  # Previous values for updates
    new_values = db.Column(db.JSON)  # New values for creates/updates
    
    # Context
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    session_id = db.Column(db.String(255))
    
    # Metadata
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AuditLog {self.user_id}:{self.action}:{self.resource_type}>'
    
    @classmethod
    def log_action(cls, user_id, action, resource_type, resource_id=None, 
                   description=None, old_values=None, new_values=None,
                   ip_address=None, user_agent=None, session_id=None):
        """Create an audit log entry"""
        log_entry = cls(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
        db.session.add(log_entry)
        return log_entry
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'description': self.description,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

