"""
Simple test runner to demonstrate test_main.py output
"""

import sys
import os
import unittest
from unittest.mock import patch, Mock
import tempfile
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from main import TaxFormProcessor
    print("✓ Successfully imported TaxFormProcessor")
except Exception as e:
    print(f"✗ Could not import TaxFormProcessor: {e}")
    sys.exit(1)

class SimpleTaxFormProcessorTest(unittest.TestCase):
    """Simplified version of the test_main.py tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock all components to avoid initialization issues
        with patch('main.OCRParser'), \
             patch('main.NLPProcessor'), \
             patch('main.DBHandler'), \
             patch('main.EFilingIntegration'):
            
            self.processor = TaxFormProcessor()
    
    def test_processor_initialization(self):
        """Test that processor initializes correctly"""
        print("Testing processor initialization...")
        self.assertIsNotNone(self.processor)
        print("✓ Processor initialized successfully")
    
    def test_process_single_form_mock(self):
        """Test processing a single form with mocked data"""
        print("Testing single form processing...")
        
        # Mock form data
        form_data = {
            'form_id': 'TEST_001',
            'raw_text': 'Form 1040 U.S. Individual Income Tax Return\nName: John Doe\nSSN: 123-45-6789'
        }
        
        # Mock the components
        with patch.object(self.processor, 'nlp_processor') as mock_nlp, \
             patch.object(self.processor, 'db_handler') as mock_db:
            
            # Setup mock returns
            mock_nlp.extract_fields.return_value = {
                'name': 'John Doe',
                'ssn': '123-45-6789'
            }
            mock_nlp.process_with_spacy.return_value = {'entities': []}
            mock_nlp.validate_extracted_data.return_value = {'valid': True, 'errors': [], 'warnings': []}
            
            mock_db.connect.return_value = True
            mock_db.create_tables.return_value = True
            mock_db.insert_form_data.return_value = 1
            mock_db.log_processing.return_value = True
            mock_db.close_connection.return_value = None
            
            # Process the form
            result = self.processor.process_single_form(form_data)
            
            # Check results
            self.assertEqual(result['form_id'], 'TEST_001')
            self.assertIn('extracted_fields', result)
            print("✓ Single form processed successfully")
    
    def test_csv_processing_simulation(self):
        """Test CSV processing simulation"""
        print("Testing CSV processing simulation...")
        
        # Create a temporary CSV file
        csv_path = os.path.join(self.temp_dir, 'test_forms.csv')
        with open(csv_path, 'w') as f:
            f.write("form_id,raw_text\n")
            f.write("FORM_001,Form 1040 test data\n")
            f.write("FORM_002,Form 1040 test data 2\n")
        
        # Mock the OCR parser
        with patch.object(self.processor, 'ocr_parser') as mock_ocr:
            mock_ocr.read_csv.return_value = [
                {'form_id': 'FORM_001', 'raw_text': 'Form 1040 test data'},
                {'form_id': 'FORM_002', 'raw_text': 'Form 1040 test data 2'}
            ]
            
            # Mock other components
            with patch.object(self.processor, 'process_single_form') as mock_process:
                mock_process.return_value = {
                    'form_id': 'TEST',
                    'processing_status': 'SUCCESS',
                    'extracted_fields': {}
                }
                
                # Process CSV
                results = self.processor.process_csv_file(csv_path)
                
                self.assertEqual(len(results), 2)
                print("✓ CSV processing simulation completed")
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

def run_demo_tests():
    """Run demonstration tests"""
    print("=" * 60)
    print("DEMO: IRS Tax Form Parser - Test Output")
    print("=" * 60)
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(SimpleTaxFormProcessorTest)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback}")
    
    print("\n" + "=" * 60)
    print("This demonstrates the functionality that would be tested")
    print("in the full test_main.py file with all components mocked.")
    print("=" * 60)

if __name__ == '__main__':
    run_demo_tests()