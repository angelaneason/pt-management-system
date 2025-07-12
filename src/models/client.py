"""
Client model for tenant-specific data in the Physical Therapy Management System.

This model exists within each tenant schema and represents client organizations
that refer patients to the physical therapy practice.
"""

from src.models.public import db
from datetime import datetime

class Client(db.Model):
    """
    Client organizations that refer patients to the practice.
    Each tenant has their own set of clients.
    """
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic information
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), default='Healthcare Facility')  # Hospital, Clinic, Insurance, etc.
    description = db.Column(db.Text)
    
    # Contact information
    primary_contact_name = db.Column(db.String(100))
    primary_contact_title = db.Column(db.String(50))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    fax = db.Column(db.String(20))
    
    # Address information
    address_line1 = db.Column(db.String(200))
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(10))
    country = db.Column(db.String(50), default='USA')
    
    # Business information
    tax_id = db.Column(db.String(50))
    npi_number = db.Column(db.String(20))  # National Provider Identifier
    license_number = db.Column(db.String(50))
    
    # Billing and payment
    billing_contact_name = db.Column(db.String(100))
    billing_email = db.Column(db.String(120))
    billing_phone = db.Column(db.String(20))
    payment_terms = db.Column(db.String(50), default='Net 30')
    preferred_payment_method = db.Column(db.String(50))
    
    # Contract and relationship
    contract_start_date = db.Column(db.Date)
    contract_end_date = db.Column(db.Date)
    referral_rate = db.Column(db.Float)  # Percentage or flat rate
    preferred_therapists = db.Column(db.JSON)  # Array of user IDs
    
    # Visual and organizational
    color_code = db.Column(db.String(7), default='#3B82F6')  # Default blue color
    logo_url = db.Column(db.String(500))
    priority_level = db.Column(db.String(20), default='Standard')  # High, Standard, Low
    
    # Communication preferences
    preferred_communication_method = db.Column(db.String(50), default='Email')
    notification_preferences = db.Column(db.JSON)
    
    # Performance metrics
    total_referrals = db.Column(db.Integer, default=0)
    active_patients = db.Column(db.Integer, default=0)
    average_referral_rating = db.Column(db.Float)
    
    # Status and metadata
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer)  # User ID who created this client
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patients = db.relationship('Patient', back_populates='client', lazy='dynamic')
    
    def __repr__(self):
        return f'<Client {self.name}>'
    
    def get_full_address(self):
        """Get formatted full address"""
        address_parts = [self.address_line1]
        if self.address_line2:
            address_parts.append(self.address_line2)
        if self.city:
            city_state_zip = self.city
            if self.state:
                city_state_zip += f", {self.state}"
            if self.zip_code:
                city_state_zip += f" {self.zip_code}"
            address_parts.append(city_state_zip)
        return "\n".join(address_parts)
    
    def get_active_patients_count(self):
        """Get count of active patients from this client"""
        return self.patients.filter_by(is_active=True).count()
    
    def get_recent_referrals(self, days=30):
        """Get recent referrals from this client"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return self.patients.filter(Patient.created_at >= cutoff_date).all()
    
    def update_metrics(self):
        """Update performance metrics"""
        self.total_referrals = self.patients.count()
        self.active_patients = self.get_active_patients_count()
        # Calculate average rating if ratings exist
        # This would be implemented based on rating system
    
    def to_dict(self, include_patients=False):
        data = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'primary_contact_name': self.primary_contact_name,
            'primary_contact_title': self.primary_contact_title,
            'email': self.email,
            'phone': self.phone,
            'fax': self.fax,
            'address_line1': self.address_line1,
            'address_line2': self.address_line2,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'country': self.country,
            'full_address': self.get_full_address(),
            'tax_id': self.tax_id,
            'npi_number': self.npi_number,
            'license_number': self.license_number,
            'billing_contact_name': self.billing_contact_name,
            'billing_email': self.billing_email,
            'billing_phone': self.billing_phone,
            'payment_terms': self.payment_terms,
            'preferred_payment_method': self.preferred_payment_method,
            'contract_start_date': self.contract_start_date.isoformat() if self.contract_start_date else None,
            'contract_end_date': self.contract_end_date.isoformat() if self.contract_end_date else None,
            'referral_rate': self.referral_rate,
            'preferred_therapists': self.preferred_therapists,
            'color_code': self.color_code,
            'logo_url': self.logo_url,
            'priority_level': self.priority_level,
            'preferred_communication_method': self.preferred_communication_method,
            'notification_preferences': self.notification_preferences,
            'total_referrals': self.total_referrals,
            'active_patients': self.active_patients,
            'average_referral_rating': self.average_referral_rating,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_patients:
            data['patients'] = [patient.to_dict() for patient in self.patients.filter_by(is_active=True).all()]
        
        return data

