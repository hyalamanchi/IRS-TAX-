"""
Database Handler Module for IRS Tax Forms

This module provides database functionality for storing extracted tax form data
using MySQL with mysql-connector-python.
"""

import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DBHandler:
    """
    Database handler for storing tax form data in MySQL
    """
    
    def __init__(self, host='localhost', user='root', password='', database='tax_forms_db'):
        """
        Initialize database connection
        
        Args:
            host (str): MySQL host
            user (str): MySQL username
            password (str): MySQL password
            database (str): Database name
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        
    def connect(self):
        """
        Connect to MySQL database
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            
            if self.connection.is_connected():
                logger.info(f"Successfully connected to MySQL database: {self.database}")
                return True
                
        except Error as e:
            logger.error(f"Error connecting to MySQL database: {e}")
            return False
            
    def create_tables(self):
        """
        Create necessary tables for storing tax form data
        
        Returns:
            bool: True if tables created successfully, False otherwise
        """
        try:
            cursor = self.connection.cursor()
            
            # Create tax_forms table
            create_tax_forms_table = """
            CREATE TABLE IF NOT EXISTS tax_forms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                form_id VARCHAR(50) NOT NULL,
                form_type VARCHAR(20),
                taxpayer_name VARCHAR(100),
                ssn VARCHAR(11),
                filing_status VARCHAR(50),
                tax_year INT,
                wages DECIMAL(12,2),
                federal_tax_withheld DECIMAL(12,2),
                address VARCHAR(200),
                city VARCHAR(50),
                state VARCHAR(2),
                zip_code VARCHAR(10),
                raw_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
            
            cursor.execute(create_tax_forms_table)
            
            # Create processing_log table
            create_log_table = """
            CREATE TABLE IF NOT EXISTS processing_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                form_id VARCHAR(50),
                processing_status VARCHAR(20),
                error_message TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            
            cursor.execute(create_log_table)
            
            self.connection.commit()
            logger.info("Database tables created successfully")
            return True
            
        except Error as e:
            logger.error(f"Error creating tables: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
    
    def insert_form_data(self, form_data):
        """
        Insert tax form data into database
        
        Args:
            form_data (dict): Dictionary containing form data
            
        Returns:
            int: Inserted record ID if successful, None otherwise
        """
        try:
            cursor = self.connection.cursor()
            
            insert_query = """
            INSERT INTO tax_forms (
                form_id, form_type, taxpayer_name, ssn, filing_status,
                tax_year, wages, federal_tax_withheld, address, city,
                state, zip_code, raw_text
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                form_data.get('form_id'),
                form_data.get('form_type'),
                form_data.get('name'),
                form_data.get('ssn'),
                form_data.get('filing_status'),
                form_data.get('tax_year'),
                form_data.get('wages'),
                form_data.get('federal_tax_withheld'),
                form_data.get('address'),
                form_data.get('city'),
                form_data.get('state'),
                form_data.get('zip_code'),
                form_data.get('raw_text')
            )
            
            cursor.execute(insert_query, values)
            self.connection.commit()
            
            record_id = cursor.lastrowid
            logger.info(f"Successfully inserted form data with ID: {record_id}")
            return record_id
            
        except Error as e:
            logger.error(f"Error inserting form data: {e}")
            self.connection.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
    
    def get_form_by_id(self, form_id):
        """
        Retrieve tax form data by form ID
        
        Args:
            form_id (str): Form ID to search for
            
        Returns:
            dict: Form data if found, None otherwise
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            select_query = "SELECT * FROM tax_forms WHERE form_id = %s"
            cursor.execute(select_query, (form_id,))
            
            result = cursor.fetchone()
            
            if result:
                logger.info(f"Retrieved form data for ID: {form_id}")
                return result
            else:
                logger.warning(f"No form found with ID: {form_id}")
                return None
                
        except Error as e:
            logger.error(f"Error retrieving form data: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def update_form_data(self, form_id, update_data):
        """
        Update existing tax form data
        
        Args:
            form_id (str): Form ID to update
            update_data (dict): Data to update
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            cursor = self.connection.cursor()
            
            # Build dynamic update query
            set_clauses = []
            values = []
            
            for field, value in update_data.items():
                if field != 'form_id':  # Don't allow updating form_id
                    set_clauses.append(f"{field} = %s")
                    values.append(value)
            
            if not set_clauses:
                logger.warning("No valid fields to update")
                return False
            
            values.append(form_id)  # Add form_id for WHERE clause
            
            update_query = f"""
            UPDATE tax_forms 
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
            WHERE form_id = %s
            """
            
            cursor.execute(update_query, values)
            self.connection.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Successfully updated form: {form_id}")
                return True
            else:
                logger.warning(f"No form found to update with ID: {form_id}")
                return False
                
        except Error as e:
            logger.error(f"Error updating form data: {e}")
            self.connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
    
    def delete_form(self, form_id):
        """
        Delete tax form data by form ID
        
        Args:
            form_id (str): Form ID to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            cursor = self.connection.cursor()
            
            delete_query = "DELETE FROM tax_forms WHERE form_id = %s"
            cursor.execute(delete_query, (form_id,))
            self.connection.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Successfully deleted form: {form_id}")
                return True
            else:
                logger.warning(f"No form found to delete with ID: {form_id}")
                return False
                
        except Error as e:
            logger.error(f"Error deleting form data: {e}")
            self.connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
    
    def get_all_forms(self, limit=100):
        """
        Retrieve all tax forms with optional limit
        
        Args:
            limit (int): Maximum number of records to return
            
        Returns:
            list: List of form data dictionaries
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            select_query = "SELECT * FROM tax_forms ORDER BY created_at DESC LIMIT %s"
            cursor.execute(select_query, (limit,))
            
            results = cursor.fetchall()
            logger.info(f"Retrieved {len(results)} forms from database")
            return results
            
        except Error as e:
            logger.error(f"Error retrieving all forms: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
    
    def log_processing(self, form_id, status, error_message=None):
        """
        Log processing status for a form
        
        Args:
            form_id (str): Form ID
            status (str): Processing status
            error_message (str): Error message if any
            
        Returns:
            bool: True if logging successful, False otherwise
        """
        try:
            cursor = self.connection.cursor()
            
            insert_query = """
            INSERT INTO processing_log (form_id, processing_status, error_message)
            VALUES (%s, %s, %s)
            """
            
            cursor.execute(insert_query, (form_id, status, error_message))
            self.connection.commit()
            
            logger.info(f"Logged processing status for {form_id}: {status}")
            return True
            
        except Error as e:
            logger.error(f"Error logging processing status: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
    
    def close_connection(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    # Example usage
    db = DBHandler()
    
    try:
        # Connect to database
        if db.connect():
            # Create tables
            db.create_tables()
            
            # Sample form data
            sample_data = {
                'form_id': 'FORM_001',
                'form_type': '1040',
                'name': 'John Smith',
                'ssn': '123-45-6789',
                'filing_status': 'Single',
                'tax_year': 2023,
                'wages': 45000.00,
                'federal_tax_withheld': 5400.00,
                'address': '123 Main St',
                'city': 'Anytown',
                'state': 'CA',
                'zip_code': '90210',
                'raw_text': 'Sample tax form text...'
            }
            
            # Insert data
            record_id = db.insert_form_data(sample_data)
            if record_id:
                print(f"Inserted record with ID: {record_id}")
                
                # Retrieve data
                retrieved = db.get_form_by_id('FORM_001')
                if retrieved:
                    print(f"Retrieved form: {retrieved['taxpayer_name']}")
                
                # Log processing
                db.log_processing('FORM_001', 'SUCCESS')
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close_connection()