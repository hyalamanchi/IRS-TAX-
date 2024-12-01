"""
Main Module for IRS Tax Form Parser

This module orchestrates the processing of tax forms using OCR, NLP, database, and e-filing components.
"""

import os
import sys
import logging
from datetime import datetime

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ocr_parser import OCRParser
from nlp_processor import NLPProcessor
from db_handler import DBHandler
from efiling_integration import EFilingIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tax_parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TaxFormProcessor:
    """
    Main processor class that coordinates all components
    """
    
    def __init__(self, db_config=None):
        """
        Initialize the tax form processor
        
        Args:
            db_config (dict): Database configuration (optional)
        """
        try:
            # Initialize components
            self.ocr_parser = OCRParser()
            self.nlp_processor = NLPProcessor()
            
            # Initialize database handler
            if db_config:
                self.db_handler = DBHandler(**db_config)
            else:
                self.db_handler = DBHandler()
                
            # Initialize e-filing integration
            self.efiling = EFilingIntegration()
            
            logger.info("TaxFormProcessor initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing TaxFormProcessor: {str(e)}")
            raise
    
    def process_csv_file(self, csv_path):
        """
        Process tax forms from CSV file
        
        Args:
            csv_path (str): Path to CSV file containing tax form data
            
        Returns:
            list: List of processing results
        """
        try:
            logger.info(f"Processing CSV file: {csv_path}")
            
            # Read tax forms from CSV
            forms_data = self.ocr_parser.read_csv(csv_path)
            
            results = []
            for form_data in forms_data:
                result = self.process_single_form(form_data)
                results.append(result)
            
            logger.info(f"Processed {len(results)} forms from CSV")
            return results
            
        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
            raise
    
    def process_single_form(self, form_data):
        """
        Process a single tax form
        
        Args:
            form_data (dict): Form data with form_id and raw_text
            
        Returns:
            dict: Processing result
        """
        try:
            form_id = form_data['form_id']
            raw_text = form_data['raw_text']
            
            logger.info(f"Processing form: {form_id}")
            
            # Extract structured data using NLP
            extracted_fields = self.nlp_processor.extract_fields(raw_text)
            
            # Process with spaCy for additional analysis
            spacy_results = self.nlp_processor.process_with_spacy(raw_text)
            
            # Validate extracted data
            validation_results = self.nlp_processor.validate_extracted_data(extracted_fields)
            
            # Prepare complete form data
            complete_form_data = {
                'form_id': form_id,
                'raw_text': raw_text,
                'form_type': '1040',  # Default form type
                **extracted_fields
            }
            
            # Store in database if connection is available
            if self.db_handler.connect():
                self.db_handler.create_tables()
                record_id = self.db_handler.insert_form_data(complete_form_data)
                
                # Log processing status
                if record_id:
                    status = 'SUCCESS' if validation_results['valid'] else 'WARNING'
                    self.db_handler.log_processing(form_id, status)
                else:
                    self.db_handler.log_processing(form_id, 'ERROR', 'Failed to insert data')
                
                self.db_handler.close_connection()
            
            # Prepare result
            result = {
                'form_id': form_id,
                'processing_status': 'SUCCESS' if validation_results['valid'] else 'WARNING',
                'extracted_fields': extracted_fields,
                'spacy_analysis': spacy_results,
                'validation': validation_results,
                'processed_at': datetime.now().isoformat()
            }
            
            logger.info(f"Successfully processed form: {form_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing form {form_data.get('form_id', 'unknown')}: {str(e)}")
            return {
                'form_id': form_data.get('form_id', 'unknown'),
                'processing_status': 'ERROR',
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            }
    
    def submit_for_efiling(self, form_data):
        """
        Submit processed form data for e-filing
        
        Args:
            form_data (dict): Complete form data
            
        Returns:
            dict: E-filing submission result
        """
        try:
            logger.info(f"Submitting form {form_data.get('form_id')} for e-filing")
            
            # Submit to e-filing system
            submission_result = self.efiling.submit_form(form_data)
            
            # Update database with submission status if applicable
            if hasattr(self, 'db_handler') and submission_result.get('submission_id'):
                if self.db_handler.connect():
                    status = 'SUBMITTED' if submission_result['success'] else 'SUBMISSION_FAILED'
                    error_msg = submission_result.get('error') if not submission_result['success'] else None
                    self.db_handler.log_processing(form_data['form_id'], status, error_msg)
                    self.db_handler.close_connection()
            
            return submission_result
            
        except Exception as e:
            logger.error(f"Error submitting form for e-filing: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'E-filing submission error'
            }
    
    def process_and_file(self, csv_path, submit_for_filing=False):
        """
        Complete processing workflow: parse, extract, validate, store, and optionally e-file
        
        Args:
            csv_path (str): Path to CSV file
            submit_for_filing (bool): Whether to submit for e-filing
            
        Returns:
            dict: Complete processing summary
        """
        try:
            logger.info("Starting complete processing workflow")
            
            # Process all forms from CSV
            processing_results = self.process_csv_file(csv_path)
            
            # Prepare summary
            total_forms = len(processing_results)
            successful_forms = len([r for r in processing_results if r['processing_status'] == 'SUCCESS'])
            warning_forms = len([r for r in processing_results if r['processing_status'] == 'WARNING'])
            error_forms = len([r for r in processing_results if r['processing_status'] == 'ERROR'])
            
            # E-filing submissions if requested
            efiling_results = []
            if submit_for_filing:
                logger.info("Starting e-filing submissions")
                for result in processing_results:
                    if result['processing_status'] in ['SUCCESS', 'WARNING']:
                        # Reconstruct form data for e-filing
                        form_data = {
                            'form_id': result['form_id'],
                            **result['extracted_fields']
                        }
                        efiling_result = self.submit_for_efiling(form_data)
                        efiling_results.append(efiling_result)
            
            # Prepare final summary
            summary = {
                'processing_summary': {
                    'total_forms': total_forms,
                    'successful': successful_forms,
                    'warnings': warning_forms,
                    'errors': error_forms,
                    'success_rate': (successful_forms / total_forms * 100) if total_forms > 0 else 0
                },
                'processing_results': processing_results,
                'efiling_summary': {
                    'attempted': len(efiling_results),
                    'successful': len([r for r in efiling_results if r.get('success', False)]),
                    'failed': len([r for r in efiling_results if not r.get('success', False)])
                } if submit_for_filing else None,
                'efiling_results': efiling_results if submit_for_filing else None,
                'completed_at': datetime.now().isoformat()
            }
            
            logger.info(f"Processing workflow completed: {summary['processing_summary']}")
            return summary
            
        except Exception as e:
            logger.error(f"Error in complete processing workflow: {str(e)}")
            raise


def main():
    """
    Main function to run the tax form processor
    """
    try:
        logger.info("Starting IRS Tax Form Parser")
        
        # Initialize processor
        processor = TaxFormProcessor()
        
        # Default CSV path
        csv_path = os.path.join('data', 'tax_forms.csv')
        
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found: {csv_path}")
            print(f"Error: CSV file not found at {csv_path}")
            return
        
        # Process forms
        print("Processing tax forms...")
        results = processor.process_and_file(csv_path, submit_for_filing=False)
        
        # Display results
        print("\n" + "="*50)
        print("PROCESSING RESULTS")
        print("="*50)
        
        summary = results['processing_summary']
        print(f"Total Forms Processed: {summary['total_forms']}")
        print(f"Successful: {summary['successful']}")
        print(f"Warnings: {summary['warnings']}")
        print(f"Errors: {summary['errors']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        
        print("\n" + "="*50)
        print("FORM DETAILS")
        print("="*50)
        
        for result in results['processing_results']:
            print(f"\nForm ID: {result['form_id']}")
            print(f"Status: {result['processing_status']}")
            
            if 'extracted_fields' in result:
                print("Extracted Fields:")
                for field, value in result['extracted_fields'].items():
                    print(f"  {field}: {value}")
            
            if 'validation' in result and result['validation']['errors']:
                print(f"Validation Errors: {result['validation']['errors']}")
            
            if 'error' in result:
                print(f"Error: {result['error']}")
        
        logger.info("IRS Tax Form Parser completed successfully")
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()