"""
Public schema models for multi-tenant Physical Therapy Management System.

This module contains models that exist in the public schema and are shared
across all tenants, including company management, user authentication,
and tenant-user relationships.
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()

class Company(db.Model):
    """
    Company model representing tenant organizations.
    Each company is a separate tenant with its own isolated data.
    """
    __bind_key__ = 'public'
    __table_args__ = {'schema': 'public'}
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)  # Used as schema name
    description = db.Column(db.Text)
    
    # Contact information
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    website = db.Column(db.String(200))
    
    # Subscription and billing
    subscription_plan = db.Column(db.String(50), default='basic')
    subscription_status = db.Column(db.String(20), default='active')
    billing_email = db.Column(db.String(120))
    
    # Configuration
    timezone = db.Column(db.String(50), default='UTC')
    date_format = db.Column(db.String(20), default='MM/DD/YYYY')
    time_format = db.Column(db.String(10), default='12h')
    
    # Branding
    logo_url = db.Column(db.String(500))
    primary_color = db.Column(db.String(7), default='#3B82F6')
    secondary_color = db.Column(db.String(7), default='#1F2937')
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    company_users = db.relationship('CompanyUser', back_populates='company', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Company {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'website': self.website,
            'subscription_plan': self.subscription_plan,
            'subscription_status': self.subscription_status,
            'timezone': self.timezone,
            'date_format': self.date_format,
            'time_format': self.time_format,
            'logo_url': self.logo_url,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }


class User(db.Model):
    """
    Global user model for authentication across all tenants.
    Users can belong to multiple companies with different roles.
    """
    __bind_key__ = 'public'
    __table_args__ = {'schema': 'public'}
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Personal information
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    
    # Security
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    password_reset_token = db.Column(db.String(100))
    password_reset_expires = db.Column(db.DateTime)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company_users = db.relationship('CompanyUser', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_reset_token(self):
        """Generate a password reset token"""
        self.password_reset_token = str(uuid.uuid4())
        self.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
        return self.password_reset_token
    
    def is_locked(self):
        """Check if account is locked due to failed login attempts"""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    def get_companies(self):
        """Get all companies this user belongs to"""
        return [cu.company for cu in self.company_users if cu.is_active]
    
    def get_company_role(self, company_id):
        """Get user's role in a specific company"""
        cu = CompanyUser.query.filter_by(user_id=self.id, company_id=company_id, is_active=True).first()
        return cu.role if cu else None
    
    def to_dict(self, include_companies=False):
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'phone': self.phone,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_companies:
            data['companies'] = [cu.to_dict() for cu in self.company_users if cu.is_active]
        
        return data


class CompanyUser(db.Model):
    """
    Association model linking users to companies with roles.
    Enables users to belong to multiple companies with different roles.
    """
    __bind_key__ = 'public'
    __table_args__ = {'schema': 'public'}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('public.user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('public.company.id'), nullable=False)
    
    # Role within the company
    role = db.Column(db.String(50), nullable=False, default='Clinician')
    # Possible roles: Super Admin, Company Admin, Practice Manager, Clinician, Office Staff, Scheduler
    
    # Permissions and access
    permissions = db.Column(db.JSON)  # Store custom permissions as JSON
    can_manage_users = db.Column(db.Boolean, default=False)
    can_manage_settings = db.Column(db.Boolean, default=False)
    can_view_reports = db.Column(db.Boolean, default=False)
    can_manage_billing = db.Column(db.Boolean, default=False)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    invited_at = db.Column(db.DateTime, default=datetime.utcnow)
    joined_at = db.Column(db.DateTime)
    last_access = db.Column(db.DateTime)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='company_users')
    company = db.relationship('Company', back_populates='company_users')
    
    # Unique constraint to prevent duplicate user-company relationships
    __table_args__ = (
        db.UniqueConstraint('user_id', 'company_id', name='unique_user_company'),
        {'schema': 'public'}
    )
    
    def __repr__(self):
        return f'<CompanyUser {self.user.username}@{self.company.name}>'
    
    def has_permission(self, permission):
        """Check if user has a specific permission"""
        if self.permissions and permission in self.permissions:
            return self.permissions[permission]
        
        # Default permissions based on role
        role_permissions = {
            'Super Admin': ['all'],
            'Company Admin': ['manage_users', 'manage_settings', 'view_reports', 'manage_billing'],
            'Practice Manager': ['manage_users', 'view_reports'],
            'Clinician': ['view_patients', 'manage_appointments', 'create_notes'],
            'Office Staff': ['view_patients', 'manage_appointments'],
            'Scheduler': ['manage_appointments']
        }
        
        if self.role in role_permissions:
            return permission in role_permissions[self.role] or 'all' in role_permissions[self.role]
        
        return False
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'company_id': self.company_id,
            'role': self.role,
            'permissions': self.permissions,
            'can_manage_users': self.can_manage_users,
            'can_manage_settings': self.can_manage_settings,
            'can_view_reports': self.can_view_reports,
            'can_manage_billing': self.can_manage_billing,
            'is_active': self.is_active,
            'invited_at': self.invited_at.isoformat() if self.invited_at else None,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'last_access': self.last_access.isoformat() if self.last_access else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user': self.user.to_dict() if self.user else None,
            'company': self.company.to_dict() if self.company else None
        }


class Practice(db.Model):
    """
    Practice locations within a company.
    Enables companies to have multiple practice locations.
    """
    __bind_key__ = 'public'
    __table_args__ = {'schema': 'public'}
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('public.company.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Location information
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(10))
    country = db.Column(db.String(50), default='USA')
    
    # Contact information
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    fax = db.Column(db.String(20))
    
    # Operating information
    operating_hours = db.Column(db.JSON)  # Store hours as JSON
    services_offered = db.Column(db.JSON)  # Store services as JSON array
    
    # Geographic coordinates for routing
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', backref='practices')
    
    def __repr__(self):
        return f'<Practice {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'description': self.description,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'country': self.country,
            'phone': self.phone,
            'email': self.email,
            'fax': self.fax,
            'operating_hours': self.operating_hours,
            'services_offered': self.services_offered,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SystemConfiguration(db.Model):
    """
    Global system configuration settings.
    """
    __bind_key__ = 'public'
    __table_args__ = {'schema': 'public'}
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    data_type = db.Column(db.String(20), default='string')  # string, integer, boolean, json
    is_public = db.Column(db.Boolean, default=False)  # Whether this setting can be read by tenants
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemConfiguration {self.key}>'
    
    def get_value(self):
        """Get the typed value based on data_type"""
        if self.data_type == 'integer':
            return int(self.value) if self.value else 0
        elif self.data_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes') if self.value else False
        elif self.data_type == 'json':
            import json
            return json.loads(self.value) if self.value else {}
        else:
            return self.value
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.get_value(),
            'description': self.description,
            'data_type': self.data_type,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

