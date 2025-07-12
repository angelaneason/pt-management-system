"""
Tenant middleware for multi-tenant request handling.

This module provides middleware functions that handle tenant context resolution,
schema switching, and access control for multi-tenant operations.
"""

from flask import request, g, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity, jwt_required
from functools import wraps
from src.models.public import User, Company, CompanyUser
from src.utils.database import DatabaseManager, set_current_tenant
from src.models.tenant_user import AuditLog
import logging

logger = logging.getLogger(__name__)

def extract_tenant_from_request():
    """
    Extract tenant information from the request.
    
    Checks multiple sources in order of priority:
    1. URL path parameter (e.g., /api/v1/tenants/{tenant_slug}/...)
    2. JWT token claims
    3. Request headers
    4. Query parameters
    
    Returns:
        str: Tenant slug or None if not found
    """
    # Check URL path for tenant slug
    if request.view_args and 'tenant_slug' in request.view_args:
        return request.view_args['tenant_slug']
    
    # Check JWT token claims
    try:
        jwt_claims = get_jwt()
        if jwt_claims and 'tenant' in jwt_claims:
            return jwt_claims['tenant']
    except:
        pass
    
    # Check request headers
    tenant_header = request.headers.get('X-Tenant-Slug')
    if tenant_header:
        return tenant_header
    
    # Check query parameters
    tenant_param = request.args.get('tenant')
    if tenant_param:
        return tenant_param
    
    return None


def validate_tenant_access(user_id, tenant_slug):
    """
    Validate that a user has access to a specific tenant.
    
    Args:
        user_id (int): User ID
        tenant_slug (str): Tenant slug
        
    Returns:
        tuple: (is_valid, company_user_record, error_message)
    """
    try:
        # Find the company by slug
        company = Company.query.filter_by(slug=tenant_slug, is_active=True).first()
        if not company:
            return False, None, f"Tenant '{tenant_slug}' not found or inactive"
        
        # Check if user has access to this company
        company_user = CompanyUser.query.filter_by(
            user_id=user_id,
            company_id=company.id,
            is_active=True
        ).first()
        
        if not company_user:
            return False, None, f"User does not have access to tenant '{tenant_slug}'"
        
        return True, company_user, None
        
    except Exception as e:
        logger.error(f"Error validating tenant access: {str(e)}")
        return False, None, "Internal error validating tenant access"


def tenant_required(f):
    """
    Decorator that requires a valid tenant context for the request.
    
    This decorator:
    1. Verifies JWT authentication
    2. Extracts tenant information from the request
    3. Validates user access to the tenant
    4. Switches database schema to the tenant
    5. Sets up request context with tenant information
    
    Usage:
        @app.route('/api/v1/tenants/<tenant_slug>/patients')
        @tenant_required
        def get_patients(tenant_slug):
            # Function will only execute if user has access to tenant
            return Patient.query.all()
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Verify JWT authentication
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            # Extract tenant from request
            tenant_slug = extract_tenant_from_request()
            if not tenant_slug:
                return jsonify({
                    'error': 'Tenant context required',
                    'message': 'Request must include tenant information'
                }), 400
            
            # Validate tenant access
            is_valid, company_user, error_message = validate_tenant_access(user_id, tenant_slug)
            if not is_valid:
                return jsonify({
                    'error': 'Access denied',
                    'message': error_message
                }), 403
            
            # Switch to tenant schema
            db_manager = current_app.extensions.get('database_manager')
            if db_manager:
                db_manager.switch_schema(tenant_slug)
            
            # Set up request context
            g.current_user_id = user_id
            g.current_tenant = tenant_slug
            g.current_company = company_user.company
            g.current_company_user = company_user
            set_current_tenant(tenant_slug)
            
            # Log the access
            try:
                AuditLog.log_action(
                    user_id=user_id,
                    action='access',
                    resource_type='tenant',
                    description=f"Accessed tenant {tenant_slug}",
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
            except Exception as e:
                logger.warning(f"Failed to log tenant access: {str(e)}")
            
            # Execute the original function
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in tenant_required decorator: {str(e)}")
            return jsonify({
                'error': 'Internal server error',
                'message': 'An error occurred processing the request'
            }), 500
        finally:
            # Reset schema after request
            db_manager = current_app.extensions.get('database_manager')
            if db_manager:
                try:
                    db_manager.reset_schema()
                except Exception as e:
                    logger.error(f"Error resetting schema: {str(e)}")
    
    return decorated_function


def public_route(f):
    """
    Decorator for public routes that don't require tenant context.
    
    These routes operate on the public schema and handle global operations
    like authentication, company management, and user registration.
    
    Usage:
        @app.route('/api/v1/auth/login')
        @public_route
        def login():
            # Function operates on public schema
            return authenticate_user()
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Ensure we're using the public schema
            db_manager = current_app.extensions.get('database_manager')
            if db_manager:
                db_manager.reset_schema()
            
            # Clear any tenant context
            g.current_tenant = None
            set_current_tenant(None)
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in public_route decorator: {str(e)}")
            return jsonify({
                'error': 'Internal server error',
                'message': 'An error occurred processing the request'
            }), 500
    
    return decorated_function


def admin_required(f):
    """
    Decorator that requires admin access within a tenant context.
    
    This decorator should be used in combination with @tenant_required
    and verifies that the user has administrative privileges within
    the current tenant.
    
    Usage:
        @app.route('/api/v1/tenants/<tenant_slug>/admin/users')
        @tenant_required
        @admin_required
        def manage_users(tenant_slug):
            # Function only executes for tenant admins
            return get_tenant_users()
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            company_user = getattr(g, 'current_company_user', None)
            if not company_user:
                return jsonify({
                    'error': 'Access denied',
                    'message': 'Admin access required'
                }), 403
            
            # Check if user has admin role
            admin_roles = ['Super Admin', 'Company Admin', 'Practice Manager']
            if company_user.role not in admin_roles and not company_user.can_manage_users:
                return jsonify({
                    'error': 'Access denied',
                    'message': 'Administrative privileges required'
                }), 403
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in admin_required decorator: {str(e)}")
            return jsonify({
                'error': 'Internal server error',
                'message': 'An error occurred processing the request'
            }), 500
    
    return decorated_function


def permission_required(permission):
    """
    Decorator factory that requires a specific permission within a tenant context.
    
    Args:
        permission (str): The required permission
        
    Usage:
        @app.route('/api/v1/tenants/<tenant_slug>/reports')
        @tenant_required
        @permission_required('view_reports')
        def get_reports(tenant_slug):
            return generate_reports()
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                company_user = getattr(g, 'current_company_user', None)
                if not company_user:
                    return jsonify({
                        'error': 'Access denied',
                        'message': 'Permission check failed'
                    }), 403
                
                # Check if user has the required permission
                if not company_user.has_permission(permission):
                    return jsonify({
                        'error': 'Access denied',
                        'message': f'Permission "{permission}" required'
                    }), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in permission_required decorator: {str(e)}")
                return jsonify({
                    'error': 'Internal server error',
                    'message': 'An error occurred processing the request'
                }), 500
        
        return decorated_function
    return decorator


def log_tenant_action(action, resource_type, resource_id=None, description=None, 
                     old_values=None, new_values=None):
    """
    Log an action within the current tenant context.
    
    Args:
        action (str): The action performed
        resource_type (str): Type of resource affected
        resource_id (int): ID of the resource (optional)
        description (str): Description of the action (optional)
        old_values (dict): Previous values for updates (optional)
        new_values (dict): New values for creates/updates (optional)
    """
    try:
        user_id = getattr(g, 'current_user_id', None)
        if user_id:
            AuditLog.log_action(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                old_values=old_values,
                new_values=new_values,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
    except Exception as e:
        logger.warning(f"Failed to log tenant action: {str(e)}")


def get_current_user_profile():
    """
    Get the current user's tenant-specific profile.
    
    Returns:
        TenantUserProfile: User profile within current tenant or None
    """
    try:
        from src.models.tenant_user import TenantUserProfile
        user_id = getattr(g, 'current_user_id', None)
        if user_id:
            return TenantUserProfile.query.filter_by(user_id=user_id).first()
        return None
    except Exception as e:
        logger.error(f"Error getting current user profile: {str(e)}")
        return None


def init_tenant_middleware(app):
    """
    Initialize tenant middleware with the Flask app.
    
    Args:
        app: Flask application instance
    """
    
    @app.before_request
    def before_request():
        """Global before request handler for tenant context setup"""
        # Skip tenant setup for static files and certain endpoints
        if request.endpoint in ['static', 'health_check']:
            return
        
        # Initialize request context
        g.current_tenant = None
        g.current_user_id = None
        g.current_company = None
        g.current_company_user = None
    
    @app.after_request
    def after_request(response):
        """Global after request handler for cleanup"""
        # Reset database schema to public
        db_manager = app.extensions.get('database_manager')
        if db_manager:
            try:
                db_manager.reset_schema()
            except Exception as e:
                logger.error(f"Error resetting schema in after_request: {str(e)}")
        
        return response
    
    @app.errorhandler(403)
    def handle_forbidden(error):
        """Handle 403 Forbidden errors with tenant context"""
        return jsonify({
            'error': 'Access denied',
            'message': 'You do not have permission to access this resource',
            'tenant': getattr(g, 'current_tenant', None)
        }), 403
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found errors with tenant context"""
        return jsonify({
            'error': 'Not found',
            'message': 'The requested resource was not found',
            'tenant': getattr(g, 'current_tenant', None)
        }), 404
"""
Tenant middleware for multi-tenant request handling.
"""
from flask import request, g, jsonify
from functools import wraps
import jwt
from src.models.public import Company, CompanyUser, User

class TenantMiddleware:
    def __init__(self, app):
        self.app = app
        app.before_request(self.before_request)
    
    def before_request(self):
        """Process request before routing to extract tenant context."""
        # Skip tenant processing for public endpoints
        if request.endpoint in ['health_check', 'api_info'] or request.path.startswith('/static'):
            return
        
        # Extract tenant from URL or header
        tenant_slug = None
        if '/tenants/' in request.path:
            path_parts = request.path.split('/')
            if 'tenants' in path_parts:
                tenant_index = path_parts.index('tenants')
                if len(path_parts) > tenant_index + 1:
                    tenant_slug = path_parts[tenant_index + 1]
        
        # Also check X-Tenant-Slug header
        if not tenant_slug:
            tenant_slug = request.headers.get('X-Tenant-Slug')
        
        # Store tenant context
        g.tenant_slug = tenant_slug
        g.tenant_company = None
        
        if tenant_slug:
            # Look up company by slug
            company = Company.query.filter_by(slug=tenant_slug, is_active=True).first()
            if company:
                g.tenant_company = company
            else:
                return jsonify({'error': 'Invalid tenant'}), 404

def require_tenant(f):
    """Decorator to require valid tenant context."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'tenant_company') or not g.tenant_company:
            return jsonify({'error': 'Tenant context required'}), 400
        return f(*args, **kwargs)
    return decorated_function

def get_current_tenant():
    """Get current tenant company from request context."""
    return getattr(g, 'tenant_company', None)
