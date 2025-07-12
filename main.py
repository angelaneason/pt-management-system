import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, request, jsonify, g
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta
import logging

# Import database and models
from src.models.public import db
from src.models.user import User
from src.models.patient import Patient
from src.models.client import Client
from src.models.appointment import Appointment
from src.models.message import Message, MessageTemplate
from src.models.note import Note, NoteTemplate
from src.models.route import Route, RouteStop
from src.models.tenant_user import TenantUserProfile

# Import utilities
from src.utils.database import DatabaseManager
from src.middleware.tenant import TenantMiddleware

# Import blueprints
from src.routes.auth import auth_bp as multi_tenant_auth_bp
from src.routes.user import user_bp
from src.routes.patient import patient_bp
from src.routes.client import client_bp
from src.routes.appointment import appointment_bp
from src.routes.message import message_bp
from src.routes.note import note_bp
from src.routes.route import route_bp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Application factory pattern for creating Flask app."""
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT-multi-tenant-key')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-string-multi-tenant')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
    
    # Database configuration - PostgreSQL for production, SQLite for development
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Production PostgreSQL
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
        }
    else:
        # Development SQLite
        db_path = os.path.join(os.path.dirname(__file__), 'database', 'multi_tenant_app.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    
    # Enable CORS for all routes, allowing credentials and specific origins
        CORS(app, supports_credentials=True, origins=['*'])
    
    # Initialize tenant middleware
    tenant_middleware = TenantMiddleware(app)
    
    # JWT token handlers
    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return {
            'user_id': user.id,
            'username': user.username,
            'company_id': getattr(user, 'current_company_id', None)
        }
    
    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.query.filter_by(id=identity['user_id']).one_or_none()
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': 'Invalid token'}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': 'Authorization token is required'}), 401
    
    # Register blueprints with versioned API
    app.register_blueprint(multi_tenant_auth_bp, url_prefix='/api/v1')
    app.register_blueprint(user_bp, url_prefix='/api/v1')
    app.register_blueprint(patient_bp, url_prefix='/api/v1')
    app.register_blueprint(client_bp, url_prefix='/api/v1')
    app.register_blueprint(appointment_bp, url_prefix='/api/v1')
    app.register_blueprint(message_bp, url_prefix='/api/v1')
    app.register_blueprint(note_bp, url_prefix='/api/v1')
    app.register_blueprint(route_bp, url_prefix='/api/v1')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'version': '2.0.0-multi-tenant',
            'database': 'connected' if db.engine else 'disconnected'
        })
    
    # API info endpoint
    @app.route('/api/v1/info')
    def api_info():
        return jsonify({
            'name': 'Physical Therapy Management System',
            'version': '2.0.0',
            'description': 'Multi-tenant physical therapy practice management system',
            'features': [
                'Multi-company support',
                'Role-based access control',
                'Tenant data isolation',
                'Comprehensive audit logging',
                'Advanced patient management',
                'Appointment scheduling',
                'Route optimization',
                'Communication hub',
                'Visit documentation',
                'Reporting and analytics'
            ],
            'endpoints': {
                'authentication': '/api/v1/auth/*',
                'companies': '/api/v1/companies/*',
                'tenant_operations': '/api/v1/tenants/{tenant_slug}/*'
            }
        })
    
    # Initialize database and create default data
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Initialize database manager
            db_manager = DatabaseManager()
            
            # Create default super admin user if it doesn't exist
            super_admin = User.query.filter_by(username='superadmin').first()
            if not super_admin:
                super_admin = User(
                    username='superadmin',
                    email='superadmin@ptmanagement.com',
                    full_name='Super Administrator',
                    phone='555-0000',
                    is_active=True,
                    is_super_admin=True
                )
                super_admin.set_password('superadmin123')
                db.session.add(super_admin)
                db.session.commit()
                logger.info("Default super admin user created: superadmin/superadmin123")
            
            # Create demo company if it doesn't exist
            from src.models.public import Company
            demo_company = Company.query.filter_by(slug='demo-clinic').first()
            if not demo_company:
                demo_company = Company(
                    name='Demo Physical Therapy Clinic',
                    slug='demo-clinic',
                    description='A demonstration physical therapy clinic for testing the multi-tenant system',
                    email='demo@ptmanagement.com',
                    phone='555-DEMO',
                    address='123 Demo Street, Demo City, DC 12345',
                    is_active=True,
                    created_by=super_admin.id
                )
                db.session.add(demo_company)
                db.session.commit()
                
                # Create tenant schema for demo company
                db_manager.create_tenant_schema(demo_company.slug)
                
                # Create demo admin user for the company
                from src.models.public import CompanyUser
                demo_admin = User(
                    username='demoadmin',
                    email='admin@demo-clinic.com',
                    full_name='Demo Administrator',
                    phone='555-0001',
                    is_active=True
                )
                demo_admin.set_password('demo123')
                db.session.add(demo_admin)
                db.session.commit()
                
                # Add user to company
                company_user = CompanyUser(
                    user_id=demo_admin.id,
                    company_id=demo_company.id,
                    role='Company Admin',
                    permissions={
                        'manage_users': True,
                        'manage_settings': True,
                        'view_reports': True,
                        'manage_billing': True,
                        'manage_patients': True,
                        'manage_appointments': True,
                        'manage_clients': True
                    },
                    is_active=True,
                    invited_by=super_admin.id
                )
                db.session.add(company_user)
                db.session.commit()
                
                logger.info("Demo company created: demo-clinic")
                logger.info("Demo admin user created: demoadmin/demo123")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            db.session.rollback()
    
    # Serve static files (React frontend)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
            return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return jsonify({
                    'message': 'Physical Therapy Management System API',
                    'version': '2.0.0-multi-tenant',
                    'status': 'running',
                    'frontend': 'not_deployed',
                    'api_docs': '/api/v1/info'
                }), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Endpoint not found'}), 404
        return serve('')
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Access forbidden'}), 403
    
    return app

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Physical Therapy Management System v2.0.0")
    logger.info(f"Multi-tenant architecture enabled")
    logger.info(f"Running on port {port} with debug={debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

