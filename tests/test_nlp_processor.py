"""
Test module for NLP Processor functionality
"""

import unittest
from unittest.mock import patch, Mock
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.nlp_processor import NLPProcessor, EntityExtraction, ValidationResult


class TestNLPProcessor(unittest.TestCase):
    """Test cases for NLP Processor"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Initialize with mock to avoid loading heavy models in tests
        with patch('src.nlp_processor.spacy.load'):
            with patch('src.nlp_processor.pipeline'):
                self.processor = NLPProcessor()
    
    def test_initialization(self):
        """Test NLP Processor initialization"""
        self.assertIsInstance(self.processor, NLPProcessor)
        self.assertIn('ssn', self.processor.tax_patterns)
        self.assertIn('ein', self.processor.tax_patterns)
    
    def test_extract_pattern_entities(self):
        """Test pattern-based entity extraction"""
        text = "SSN: 123-45-6789, EIN: 12-3456789, Phone: 555-123-4567"
        
        entities = self.processor._extract_pattern_entities(text)
        
        self.assertGreater(len(entities), 0)
        
        # Check for SSN entity
        ssn_entities = [e for e in entities if e.entity_type == 'ssn']
        self.assertEqual(len(ssn_entities), 1)
        self.assertEqual(ssn_entities[0].entity_value, '123-45-6789')
        
        # Check for EIN entity
        ein_entities = [e for e in entities if e.entity_type == 'ein']
        self.assertEqual(len(ein_entities), 1)
        self.assertEqual(ein_entities[0].entity_value, '12-3456789')
    
    def test_merge_overlapping_entities(self):
        """Test entity merging functionality"""
        entities = [
            EntityExtraction('PERSON', 'John', 0.8, 0, 4),
            EntityExtraction('NAME', 'John Doe', 0.9, 0, 8),  # Overlapping with higher confidence
            EntityExtraction('ORG', 'Company', 0.7, 20, 27)
        ]
        
        merged = self.processor._merge_overlapping_entities(entities)
        
        self.assertEqual(len(merged), 2)  # Should merge the overlapping ones
        self.assertEqual(merged[0].entity_value, 'John Doe')  # Higher confidence should win
        self.assertEqual(merged[0].confidence, 0.9)
    
    def test_validate_extracted_data_1040(self):
        """Test validation for Form 1040"""
        # Valid data
        valid_data = {
            'name': 'John Doe',
            'ssn': '123-45-6789',
            'filing_status': 'single',
            'total_income': '50000'
        }
        
        result = self.processor.validate_extracted_data('1040', valid_data)
        
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertGreater(result.confidence, 0.5)
    
    def test_validate_extracted_data_missing_required(self):
        """Test validation with missing required fields"""
        invalid_data = {
            'name': 'John Doe',
            # Missing SSN, filing_status, total_income
        }
        
        result = self.processor.validate_extracted_data('1040', invalid_data)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
        self.assertLess(result.confidence, 0.5)
    
    def test_validate_extracted_data_invalid_ssn(self):
        """Test validation with invalid SSN"""
        data_with_invalid_ssn = {
            'name': 'John Doe',
            'ssn': '123-45-67890',  # Too many digits
            'filing_status': 'single',
            'total_income': '50000'
        }
        
        result = self.processor.validate_extracted_data('1040', data_with_invalid_ssn)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any('Invalid SSN format' in error for error in result.errors))
    
    def test_classify_form_content(self):
        """Test form content classification"""
        text_1040 = "Individual Income Tax Return filing status standard deduction taxable income"
        scores = self.processor.classify_form_content(text_1040)
        
        self.assertIsInstance(scores, dict)
        self.assertIn('1040', scores)
        self.assertGreater(scores['1040'], scores.get('W2', 0))
    
    def test_extract_financial_amounts(self):
        """Test financial amount extraction"""
        text = "Total income: $75,000.00, Tax withheld: $8,500, Refund: $1,200.50"
        
        amounts = self.processor.extract_financial_amounts(text)
        
        self.assertEqual(len(amounts), 3)
        self.assertEqual(amounts[0]['amount'], 75000.0)
        self.assertEqual(amounts[1]['amount'], 8500.0)
        self.assertEqual(amounts[2]['amount'], 1200.5)
    
    def test_calculate_text_similarity(self):
        """Test text similarity calculation"""
        text1 = "Form 1040 Individual Income Tax Return"
        text2 = "Form 1040 U.S. Individual Income Tax Return"
        text3 = "Form W2 Wage and Tax Statement"
        
        # Similar texts should have high similarity
        similarity_high = self.processor.calculate_text_similarity(text1, text2)
        self.assertGreater(similarity_high, 0.5)
        
        # Different texts should have lower similarity
        similarity_low = self.processor.calculate_text_similarity(text1, text3)
        self.assertLess(similarity_low, similarity_high)
    
    def test_process_tax_form_text(self):
        """Test complete tax form text processing"""
        sample_text = """
        Form 1040 - U.S. Individual Income Tax Return
        
        Name: John Doe
        Social Security Number: 123-45-6789
        Filing Status: Single
        
        Income:
        Wages: $50,000
        Interest: $500
        Total Income: $50,500
        """
        
        with patch.object(self.processor, 'extract_entities') as mock_extract:
            mock_extract.return_value = [
                EntityExtraction('PERSON', 'John Doe', 0.9, 0, 8),
                EntityExtraction('ssn', '123-45-6789', 0.95, 10, 21)
            ]
            
            result = self.processor.process_tax_form_text(sample_text)
            
            self.assertIsInstance(result, dict)
            self.assertIn('form_type', result)
            self.assertIn('entities', result)
            self.assertIn('structured_data', result)
            self.assertIn('validation', result)
            self.assertIn('financial_amounts', result)
    
    def test_additional_validations_ssn(self):
        """Test additional SSN validations"""
        # Test placeholder SSN
        data_placeholder = {'ssn': '123-45-6789'}
        errors = []
        warnings = []
        confidence = 1.0
        
        confidence = self.processor._perform_additional_validations(
            data_placeholder, errors, warnings, confidence
        )
        
        # Should have warning for common placeholder SSN
        self.assertGreater(len(warnings), 0)
        self.assertLess(confidence, 1.0)
    
    def test_additional_validations_invalid_ssn_format(self):
        """Test SSN format validation"""
        data_invalid = {'ssn': '123-456-789'}  # Wrong format
        errors = []
        warnings = []
        confidence = 1.0
        
        confidence = self.processor._perform_additional_validations(
            data_invalid, errors, warnings, confidence
        )
        
        # Should have error for invalid format
        self.assertGreater(len(errors), 0)
        self.assertLess(confidence, 0.8)


if __name__ == '__main__':
    unittest.main()