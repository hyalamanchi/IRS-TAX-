"""
Main Application Module for IRS Tax Form Parser

This module provides the main application interface that orchestrates
all components for processing IRS tax forms from start to finish.
"""

import os
import sys
import logging
import argparse
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from pathlib import Path

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.ocr_parser import OCRParser, OCRResult
from src.nlp_processor import NLPProcessor
from src.db_handler import DatabaseHandler, TaxFormRecord
from src.efiling_integration import EFilingIntegration, EFilingConfiguration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tax_form_parser.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TaxFormProcessor:
    """
    Main tax form processing class that coordinates all components
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the tax form processor
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_configuration(config_path)
        
        # Initialize components
        logger.info("Initializing tax form processor components...")
        
        try:
            # Initialize OCR Parser
            self.ocr_parser = OCRParser(
                tesseract_path=self.config.get('tesseract_path')
            )
            logger.info("OCR Parser initialized successfully")
            
            # Initialize NLP Processor
            self.nlp_processor = NLPProcessor(
                model_name=self.config.get('nlp_model', 'dbmdz/bert-large-cased-finetuned-conll03-english')
            )
            logger.info("NLP Processor initialized successfully")
            
            # Initialize Database Handler
            self.db_handler = DatabaseHandler(
                db_type=self.config.get('database_type', 'sqlite'),
                connection_string=self.config.get('database_connection')
            )
            logger.info("Database Handler initialized successfully")
            
            # Initialize E-Filing Integration (optional)
            if self.config.get('enable_efiling', False):
                efiling_config = EFilingConfiguration(
                    service_provider=self.config.get('efiling_provider', 'irs_mef'),
                    environment=self.config.get('efiling_environment', 'test'),
                    api_endpoint=self.config.get('efiling_endpoint', ''),
                    username=self.config.get('efiling_username', ''),
                    password=self.config.get('efiling_password', ''),
                    encryption_key=self.config.get('efiling_encryption_key', '')
                )
                self.efiling_integration = EFilingIntegration(efiling_config)
                logger.info("E-Filing Integration initialized successfully")
            else:
                self.efiling_integration = None
                logger.info("E-Filing Integration disabled")
            
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            raise
    
    def _load_configuration(self, config_path: str = None) -> Dict[str, Any]:
        """Load configuration from file or environment variables"""
        config = {}
        
        # Default configuration
        default_config = {
            'database_type': 'sqlite',
            'enable_efiling': False,
            'nlp_model': 'dbmdz/bert-large-cased-finetuned-conll03-english',
            'tesseract_path': None,
            'output_directory': './output',
            'log_level': 'INFO'
        }
        
        # Load from config file if provided
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                config.update(file_config)
                logger.info(f"Configuration loaded from {config_path}")
            except Exception as e:
                logger.warning(f"Could not load config file {config_path}: {str(e)}")
        
        # Override with environment variables
        env_config = {
            'database_type': os.getenv('DB_TYPE'),
            'database_connection': os.getenv('DATABASE_URL'),
            'tesseract_path': os.getenv('TESSERACT_PATH'),
            'enable_efiling': os.getenv('ENABLE_EFILING', '').lower() == 'true',
            'efiling_provider': os.getenv('EFILING_PROVIDER'),
            'efiling_environment': os.getenv('EFILING_ENV'),
            'efiling_endpoint': os.getenv('EFILING_ENDPOINT'),
            'efiling_username': os.getenv('EFILING_USERNAME'),
            'efiling_password': os.getenv('EFILING_PASSWORD'),
            'efiling_encryption_key': os.getenv('EFILING_ENCRYPTION_KEY'),
            'output_directory': os.getenv('OUTPUT_DIR'),
            'log_level': os.getenv('LOG_LEVEL')
        }
        
        # Filter out None values and update config
        env_config = {k: v for k, v in env_config.items() if v is not None}
        config.update(env_config)
        
        # Apply defaults for missing values
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
        
        return config
    
    def process_document(self, file_path: str, form_type: str = None) -> Dict[str, Any]:
        """
        Process a complete tax form document from start to finish
        
        Args:
            file_path: Path to the document to process
            form_type: Optional form type hint
            
        Returns:
            Complete processing results
        """
        try:
            logger.info(f"Starting document processing: {file_path}")
            
            # Step 1: OCR Processing
            logger.info("Step 1: Performing OCR extraction...")
            ocr_results = self.ocr_parser.process_document(file_path)
            
            if not ocr_results:
                raise ValueError("No OCR results obtained from document")
            
            # Combine results from all pages
            combined_text = "\n".join([result.text for result in ocr_results])
            combined_confidence = sum([result.confidence for result in ocr_results]) / len(ocr_results)
            
            # Step 2: NLP Processing
            logger.info("Step 2: Performing NLP analysis...")
            nlp_results = self.nlp_processor.process_tax_form_text(combined_text, form_type)
            
            # Step 3: Data Validation and Structuring
            logger.info("Step 3: Validating and structuring data...")
            validation_result = nlp_results['validation']
            
            # Step 4: Database Storage
            logger.info("Step 4: Storing results in database...")
            form_record = TaxFormRecord(
                form_type=nlp_results['form_type'],
                form_name=self._get_form_name(nlp_results['form_type']),
                tax_year=self._extract_tax_year(nlp_results['structured_data']),
                file_path=file_path,
                processing_status='processed' if validation_result.is_valid else 'validation_errors',
                fields_extracted=nlp_results['structured_data'],
                confidence_score=min(combined_confidence, validation_result.confidence),
                validation_errors=validation_result.errors,
                validation_warnings=validation_result.warnings,
                processed_by=os.getenv('USER', 'system')
            )
            
            form_id = self.db_handler.insert_tax_form(form_record)
            
            # Step 5: E-Filing Preparation (if enabled and valid)
            efiling_result = None
            if (self.efiling_integration and 
                validation_result.is_valid and 
                self.config.get('auto_efile', False)):
                
                logger.info("Step 5: Preparing for e-filing...")
                try:
                    submission = self.efiling_integration.prepare_submission(
                        nlp_results['structured_data'],
                        nlp_results['form_type'],
                        self._extract_tax_year(nlp_results['structured_data'])
                    )
                    efiling_result = {
                        'submission_id': submission.submission_id,
                        'status': 'prepared',
                        'message': 'Ready for e-filing submission'
                    }
                except Exception as e:
                    logger.warning(f"E-filing preparation failed: {str(e)}")
                    efiling_result = {
                        'status': 'error',
                        'message': str(e)
                    }
            
            # Step 6: Generate Processing Report
            logger.info("Step 6: Generating processing report...")
            processing_result = {
                'success': True,
                'form_id': form_id,
                'processing_timestamp': datetime.utcnow().isoformat(),
                'file_path': file_path,
                'form_type': nlp_results['form_type'],
                'confidence_score': form_record.confidence_score,
                'validation': {
                    'is_valid': validation_result.is_valid,
                    'confidence': validation_result.confidence,
                    'errors': validation_result.errors,
                    'warnings': validation_result.warnings
                },
                'ocr_results': {
                    'pages_processed': len(ocr_results),
                    'average_confidence': combined_confidence,
                    'text_length': len(combined_text)
                },
                'nlp_results': {
                    'entities_found': len(nlp_results['entities']),
                    'financial_amounts': len(nlp_results['financial_amounts']),
                    'structured_fields': len(nlp_results['structured_data'])
                },
                'extracted_data': nlp_results['structured_data'],
                'efiling': efiling_result
            }
            
            # Save detailed results to file
            self._save_processing_results(processing_result)
            
            logger.info(f"Document processing completed successfully: {form_id}")
            return processing_result
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            
            # Store error in database
            error_record = TaxFormRecord(
                file_path=file_path,
                processing_status='error',
                validation_errors=[str(e)],
                processed_by=os.getenv('USER', 'system')
            )
            
            try:
                error_form_id = self.db_handler.insert_tax_form(error_record)
            except:
                error_form_id = 'unknown'
            
            return {
                'success': False,
                'form_id': error_form_id,
                'error': str(e),
                'file_path': file_path,
                'processing_timestamp': datetime.utcnow().isoformat()
            }
    
    def process_batch(self, directory_path: str, file_patterns: List[str] = None) -> Dict[str, Any]:
        """
        Process multiple documents in a directory
        
        Args:
            directory_path: Path to directory containing documents
            file_patterns: List of file patterns to match (default: ['*.pdf', '*.png', '*.jpg'])
            
        Returns:
            Batch processing results
        """
        try:
            if file_patterns is None:
                file_patterns = ['*.pdf', '*.png', '*.jpg', '*.jpeg', '*.tiff']
            
            # Find all matching files
            directory = Path(directory_path)
            files_to_process = []
            
            for pattern in file_patterns:
                files_to_process.extend(directory.glob(pattern))
            
            logger.info(f"Found {len(files_to_process)} files to process in {directory_path}")
            
            batch_results = {
                'batch_id': f"BATCH_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'start_time': datetime.utcnow().isoformat(),
                'directory': directory_path,
                'total_files': len(files_to_process),
                'processed_files': [],
                'successful_count': 0,
                'error_count': 0,
                'summary': {}
            }
            
            # Process each file
            for file_path in files_to_process:
                logger.info(f"Processing file {len(batch_results['processed_files']) + 1}/{len(files_to_process)}: {file_path}")
                
                result = self.process_document(str(file_path))
                batch_results['processed_files'].append(result)
                
                if result['success']:
                    batch_results['successful_count'] += 1
                else:
                    batch_results['error_count'] += 1
            
            # Generate batch summary
            batch_results['end_time'] = datetime.utcnow().isoformat()
            batch_results['success_rate'] = (batch_results['successful_count'] / batch_results['total_files'] * 100) if batch_results['total_files'] > 0 else 0
            
            # Form type distribution
            form_types = {}
            for result in batch_results['processed_files']:
                if result['success'] and 'form_type' in result:
                    form_type = result['form_type']
                    form_types[form_type] = form_types.get(form_type, 0) + 1
            
            batch_results['summary'] = {
                'form_type_distribution': form_types,
                'average_confidence': sum([r.get('confidence_score', 0) for r in batch_results['processed_files'] if r['success']]) / max(batch_results['successful_count'], 1)
            }
            
            # Save batch results
            self._save_batch_results(batch_results)
            
            logger.info(f"Batch processing completed: {batch_results['successful_count']}/{batch_results['total_files']} successful")
            return batch_results
            
        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            raise
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics"""
        try:
            db_stats = self.db_handler.get_processing_statistics()
            
            # Add additional statistics
            stats = {
                'database_statistics': db_stats,
                'system_info': {
                    'processor_version': '1.0.0',
                    'last_updated': datetime.utcnow().isoformat(),
                    'configuration': {
                        'database_type': self.config['database_type'],
                        'efiling_enabled': bool(self.efiling_integration),
                        'nlp_model': self.config['nlp_model']
                    }
                }
            }
            
            # Add e-filing statistics if available
            if self.efiling_integration:
                efiling_history = self.efiling_integration.get_submission_history()
                efiling_stats = {
                    'total_submissions': len(efiling_history),
                    'status_distribution': {}
                }
                
                for submission in efiling_history:
                    status = submission['status']
                    efiling_stats['status_distribution'][status] = efiling_stats['status_distribution'].get(status, 0) + 1
                
                stats['efiling_statistics'] = efiling_stats
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            raise
    
    def _get_form_name(self, form_type: str) -> str:
        """Get full form name from form type"""
        form_names = {
            '1040': 'U.S. Individual Income Tax Return',
            'W2': 'Wage and Tax Statement',
            '1099': 'Miscellaneous Income',
            'Schedule C': 'Profit or Loss From Business',
            '941': 'Employer\'s Quarterly Federal Tax Return',
            '1120': 'U.S. Corporation Income Tax Return'
        }
        return form_names.get(form_type, f'Form {form_type}')
    
    def _extract_tax_year(self, structured_data: Dict[str, Any]) -> int:
        """Extract tax year from structured data"""
        current_year = datetime.now().year
        
        # Look for tax year in various fields
        if 'tax_year' in structured_data:
            try:
                return int(structured_data['tax_year'])
            except (ValueError, TypeError):
                pass
        
        # Default to previous year (most common case)
        return current_year - 1
    
    def _save_processing_results(self, results: Dict[str, Any]):
        """Save detailed processing results to file"""
        try:
            output_dir = Path(self.config['output_directory'])
            output_dir.mkdir(exist_ok=True)
            
            filename = f"processing_result_{results['form_id']}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            output_path = output_dir / filename
            
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Processing results saved to {output_path}")
            
        except Exception as e:
            logger.warning(f"Could not save processing results: {str(e)}")
    
    def _save_batch_results(self, batch_results: Dict[str, Any]):
        """Save batch processing results to file"""
        try:
            output_dir = Path(self.config['output_directory'])
            output_dir.mkdir(exist_ok=True)
            
            filename = f"batch_result_{batch_results['batch_id']}.json"
            output_path = output_dir / filename
            
            with open(output_path, 'w') as f:
                json.dump(batch_results, f, indent=2, default=str)
            
            logger.info(f"Batch results saved to {output_path}")
            
        except Exception as e:
            logger.warning(f"Could not save batch results: {str(e)}")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description='IRS Tax Form Parser')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--file', '-f', help='Single file to process')
    parser.add_argument('--directory', '-d', help='Directory to process (batch mode)')
    parser.add_argument('--form-type', '-t', help='Form type hint')
    parser.add_argument('--stats', action='store_true', help='Show processing statistics')
    parser.add_argument('--output', '-o', help='Output directory')
    
    args = parser.parse_args()
    
    try:
        # Initialize processor
        processor = TaxFormProcessor(config_path=args.config)
        
        # Override output directory if specified
        if args.output:
            processor.config['output_directory'] = args.output
        
        if args.stats:
            # Show statistics
            stats = processor.get_processing_statistics()
            print(json.dumps(stats, indent=2, default=str))
            
        elif args.file:
            # Process single file
            result = processor.process_document(args.file, args.form_type)
            print(json.dumps(result, indent=2, default=str))
            
        elif args.directory:
            # Process directory (batch mode)
            result = processor.process_batch(args.directory)
            print(json.dumps(result, indent=2, default=str))
            
        else:
            # Interactive mode
            print("IRS Tax Form Parser - Interactive Mode")
            print("1. Process single file")
            print("2. Process directory")
            print("3. Show statistics")
            print("4. Exit")
            
            while True:
                choice = input("\nEnter your choice (1-4): ").strip()
                
                if choice == '1':
                    file_path = input("Enter file path: ").strip()
                    if os.path.exists(file_path):
                        result = processor.process_document(file_path)
                        print(f"Processing result: {result['success']}")
                        if result['success']:
                            print(f"Form ID: {result['form_id']}")
                            print(f"Form Type: {result['form_type']}")
                            print(f"Confidence: {result['confidence_score']:.2f}")
                    else:
                        print("File not found!")
                        
                elif choice == '2':
                    dir_path = input("Enter directory path: ").strip()
                    if os.path.exists(dir_path):
                        result = processor.process_batch(dir_path)
                        print(f"Batch processing completed: {result['successful_count']}/{result['total_files']} successful")
                    else:
                        print("Directory not found!")
                        
                elif choice == '3':
                    stats = processor.get_processing_statistics()
                    print("Processing Statistics:")
                    print(f"Total forms: {stats['database_statistics']['total_forms']}")
                    print(f"Average confidence: {stats['database_statistics']['average_confidence']:.2f}")
                    
                elif choice == '4':
                    print("Goodbye!")
                    break
                    
                else:
                    print("Invalid choice. Please try again.")
    
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()