"""
Database utility classes for multi-tenant schema management.

This module provides utilities for creating, managing, and switching between
tenant schemas in the Physical Therapy Management System.
"""

from flask import current_app
from sqlalchemy import text, create_engine
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy.exc import ProgrammingError, IntegrityError
from src.models.public import db, Company
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages database operations for multi-tenant architecture.
    Handles schema creation, switching, and tenant provisioning.
    """
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the database manager with Flask app"""
        self.app = app
        app.extensions['database_manager'] = self
    
    def create_tenant_schema(self, tenant_slug):
        """
        Create a new tenant schema with all required tables.
        
        Args:
            tenant_slug (str): The tenant's unique slug identifier
            
        Returns:
            bool: True if schema was created successfully, False otherwise
        """
        try:
            # Create the schema
            with db.engine.connect() as connection:
                connection.execute(CreateSchema(tenant_slug))
                connection.commit()
                logger.info(f"Created schema: {tenant_slug}")
            
            # Switch to the new schema and create tables
            self.switch_schema(tenant_slug)
            
            # Create all tenant tables in the new schema
            self._create_tenant_tables(tenant_slug)
            
            # Initialize default data
            self._initialize_tenant_data(tenant_slug)
            
            logger.info(f"Successfully created tenant schema: {tenant_slug}")
            return True
            
        except ProgrammingError as e:
            logger.error(f"Error creating schema {tenant_slug}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating schema {tenant_slug}: {str(e)}")
            return False
    
    def drop_tenant_schema(self, tenant_slug):
        """
        Drop a tenant schema and all its data.
        
        Args:
            tenant_slug (str): The tenant's unique slug identifier
            
        Returns:
            bool: True if schema was dropped successfully, False otherwise
        """
        try:
            with db.engine.connect() as connection:
                connection.execute(DropSchema(tenant_slug, cascade=True))
                connection.commit()
                logger.info(f"Dropped schema: {tenant_slug}")
            return True
            
        except ProgrammingError as e:
            logger.error(f"Error dropping schema {tenant_slug}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error dropping schema {tenant_slug}: {str(e)}")
            return False
    
    def switch_schema(self, tenant_slug):
        """
        Switch the database connection to use a specific tenant schema.
        
        Args:
            tenant_slug (str): The tenant's unique slug identifier
        """
        try:
            with db.engine.connect() as connection:
                connection.execute(text(f'SET search_path TO "{tenant_slug}", public'))
                connection.commit()
                logger.debug(f"Switched to schema: {tenant_slug}")
                
        except Exception as e:
            logger.error(f"Error switching to schema {tenant_slug}: {str(e)}")
            raise
    
    def reset_schema(self):
        """Reset the database connection to use the default public schema."""
        try:
            with db.engine.connect() as connection:
                connection.execute(text('SET search_path TO public'))
                connection.commit()
                logger.debug("Reset to public schema")
                
        except Exception as e:
            logger.error(f"Error resetting to public schema: {str(e)}")
            raise
    
    def get_tenant_schemas(self):
        """
        Get a list of all tenant schemas in the database.
        
        Returns:
            list: List of schema names
        """
        try:
            with db.engine.connect() as connection:
                result = connection.execute(text("""
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'public', 'pg_toast')
                    ORDER BY schema_name
                """))
                schemas = [row[0] for row in result]
                return schemas
                
        except Exception as e:
            logger.error(f"Error getting tenant schemas: {str(e)}")
            return []
    
    def schema_exists(self, tenant_slug):
        """
        Check if a tenant schema exists.
        
        Args:
            tenant_slug (str): The tenant's unique slug identifier
            
        Returns:
            bool: True if schema exists, False otherwise
        """
        try:
            with db.engine.connect() as connection:
                result = connection.execute(text("""
                    SELECT COUNT(*) 
                    FROM information_schema.schemata 
                    WHERE schema_name = :schema_name
                """), {'schema_name': tenant_slug})
                count = result.scalar()
                return count > 0
                
        except Exception as e:
            logger.error(f"Error checking if schema exists {tenant_slug}: {str(e)}")
            return False
    
    def _create_tenant_tables(self, tenant_slug):
        """
        Create all tenant-specific tables in the given schema.
        
        Args:
            tenant_slug (str): The tenant's unique slug identifier
        """
        try:
            # Import tenant models to ensure they're registered
            from src.models.client import Client
            from src.models.patient import Patient
            from src.models.appointment import Appointment
            from src.models.message import Message
            from src.models.note import Note
            from src.models.route import Route
            from src.models.tenant_user import TenantUserProfile, UserSession, AuditLog
            
            # Create all tables in the tenant schema
            with db.engine.connect() as connection:
                # Set search path to the tenant schema
                connection.execute(text(f'SET search_path TO "{tenant_slug}", public'))
                
                # Create tables using SQLAlchemy metadata
                db.metadata.create_all(bind=connection, checkfirst=True)
                connection.commit()
                
                logger.info(f"Created tables in schema: {tenant_slug}")
                
        except Exception as e:
            logger.error(f"Error creating tables in schema {tenant_slug}: {str(e)}")
            raise
    
    def _initialize_tenant_data(self, tenant_slug):
        """
        Initialize default data for a new tenant.
        
        Args:
            tenant_slug (str): The tenant's unique slug identifier
        """
        try:
            # Switch to tenant schema
            self.switch_schema(tenant_slug)
            
            # Add any default data here
            # For example, default appointment types, note templates, etc.
            
            db.session.commit()
            logger.info(f"Initialized default data for schema: {tenant_slug}")
            
        except Exception as e:
            logger.error(f"Error initializing data for schema {tenant_slug}: {str(e)}")
            db.session.rollback()
            raise
        finally:
            # Reset to public schema
            self.reset_schema()
    
    def migrate_tenant_schemas(self, migration_function=None):
        """
        Apply migrations to all tenant schemas.
        
        Args:
            migration_function (callable): Optional function to run for each schema
        """
        tenant_schemas = self.get_tenant_schemas()
        
        for schema in tenant_schemas:
            try:
                logger.info(f"Migrating schema: {schema}")
                self.switch_schema(schema)
                
                if migration_function:
                    migration_function()
                else:
                    # Default migration: create any missing tables
                    db.metadata.create_all(bind=db.engine, checkfirst=True)
                
                db.session.commit()
                logger.info(f"Successfully migrated schema: {schema}")
                
            except Exception as e:
                logger.error(f"Error migrating schema {schema}: {str(e)}")
                db.session.rollback()
            finally:
                self.reset_schema()
    
    def backup_tenant_schema(self, tenant_slug, backup_path=None):
        """
        Create a backup of a tenant schema.
        
        Args:
            tenant_slug (str): The tenant's unique slug identifier
            backup_path (str): Optional path for backup file
            
        Returns:
            str: Path to the backup file
        """
        if not backup_path:
            backup_path = f"/tmp/{tenant_slug}_backup.sql"
        
        try:
            # Use pg_dump to create schema backup
            db_url = current_app.config['SQLALCHEMY_DATABASE_URI']
            # Parse database URL to get connection parameters
            # This is a simplified version - you might want to use a proper URL parser
            
            import subprocess
            cmd = [
                'pg_dump',
                '--schema', tenant_slug,
                '--file', backup_path,
                '--no-owner',
                '--no-privileges',
                db_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully backed up schema {tenant_slug} to {backup_path}")
                return backup_path
            else:
                logger.error(f"Error backing up schema {tenant_slug}: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error backing up schema {tenant_slug}: {str(e)}")
            return None
    
    def restore_tenant_schema(self, tenant_slug, backup_path):
        """
        Restore a tenant schema from backup.
        
        Args:
            tenant_slug (str): The tenant's unique slug identifier
            backup_path (str): Path to the backup file
            
        Returns:
            bool: True if restore was successful, False otherwise
        """
        try:
            # First, drop the existing schema if it exists
            if self.schema_exists(tenant_slug):
                self.drop_tenant_schema(tenant_slug)
            
            # Use psql to restore from backup
            db_url = current_app.config['SQLALCHEMY_DATABASE_URI']
            
            import subprocess
            cmd = [
                'psql',
                '--file', backup_path,
                db_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully restored schema {tenant_slug} from {backup_path}")
                return True
            else:
                logger.error(f"Error restoring schema {tenant_slug}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error restoring schema {tenant_slug}: {str(e)}")
            return False


class TenantContext:
    """
    Context manager for temporarily switching to a tenant schema.
    
    Usage:
        with TenantContext('tenant_slug'):
            # All database operations will use the tenant schema
            patients = Patient.query.all()
    """
    
    def __init__(self, tenant_slug, db_manager=None):
        self.tenant_slug = tenant_slug
        self.db_manager = db_manager or current_app.extensions.get('database_manager')
        self.original_schema = None
    
    def __enter__(self):
        if self.db_manager:
            self.db_manager.switch_schema(self.tenant_slug)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db_manager:
            self.db_manager.reset_schema()


def get_current_tenant():
    """
    Get the current tenant from Flask's g object or request context.
    
    Returns:
        str: Current tenant slug or None
    """
    from flask import g
    return getattr(g, 'current_tenant', None)


def set_current_tenant(tenant_slug):
    """
    Set the current tenant in Flask's g object.
    
    Args:
        tenant_slug (str): The tenant's unique slug identifier
    """
    from flask import g
    g.current_tenant = tenant_slug


def require_tenant_context(f):
    """
    Decorator to ensure a function is called within a tenant context.
    
    Usage:
        @require_tenant_context
        def get_patients():
            return Patient.query.all()
    """
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_tenant = get_current_tenant()
        if not current_tenant:
            raise ValueError("Function requires tenant context")
        return f(*args, **kwargs)
    
    return decorated_function


def init_database_manager(app):
    """
    Initialize the database manager with the Flask app.
    
    Args:
        app: Flask application instance
    """
    db_manager = DatabaseManager(app)
    return db_manager

