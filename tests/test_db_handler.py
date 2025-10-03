"""
Test module for Database Handler functionality
"""

import unittest
import tempfile
import os
from unittest.mock import patch, Mock
from datetime import datetime
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.db_handler import DatabaseHandler, TaxFormRecord


class TestDatabaseHandler(unittest.TestCase):
    """Test cases for Database Handler"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Use temporary SQLite database for testing
        self.temp_db_path = tempfile.mktemp(suffix='.db')
        connection_string = f"sqlite:///{self.temp_db_path}"
        self.db_handler = DatabaseHandler(db_type='sqlite', connection_string=connection_string)
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.db_handler.close_connection()
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)
    
    def test_initialization(self):
        """Test database handler initialization"""
        self.assertIsInstance(self.db_handler, DatabaseHandler)
        self.assertEqual(self.db_handler.db_type, 'sqlite')
    
    def test_insert_tax_form(self):
        """Test inserting a tax form record"""
        # Create test record
        test_record = TaxFormRecord(
            form_type='1040',
            form_name='Individual Income Tax Return',
            tax_year=2023,
            file_path='/test/path/form.pdf',
            processing_status='processed',
            fields_extracted={'name': 'John Doe', 'ssn': '123-45-6789'},
            confidence_score=0.95
        )
        
        # Insert record
        form_id = self.db_handler.insert_tax_form(test_record)
        
        self.assertIsNotNone(form_id)
        self.assertTrue(form_id.startswith('FORM_'))
    
    def test_get_tax_form(self):
        """Test retrieving a tax form record"""
        # Insert test record first
        test_record = TaxFormRecord(
            form_type='W2',
            form_name='Wage and Tax Statement',
            tax_year=2023,
            file_path='/test/path/w2.pdf',
            processing_status='processed',
            confidence_score=0.88
        )
        
        form_id = self.db_handler.insert_tax_form(test_record)
        
        # Retrieve the record
        retrieved_record = self.db_handler.get_tax_form(form_id)
        
        self.assertIsNotNone(retrieved_record)
        self.assertEqual(retrieved_record.form_type, 'W2')
        self.assertEqual(retrieved_record.form_name, 'Wage and Tax Statement')
        self.assertEqual(retrieved_record.confidence_score, 0.88)
    
    def test_get_nonexistent_tax_form(self):
        """Test retrieving a non-existent tax form"""
        result = self.db_handler.get_tax_form('NONEXISTENT_FORM_ID')
        self.assertIsNone(result)
    
    def test_update_tax_form(self):
        """Test updating a tax form record"""
        # Insert test record first
        test_record = TaxFormRecord(
            form_type='1040',
            processing_status='pending',
            confidence_score=0.7
        )
        
        form_id = self.db_handler.insert_tax_form(test_record)
        
        # Update the record
        updates = {
            'processing_status': 'processed',
            'confidence_score': 0.95,
            'fields_extracted': {'name': 'Updated Name'}
        }
        
        success = self.db_handler.update_tax_form(form_id, updates)
        self.assertTrue(success)
        
        # Verify the update
        updated_record = self.db_handler.get_tax_form(form_id)
        self.assertEqual(updated_record.processing_status, 'processed')
        self.assertEqual(updated_record.confidence_score, 0.95)
    
    def test_update_nonexistent_tax_form(self):
        """Test updating a non-existent tax form"""
        success = self.db_handler.update_tax_form('NONEXISTENT_ID', {'status': 'processed'})
        self.assertFalse(success)
    
    def test_search_tax_forms(self):
        """Test searching tax forms with filters"""
        # Insert multiple test records
        records = [
            TaxFormRecord(form_type='1040', tax_year=2023, processing_status='processed'),
            TaxFormRecord(form_type='1040', tax_year=2022, processing_status='pending'),
            TaxFormRecord(form_type='W2', tax_year=2023, processing_status='processed'),
        ]
        
        for record in records:
            self.db_handler.insert_tax_form(record)
        
        # Search by form type
        results_1040 = self.db_handler.search_tax_forms({'form_type': '1040'})
        self.assertEqual(len(results_1040), 2)
        
        # Search by status
        results_processed = self.db_handler.search_tax_forms({'processing_status': 'processed'})
        self.assertEqual(len(results_processed), 2)
        
        # Search by multiple criteria
        results_combined = self.db_handler.search_tax_forms({
            'form_type': '1040',
            'processing_status': 'processed'
        })
        self.assertEqual(len(results_combined), 1)
    
    def test_get_processing_statistics(self):
        """Test getting processing statistics"""
        # Insert test records with various statuses and types
        records = [
            TaxFormRecord(form_type='1040', processing_status='processed', confidence_score=0.9),
            TaxFormRecord(form_type='1040', processing_status='pending', confidence_score=0.8),
            TaxFormRecord(form_type='W2', processing_status='processed', confidence_score=0.95),
            TaxFormRecord(form_type='W2', processing_status='error', confidence_score=0.3),
        ]
        
        for record in records:
            self.db_handler.insert_tax_form(record)
        
        stats = self.db_handler.get_processing_statistics()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('total_forms', stats)
        self.assertIn('status_distribution', stats)
        self.assertIn('form_type_distribution', stats)
        self.assertEqual(stats['total_forms'], 4)
    
    def test_generate_form_id(self):
        """Test form ID generation"""
        form_id1 = self.db_handler._generate_form_id()
        form_id2 = self.db_handler._generate_form_id()
        
        self.assertTrue(form_id1.startswith('FORM_'))
        self.assertTrue(form_id2.startswith('FORM_'))
        self.assertNotEqual(form_id1, form_id2)  # Should be unique
    
    def test_search_with_pagination(self):
        """Test search with pagination"""
        # Insert multiple records
        for i in range(5):
            record = TaxFormRecord(
                form_type='1040',
                processing_status='processed',
                confidence_score=0.9
            )
            self.db_handler.insert_tax_form(record)
        
        # Test pagination
        results_page1 = self.db_handler.search_tax_forms({'form_type': '1040'}, limit=3, offset=0)
        results_page2 = self.db_handler.search_tax_forms({'form_type': '1040'}, limit=3, offset=3)
        
        self.assertEqual(len(results_page1), 3)
        self.assertEqual(len(results_page2), 2)
    
    def test_invalid_database_type(self):
        """Test initialization with invalid database type"""
        with self.assertRaises(ValueError):
            DatabaseHandler(db_type='invalid_type')
    
    def test_sql_to_record_conversion(self):
        """Test conversion from SQLAlchemy model to TaxFormRecord"""
        # Insert a record
        test_record = TaxFormRecord(
            form_type='1099',
            form_name='Miscellaneous Income',
            tax_year=2023,
            confidence_score=0.87
        )
        
        form_id = self.db_handler.insert_tax_form(test_record)
        retrieved_record = self.db_handler.get_tax_form(form_id)
        
        # Verify all fields are properly converted
        self.assertIsInstance(retrieved_record, TaxFormRecord)
        self.assertEqual(retrieved_record.form_type, '1099')
        self.assertEqual(retrieved_record.form_name, 'Miscellaneous Income')
        self.assertEqual(retrieved_record.tax_year, 2023)
        self.assertEqual(retrieved_record.confidence_score, 0.87)


class TestDatabaseHandlerMongoDB(unittest.TestCase):
    """Test cases for MongoDB Database Handler"""
    
    @patch('src.db_handler.pymongo.MongoClient')
    def test_mongodb_initialization(self, mock_mongo_client):
        """Test MongoDB database handler initialization"""
        mock_client = Mock()
        mock_db = Mock()
        mock_collection = Mock()
        
        mock_mongo_client.return_value = mock_client
        mock_client.tax_forms_db = mock_db
        mock_db.tax_forms = mock_collection
        
        db_handler = DatabaseHandler(db_type='mongodb', connection_string='mongodb://localhost:27017/')
        
        self.assertEqual(db_handler.db_type, 'mongodb')
        mock_mongo_client.assert_called_once_with('mongodb://localhost:27017/')
    
    @patch('src.db_handler.pymongo.MongoClient')
    def test_mongodb_insert_tax_form(self, mock_mongo_client):
        """Test inserting tax form in MongoDB"""
        # Setup mocks
        mock_client = Mock()
        mock_db = Mock()
        mock_collection = Mock()
        mock_audit_collection = Mock()
        
        mock_mongo_client.return_value = mock_client
        mock_client.tax_forms_db = mock_db
        mock_db.tax_forms = mock_collection
        mock_db.audit_logs = mock_audit_collection
        
        # Mock insert result
        mock_result = Mock()
        mock_result.inserted_id = 'test_object_id'
        mock_collection.insert_one.return_value = mock_result
        
        db_handler = DatabaseHandler(db_type='mongodb')
        
        test_record = TaxFormRecord(
            form_type='1040',
            form_name='Individual Income Tax Return'
        )
        
        form_id = db_handler.insert_tax_form(test_record)
        
        self.assertIsNotNone(form_id)
        mock_collection.insert_one.assert_called_once()


if __name__ == '__main__':
    unittest.main()