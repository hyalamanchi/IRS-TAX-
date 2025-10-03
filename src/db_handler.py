"""
Database Handler Module for Tax Form Data Management

This module provides comprehensive database operations for storing,
retrieving, and managing tax form data with support for multiple database backends.
"""

import os
import logging
import sqlite3
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
import pymongo
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSON

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()


@dataclass
class TaxFormRecord:
    """Data class for tax form records"""
    id: Optional[int] = None
    form_id: Optional[str] = None
    form_type: Optional[str] = None
    form_name: Optional[str] = None
    tax_year: Optional[int] = None
    file_path: Optional[str] = None
    processing_status: Optional[str] = None
    fields_extracted: Optional[Dict] = None
    confidence_score: Optional[float] = None
    validation_errors: Optional[List[str]] = None
    validation_warnings: Optional[List[str]] = None
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    processed_by: Optional[str] = None


class TaxForm(Base):
    """SQLAlchemy model for tax forms table"""
    __tablename__ = 'tax_forms'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    form_id = Column(String(50), unique=True, nullable=False)
    form_type = Column(String(20), nullable=False)
    form_name = Column(String(200))
    tax_year = Column(Integer)
    file_path = Column(String(500))
    processing_status = Column(String(20), default='pending')
    fields_extracted = Column(JSON)
    confidence_score = Column(Float)
    validation_errors = Column(JSON)
    validation_warnings = Column(JSON)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_by = Column(String(100))


class AuditLog(Base):
    """SQLAlchemy model for audit logs"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False)
    record_id = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)  # INSERT, UPDATE, DELETE
    old_values = Column(JSON)
    new_values = Column(JSON)
    user_id = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))


class DatabaseHandler:
    """
    Comprehensive database handler supporting multiple database backends
    """
    
    def __init__(self, db_type: str = "sqlite", connection_string: str = None):
        """
        Initialize database handler
        
        Args:
            db_type: Type of database ('sqlite', 'postgresql', 'mongodb')
            connection_string: Database connection string
        """
        self.db_type = db_type.lower()
        self.connection_string = connection_string or self._get_default_connection_string()
        
        if self.db_type in ['sqlite', 'postgresql']:
            self.engine = create_engine(self.connection_string)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self._create_tables()
        elif self.db_type == 'mongodb':
            self.client = pymongo.MongoClient(self.connection_string)
            self.db = self.client.tax_forms_db
            self.collection = self.db.tax_forms
            self.audit_collection = self.db.audit_logs
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def _get_default_connection_string(self) -> str:
        """Get default connection string based on database type"""
        if self.db_type == 'sqlite':
            return "sqlite:///tax_forms.db"
        elif self.db_type == 'postgresql':
            return os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/tax_forms')
        elif self.db_type == 'mongodb':
            return os.getenv('MONGODB_URL', 'mongodb://localhost:27017/')
        else:
            raise ValueError(f"No default connection string for {self.db_type}")
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            raise
    
    @contextmanager
    def get_session(self) -> Session:
        """Context manager for database sessions"""
        if self.db_type not in ['sqlite', 'postgresql']:
            raise ValueError("Sessions only available for SQL databases")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()
    
    def insert_tax_form(self, form_data: TaxFormRecord) -> str:
        """
        Insert a new tax form record
        
        Args:
            form_data: TaxFormRecord object with form data
            
        Returns:
            ID of the inserted record
        """
        try:
            if self.db_type in ['sqlite', 'postgresql']:
                return self._insert_sql_tax_form(form_data)
            elif self.db_type == 'mongodb':
                return self._insert_mongo_tax_form(form_data)
        except Exception as e:
            logger.error(f"Error inserting tax form: {str(e)}")
            raise
    
    def _insert_sql_tax_form(self, form_data: TaxFormRecord) -> str:
        """Insert tax form using SQL database"""
        with self.get_session() as session:
            # Generate form_id if not provided
            if not form_data.form_id:
                form_data.form_id = self._generate_form_id()
            
            tax_form = TaxForm(
                form_id=form_data.form_id,
                form_type=form_data.form_type,
                form_name=form_data.form_name,
                tax_year=form_data.tax_year,
                file_path=form_data.file_path,
                processing_status=form_data.processing_status or 'pending',
                fields_extracted=form_data.fields_extracted,
                confidence_score=form_data.confidence_score,
                validation_errors=form_data.validation_errors,
                validation_warnings=form_data.validation_warnings,
                processed_by=form_data.processed_by
            )
            
            session.add(tax_form)
            session.flush()  # Get the ID
            
            # Log the insertion
            self._log_audit_action('tax_forms', str(tax_form.id), 'INSERT', None, asdict(form_data))
            
            return form_data.form_id
    
    def _insert_mongo_tax_form(self, form_data: TaxFormRecord) -> str:
        """Insert tax form using MongoDB"""
        # Generate form_id if not provided
        if not form_data.form_id:
            form_data.form_id = self._generate_form_id()
        
        # Convert dataclass to dict
        doc = asdict(form_data)
        doc['created_date'] = datetime.utcnow()
        doc['updated_date'] = datetime.utcnow()
        
        result = self.collection.insert_one(doc)
        
        # Log the insertion
        self._log_audit_action('tax_forms', str(result.inserted_id), 'INSERT', None, doc)
        
        return form_data.form_id
    
    def update_tax_form(self, form_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing tax form record
        
        Args:
            form_id: ID of the form to update
            updates: Dictionary of fields to update
            
        Returns:
            True if update was successful
        """
        try:
            if self.db_type in ['sqlite', 'postgresql']:
                return self._update_sql_tax_form(form_id, updates)
            elif self.db_type == 'mongodb':
                return self._update_mongo_tax_form(form_id, updates)
        except Exception as e:
            logger.error(f"Error updating tax form {form_id}: {str(e)}")
            raise
    
    def _update_sql_tax_form(self, form_id: str, updates: Dict[str, Any]) -> bool:
        """Update tax form using SQL database"""
        with self.get_session() as session:
            tax_form = session.query(TaxForm).filter(TaxForm.form_id == form_id).first()
            
            if not tax_form:
                logger.warning(f"Tax form {form_id} not found")
                return False
            
            # Store old values for audit
            old_values = {column.name: getattr(tax_form, column.name) for column in tax_form.__table__.columns}
            
            # Apply updates
            for field, value in updates.items():
                if hasattr(tax_form, field):
                    setattr(tax_form, field, value)
            
            tax_form.updated_date = datetime.utcnow()
            
            # Log the update
            self._log_audit_action('tax_forms', str(tax_form.id), 'UPDATE', old_values, updates)
            
            return True
    
    def _update_mongo_tax_form(self, form_id: str, updates: Dict[str, Any]) -> bool:
        """Update tax form using MongoDB"""
        # Get old document for audit
        old_doc = self.collection.find_one({'form_id': form_id})
        
        if not old_doc:
            logger.warning(f"Tax form {form_id} not found")
            return False
        
        updates['updated_date'] = datetime.utcnow()
        result = self.collection.update_one(
            {'form_id': form_id},
            {'$set': updates}
        )
        
        if result.modified_count > 0:
            # Log the update
            self._log_audit_action('tax_forms', str(old_doc['_id']), 'UPDATE', old_doc, updates)
            return True
        
        return False
    
    def get_tax_form(self, form_id: str) -> Optional[TaxFormRecord]:
        """
        Retrieve a tax form by ID
        
        Args:
            form_id: ID of the form to retrieve
            
        Returns:
            TaxFormRecord object or None if not found
        """
        try:
            if self.db_type in ['sqlite', 'postgresql']:
                return self._get_sql_tax_form(form_id)
            elif self.db_type == 'mongodb':
                return self._get_mongo_tax_form(form_id)
        except Exception as e:
            logger.error(f"Error retrieving tax form {form_id}: {str(e)}")
            raise
    
    def _get_sql_tax_form(self, form_id: str) -> Optional[TaxFormRecord]:
        """Get tax form using SQL database"""
        with self.get_session() as session:
            tax_form = session.query(TaxForm).filter(TaxForm.form_id == form_id).first()
            
            if tax_form:
                return TaxFormRecord(
                    id=tax_form.id,
                    form_id=tax_form.form_id,
                    form_type=tax_form.form_type,
                    form_name=tax_form.form_name,
                    tax_year=tax_form.tax_year,
                    file_path=tax_form.file_path,
                    processing_status=tax_form.processing_status,
                    fields_extracted=tax_form.fields_extracted,
                    confidence_score=tax_form.confidence_score,
                    validation_errors=tax_form.validation_errors,
                    validation_warnings=tax_form.validation_warnings,
                    created_date=tax_form.created_date,
                    updated_date=tax_form.updated_date,
                    processed_by=tax_form.processed_by
                )
            return None
    
    def _get_mongo_tax_form(self, form_id: str) -> Optional[TaxFormRecord]:
        """Get tax form using MongoDB"""
        doc = self.collection.find_one({'form_id': form_id})
        
        if doc:
            # Remove MongoDB-specific fields
            doc.pop('_id', None)
            return TaxFormRecord(**doc)
        
        return None
    
    def search_tax_forms(self, filters: Dict[str, Any], limit: int = 100, offset: int = 0) -> List[TaxFormRecord]:
        """
        Search tax forms with filters
        
        Args:
            filters: Dictionary of search criteria
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of TaxFormRecord objects
        """
        try:
            if self.db_type in ['sqlite', 'postgresql']:
                return self._search_sql_tax_forms(filters, limit, offset)
            elif self.db_type == 'mongodb':
                return self._search_mongo_tax_forms(filters, limit, offset)
        except Exception as e:
            logger.error(f"Error searching tax forms: {str(e)}")
            raise
    
    def _search_sql_tax_forms(self, filters: Dict[str, Any], limit: int, offset: int) -> List[TaxFormRecord]:
        """Search tax forms using SQL database"""
        with self.get_session() as session:
            query = session.query(TaxForm)
            
            # Apply filters
            for field, value in filters.items():
                if hasattr(TaxForm, field):
                    if isinstance(value, list):
                        query = query.filter(getattr(TaxForm, field).in_(value))
                    else:
                        query = query.filter(getattr(TaxForm, field) == value)
            
            # Apply pagination
            results = query.offset(offset).limit(limit).all()
            
            return [self._sql_to_record(form) for form in results]
    
    def _search_mongo_tax_forms(self, filters: Dict[str, Any], limit: int, offset: int) -> List[TaxFormRecord]:
        """Search tax forms using MongoDB"""
        # Convert filters to MongoDB query
        mongo_filters = {}
        for field, value in filters.items():
            if isinstance(value, list):
                mongo_filters[field] = {'$in': value}
            else:
                mongo_filters[field] = value
        
        cursor = self.collection.find(mongo_filters).skip(offset).limit(limit)
        
        results = []
        for doc in cursor:
            doc.pop('_id', None)
            results.append(TaxFormRecord(**doc))
        
        return results
    
    def _sql_to_record(self, tax_form: TaxForm) -> TaxFormRecord:
        """Convert SQLAlchemy model to TaxFormRecord"""
        return TaxFormRecord(
            id=tax_form.id,
            form_id=tax_form.form_id,
            form_type=tax_form.form_type,
            form_name=tax_form.form_name,
            tax_year=tax_form.tax_year,
            file_path=tax_form.file_path,
            processing_status=tax_form.processing_status,
            fields_extracted=tax_form.fields_extracted,
            confidence_score=tax_form.confidence_score,
            validation_errors=tax_form.validation_errors,
            validation_warnings=tax_form.validation_warnings,
            created_date=tax_form.created_date,
            updated_date=tax_form.updated_date,
            processed_by=tax_form.processed_by
        )
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics for tax forms
        
        Returns:
            Dictionary with various statistics
        """
        try:
            if self.db_type in ['sqlite', 'postgresql']:
                return self._get_sql_statistics()
            elif self.db_type == 'mongodb':
                return self._get_mongo_statistics()
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            raise
    
    def _get_sql_statistics(self) -> Dict[str, Any]:
        """Get statistics using SQL database"""
        with self.get_session() as session:
            total_forms = session.query(TaxForm).count()
            
            # Get status counts
            status_counts = {}
            status_results = session.query(TaxForm.processing_status, 
                                         session.query(TaxForm).filter(TaxForm.processing_status == TaxForm.processing_status).count()
                                         ).group_by(TaxForm.processing_status).all()
            
            for status, count in status_results:
                status_counts[status] = count
            
            # Get form type counts
            type_counts = {}
            type_results = session.query(TaxForm.form_type,
                                       session.query(TaxForm).filter(TaxForm.form_type == TaxForm.form_type).count()
                                       ).group_by(TaxForm.form_type).all()
            
            for form_type, count in type_results:
                type_counts[form_type] = count
            
            # Get average confidence score
            avg_confidence = session.query(session.query(TaxForm.confidence_score).filter(TaxForm.confidence_score.isnot(None)).all()).scalar()
            
            return {
                'total_forms': total_forms,
                'status_distribution': status_counts,
                'form_type_distribution': type_counts,
                'average_confidence': avg_confidence or 0.0
            }
    
    def _get_mongo_statistics(self) -> Dict[str, Any]:
        """Get statistics using MongoDB"""
        pipeline = [
            {
                '$group': {
                    '_id': None,
                    'total_forms': {'$sum': 1},
                    'avg_confidence': {'$avg': '$confidence_score'}
                }
            }
        ]
        
        stats = list(self.collection.aggregate(pipeline))[0]
        
        # Get status distribution
        status_pipeline = [
            {'$group': {'_id': '$processing_status', 'count': {'$sum': 1}}}
        ]
        status_counts = {item['_id']: item['count'] for item in self.collection.aggregate(status_pipeline)}
        
        # Get form type distribution
        type_pipeline = [
            {'$group': {'_id': '$form_type', 'count': {'$sum': 1}}}
        ]
        type_counts = {item['_id']: item['count'] for item in self.collection.aggregate(type_pipeline)}
        
        return {
            'total_forms': stats['total_forms'],
            'status_distribution': status_counts,
            'form_type_distribution': type_counts,
            'average_confidence': stats['avg_confidence'] or 0.0
        }
    
    def _generate_form_id(self) -> str:
        """Generate a unique form ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        import random
        random_suffix = str(random.randint(1000, 9999))
        return f"FORM_{timestamp}_{random_suffix}"
    
    def _log_audit_action(self, table_name: str, record_id: str, action: str, 
                         old_values: Optional[Dict], new_values: Optional[Dict]):
        """Log audit action"""
        try:
            if self.db_type in ['sqlite', 'postgresql']:
                with self.get_session() as session:
                    audit_log = AuditLog(
                        table_name=table_name,
                        record_id=record_id,
                        action=action,
                        old_values=old_values,
                        new_values=new_values,
                        user_id=os.getenv('USER', 'system'),
                        ip_address='127.0.0.1'  # Could be enhanced to get actual IP
                    )
                    session.add(audit_log)
            elif self.db_type == 'mongodb':
                audit_doc = {
                    'table_name': table_name,
                    'record_id': record_id,
                    'action': action,
                    'old_values': old_values,
                    'new_values': new_values,
                    'user_id': os.getenv('USER', 'system'),
                    'timestamp': datetime.utcnow(),
                    'ip_address': '127.0.0.1'
                }
                self.audit_collection.insert_one(audit_doc)
        except Exception as e:
            logger.warning(f"Failed to log audit action: {str(e)}")
    
    def backup_data(self, backup_path: str) -> bool:
        """
        Create a backup of the database
        
        Args:
            backup_path: Path where backup should be stored
            
        Returns:
            True if backup was successful
        """
        try:
            if self.db_type == 'sqlite':
                import shutil
                db_path = self.connection_string.replace('sqlite:///', '')
                shutil.copy2(db_path, backup_path)
                return True
            elif self.db_type == 'postgresql':
                # This would require pg_dump - simplified implementation
                logger.warning("PostgreSQL backup requires pg_dump utility")
                return False
            elif self.db_type == 'mongodb':
                # This would require mongodump - simplified implementation
                logger.warning("MongoDB backup requires mongodump utility")
                return False
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return False
    
    def close_connection(self):
        """Close database connections"""
        try:
            if self.db_type == 'mongodb' and hasattr(self, 'client'):
                self.client.close()
            elif self.db_type in ['sqlite', 'postgresql'] and hasattr(self, 'engine'):
                self.engine.dispose()
        except Exception as e:
            logger.error(f"Error closing connection: {str(e)}")


if __name__ == "__main__":
    # Example usage
    db_handler = DatabaseHandler(db_type='sqlite')
    
    # Create a sample tax form record
    sample_form = TaxFormRecord(
        form_type='1040',
        form_name='Individual Income Tax Return',
        tax_year=2023,
        file_path='/uploads/sample_1040.pdf',
        processing_status='processed',
        fields_extracted={'name': 'John Doe', 'ssn': '123-45-6789'},
        confidence_score=0.95
    )
    
    try:
        # Insert the record
        form_id = db_handler.insert_tax_form(sample_form)
        print(f"Inserted form with ID: {form_id}")
        
        # Retrieve the record
        retrieved_form = db_handler.get_tax_form(form_id)
        print(f"Retrieved form: {retrieved_form.form_type}")
        
        # Get statistics
        stats = db_handler.get_processing_statistics()
        print(f"Database statistics: {stats}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db_handler.close_connection()