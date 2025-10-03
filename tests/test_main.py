"""
Test module for Main Application functionality
"""

import unittest
import tempfile
import os
import json
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.main import TaxFormProcessor


class TestTaxFormProcessor(unittest.TestCase):
    """Test cases for Tax Form Processor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test configuration
        self.test_config = {
            'database_type': 'sqlite',
            'enable_efiling': False,
            'tesseract_path': None,
            'output_directory': self.temp_dir,
            'log_level': 'INFO'
        }
        
        # Mock all components to avoid heavy initialization
        with patch('src.main.OCRParser'), \
             patch('src.main.NLPProcessor'), \
             patch('src.main.DatabaseHandler'), \
             patch('src.main.EFilingIntegration'):
            
            self.processor = TaxFormProcessor()
            self.processor.config = self.test_config
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_load_configuration_defaults(self):
        """Test loading default configuration"""
        with patch('src.main.OCRParser'), \
             patch('src.main.NLPProcessor'), \
             patch('src.main.DatabaseHandler'):
            
            processor = TaxFormProcessor()
            config = processor.config
            
            self.assertEqual(config['database_type'], 'sqlite')
            self.assertFalse(config['enable_efiling'])
            self.assertEqual(config['log_level'], 'INFO')
    
    def test_load_configuration_from_file(self):
        """Test loading configuration from file"""
        # Create test config file
        config_file = os.path.join(self.temp_dir, 'config.json')
        test_config = {
            'database_type': 'postgresql',
            'enable_efiling': True,
            'custom_setting': 'test_value'
        }
        
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        with patch('src.main.OCRParser'), \
             patch('src.main.NLPProcessor'), \
             patch('src.main.DatabaseHandler'), \
             patch('src.main.EFilingIntegration'):
            
            processor = TaxFormProcessor(config_path=config_file)
            
            self.assertEqual(processor.config['database_type'], 'postgresql')
            self.assertTrue(processor.config['enable_efiling'])
            self.assertEqual(processor.config['custom_setting'], 'test_value')
    
    @patch.dict(os.environ, {
        'DB_TYPE': 'mongodb',
        'ENABLE_EFILING': 'true',
        'OUTPUT_DIR': '/custom/output'
    })
    def test_load_configuration_from_environment(self):
        """Test loading configuration from environment variables"""
        with patch('src.main.OCRParser'), \
             patch('src.main.NLPProcessor'), \
             patch('src.main.DatabaseHandler'), \
             patch('src.main.EFilingIntegration'):
            
            processor = TaxFormProcessor()
            
            self.assertEqual(processor.config['database_type'], 'mongodb')
            self.assertTrue(processor.config['enable_efiling'])
            self.assertEqual(processor.config['output_directory'], '/custom/output')
    
    def test_get_form_name(self):
        """Test form name retrieval"""
        self.assertEqual(self.processor._get_form_name('1040'), 'U.S. Individual Income Tax Return')
        self.assertEqual(self.processor._get_form_name('W2'), 'Wage and Tax Statement')
        self.assertEqual(self.processor._get_form_name('Unknown'), 'Form Unknown')
    
    def test_extract_tax_year(self):
        """Test tax year extraction"""
        # Test explicit tax year
        data_with_year = {'tax_year': '2023'}
        self.assertEqual(self.processor._extract_tax_year(data_with_year), 2023)
        
        # Test default to previous year
        data_without_year = {'name': 'John Doe'}
        current_year = datetime.now().year
        self.assertEqual(self.processor._extract_tax_year(data_without_year), current_year - 1)
    
    def test_process_document_success(self):
        """Test successful document processing"""
        # Mock all components
        mock_ocr_results = [Mock()]
        mock_ocr_results[0].text = "Form 1040\nName: John Doe\nSSN: 123-45-6789"
        mock_ocr_results[0].confidence = 0.95
        
        mock_nlp_results = {
            'form_type': '1040',
            'entities': [],
            'structured_data': {
                'name': 'John Doe',
                'ssn': '123-45-6789',
                'filing_status': 'single'
            },
            'financial_amounts': [],
            'validation': Mock()
        }
        mock_nlp_results['validation'].is_valid = True
        mock_nlp_results['validation'].confidence = 0.9
        mock_nlp_results['validation'].errors = []
        mock_nlp_results['validation'].warnings = []
        
        self.processor.ocr_parser.process_document.return_value = mock_ocr_results
        self.processor.nlp_processor.process_tax_form_text.return_value = mock_nlp_results
        self.processor.db_handler.insert_tax_form.return_value = 'FORM_123'
        
        # Test processing
        test_file = os.path.join(self.temp_dir, 'test_form.pdf')
        with open(test_file, 'w') as f:
            f.write("dummy content")
        
        result = self.processor.process_document(test_file)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['form_id'], 'FORM_123')
        self.assertEqual(result['form_type'], '1040')
        self.assertTrue(result['validation']['is_valid'])
    
    def test_process_document_failure(self):
        """Test document processing failure"""
        # Mock OCR parser to raise exception
        self.processor.ocr_parser.process_document.side_effect = Exception("OCR failed")
        self.processor.db_handler.insert_tax_form.return_value = 'ERROR_FORM_123'
        
        test_file = os.path.join(self.temp_dir, 'test_form.pdf')
        with open(test_file, 'w') as f:
            f.write("dummy content")
        
        result = self.processor.process_document(test_file)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'OCR failed')
    
    def test_process_batch(self):
        """Test batch processing"""
        # Create test files
        test_files = []
        for i in range(3):
            file_path = os.path.join(self.temp_dir, f'test_form_{i}.pdf')
            with open(file_path, 'w') as f:
                f.write(f"dummy content {i}")
            test_files.append(file_path)
        
        # Mock process_document to return success for all files
        def mock_process_document(file_path):
            return {
                'success': True,
                'form_id': f'FORM_{os.path.basename(file_path)}',
                'form_type': '1040',
                'confidence_score': 0.9
            }
        
        self.processor.process_document = mock_process_document
        
        result = self.processor.process_batch(self.temp_dir, ['*.pdf'])
        
        self.assertEqual(result['total_files'], 3)
        self.assertEqual(result['successful_count'], 3)
        self.assertEqual(result['error_count'], 0)
        self.assertEqual(result['success_rate'], 100.0)
    
    def test_process_batch_mixed_results(self):
        """Test batch processing with mixed success/failure results"""
        # Create test files
        for i in range(3):
            file_path = os.path.join(self.temp_dir, f'test_form_{i}.pdf')
            with open(file_path, 'w') as f:
                f.write(f"dummy content {i}")
        
        # Mock process_document to return mixed results
        def mock_process_document(file_path):
            file_name = os.path.basename(file_path)
            if '0' in file_name:
                return {'success': False, 'error': 'Processing failed'}
            else:
                return {
                    'success': True,
                    'form_id': f'FORM_{file_name}',
                    'form_type': '1040',
                    'confidence_score': 0.9
                }
        
        self.processor.process_document = mock_process_document
        
        result = self.processor.process_batch(self.temp_dir, ['*.pdf'])
        
        self.assertEqual(result['total_files'], 3)
        self.assertEqual(result['successful_count'], 2)
        self.assertEqual(result['error_count'], 1)
        self.assertAlmostEqual(result['success_rate'], 66.67, places=1)
    
    def test_get_processing_statistics(self):
        """Test getting processing statistics"""
        # Mock database statistics
        mock_db_stats = {
            'total_forms': 10,
            'status_distribution': {'processed': 8, 'pending': 2},
            'form_type_distribution': {'1040': 6, 'W2': 4},
            'average_confidence': 0.85
        }
        
        self.processor.db_handler.get_processing_statistics.return_value = mock_db_stats
        
        stats = self.processor.get_processing_statistics()
        
        self.assertIn('database_statistics', stats)
        self.assertIn('system_info', stats)
        self.assertEqual(stats['database_statistics']['total_forms'], 10)
        self.assertEqual(stats['system_info']['processor_version'], '1.0.0')
    
    def test_get_processing_statistics_with_efiling(self):
        """Test getting statistics with e-filing enabled"""
        # Enable e-filing
        self.processor.efiling_integration = Mock()
        mock_efiling_history = [
            {'status': 'transmitted', 'form_type': '1040'},
            {'status': 'pending', 'form_type': '1040'},
            {'status': 'transmitted', 'form_type': 'W2'}
        ]
        self.processor.efiling_integration.get_submission_history.return_value = mock_efiling_history
        
        # Mock database statistics
        mock_db_stats = {
            'total_forms': 5,
            'status_distribution': {'processed': 5},
            'form_type_distribution': {'1040': 3, 'W2': 2},
            'average_confidence': 0.9
        }
        self.processor.db_handler.get_processing_statistics.return_value = mock_db_stats
        
        stats = self.processor.get_processing_statistics()
        
        self.assertIn('efiling_statistics', stats)
        self.assertEqual(stats['efiling_statistics']['total_submissions'], 3)
        self.assertEqual(stats['efiling_statistics']['status_distribution']['transmitted'], 2)
        self.assertEqual(stats['efiling_statistics']['status_distribution']['pending'], 1)
    
    def test_save_processing_results(self):
        """Test saving processing results to file"""
        test_results = {
            'success': True,
            'form_id': 'FORM_123',
            'form_type': '1040',
            'confidence_score': 0.95
        }
        
        self.processor._save_processing_results(test_results)
        
        # Check if file was created
        output_files = os.listdir(self.temp_dir)
        result_files = [f for f in output_files if f.startswith('processing_result_')]
        
        self.assertEqual(len(result_files), 1)
        
        # Verify file content
        with open(os.path.join(self.temp_dir, result_files[0]), 'r') as f:
            saved_results = json.load(f)
        
        self.assertEqual(saved_results['form_id'], 'FORM_123')
        self.assertEqual(saved_results['form_type'], '1040')
    
    def test_save_batch_results(self):
        """Test saving batch processing results to file"""
        test_batch_results = {
            'batch_id': 'BATCH_20240101_120000',
            'total_files': 5,
            'successful_count': 4,
            'error_count': 1
        }
        
        self.processor._save_batch_results(test_batch_results)
        
        # Check if file was created
        output_files = os.listdir(self.temp_dir)
        batch_files = [f for f in output_files if f.startswith('batch_result_')]
        
        self.assertEqual(len(batch_files), 1)
        
        # Verify file content
        with open(os.path.join(self.temp_dir, batch_files[0]), 'r') as f:
            saved_results = json.load(f)
        
        self.assertEqual(saved_results['batch_id'], 'BATCH_20240101_120000')
        self.assertEqual(saved_results['total_files'], 5)


class TestMainCLI(unittest.TestCase):
    """Test cases for Main CLI functionality"""
    
    @patch('src.main.TaxFormProcessor')
    @patch('sys.argv', ['main.py', '--stats'])
    def test_cli_stats_command(self, mock_processor_class):
        """Test CLI stats command"""
        mock_processor = Mock()
        mock_stats = {
            'database_statistics': {'total_forms': 10},
            'system_info': {'processor_version': '1.0.0'}
        }
        mock_processor.get_processing_statistics.return_value = mock_stats
        mock_processor_class.return_value = mock_processor
        
        with patch('builtins.print') as mock_print:
            from src.main import main
            main()
            
            # Verify stats were printed
            mock_print.assert_called()
            printed_output = mock_print.call_args[0][0]
            self.assertIn('total_forms', printed_output)
    
    @patch('src.main.TaxFormProcessor')
    @patch('os.path.exists', return_value=True)
    @patch('sys.argv', ['main.py', '--file', 'test.pdf'])
    def test_cli_file_command(self, mock_exists, mock_processor_class):
        """Test CLI single file processing command"""
        mock_processor = Mock()
        mock_result = {
            'success': True,
            'form_id': 'FORM_123',
            'form_type': '1040'
        }
        mock_processor.process_document.return_value = mock_result
        mock_processor_class.return_value = mock_processor
        
        with patch('builtins.print') as mock_print:
            from src.main import main
            main()
            
            # Verify file was processed
            mock_processor.process_document.assert_called_once_with('test.pdf', None)
            mock_print.assert_called()
    
    @patch('src.main.TaxFormProcessor')
    @patch('os.path.exists', return_value=True)
    @patch('sys.argv', ['main.py', '--directory', '/test/dir'])
    def test_cli_directory_command(self, mock_exists, mock_processor_class):
        """Test CLI directory processing command"""
        mock_processor = Mock()
        mock_batch_result = {
            'successful_count': 5,
            'total_files': 6,
            'error_count': 1
        }
        mock_processor.process_batch.return_value = mock_batch_result
        mock_processor_class.return_value = mock_processor
        
        with patch('builtins.print') as mock_print:
            from src.main import main
            main()
            
            # Verify batch processing was called
            mock_processor.process_batch.assert_called_once_with('/test/dir')
            mock_print.assert_called()


if __name__ == '__main__':
    unittest.main()