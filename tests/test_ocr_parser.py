"""
Test module for OCR Parser functionality
"""

import unittest
import tempfile
import os
from unittest.mock import patch, Mock, MagicMock
import numpy as np
from PIL import Image
import cv2

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.ocr_parser import OCRParser, OCRResult


class TestOCRParser(unittest.TestCase):
    """Test cases for OCR Parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.parser = OCRParser()
        
        # Create a temporary test image
        self.temp_dir = tempfile.mkdtemp()
        self.test_image_path = os.path.join(self.temp_dir, 'test_form.png')
        
        # Create a simple test image with text
        img = Image.new('RGB', (800, 600), color='white')
        img.save(self.test_image_path)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_image_path):
            os.remove(self.test_image_path)
        os.rmdir(self.temp_dir)
    
    def test_initialization(self):
        """Test OCR Parser initialization"""
        parser = OCRParser()
        self.assertIsInstance(parser, OCRParser)
        self.assertIn('1040', parser.form_patterns)
        self.assertIn('W2', parser.form_patterns)
    
    def test_preprocess_image(self):
        """Test image preprocessing"""
        processed_image = self.parser.preprocess_image(self.test_image_path)
        self.assertIsInstance(processed_image, np.ndarray)
        self.assertEqual(len(processed_image.shape), 2)  # Should be grayscale
    
    @patch('pytesseract.image_to_data')
    @patch('pytesseract.image_to_string')
    def test_extract_text_from_image(self, mock_string, mock_data):
        """Test text extraction from image"""
        # Mock pytesseract responses
        mock_data.return_value = {
            'text': ['Form', '1040', 'John', 'Doe'],
            'conf': [95, 90, 85, 88],
            'left': [10, 50, 100, 150],
            'top': [10, 10, 50, 50],
            'width': [40, 40, 40, 40],
            'height': [20, 20, 20, 20]
        }
        mock_string.return_value = "Form 1040\nJohn Doe"
        
        result = self.parser.extract_text_from_image(self.test_image_path)
        
        self.assertIsInstance(result, OCRResult)
        self.assertEqual(result.text, "Form 1040\nJohn Doe")
        self.assertGreater(result.confidence, 0)
        self.assertGreater(len(result.bounding_boxes), 0)
    
    def test_identify_form_type(self):
        """Test form type identification"""
        # Test 1040 identification
        text_1040 = "Form 1040 U.S. Individual Income Tax Return"
        self.assertEqual(self.parser.identify_form_type(text_1040), '1040')
        
        # Test W2 identification
        text_w2 = "Form W-2 Wage and Tax Statement"
        self.assertEqual(self.parser.identify_form_type(text_w2), 'W2')
        
        # Test unknown form
        text_unknown = "Some random text"
        self.assertEqual(self.parser.identify_form_type(text_unknown), 'Unknown')
    
    def test_extract_structured_data(self):
        """Test structured data extraction"""
        # Create mock OCR result
        ocr_result = OCRResult(
            text="Form 1040\nName: John Doe\nSocial security number: 123-45-6789",
            confidence=0.9,
            bounding_boxes=[]
        )
        
        result = self.parser.extract_structured_data(ocr_result)
        
        self.assertEqual(result.form_type, '1040')
        self.assertIsInstance(result.extracted_fields, dict)
    
    @patch('src.ocr_parser.pdf2image.convert_from_path')
    def test_extract_text_from_pdf(self, mock_convert):
        """Test PDF text extraction"""
        # Mock PDF conversion
        mock_image = Mock()
        mock_convert.return_value = [mock_image]
        
        with patch.object(self.parser, 'extract_text_from_image') as mock_extract:
            mock_extract.return_value = OCRResult("Test text", 0.9, [])
            
            # Create a temporary PDF path
            pdf_path = os.path.join(self.temp_dir, 'test.pdf')
            with open(pdf_path, 'w') as f:
                f.write("dummy pdf content")
            
            try:
                results = self.parser.extract_text_from_pdf(pdf_path)
                self.assertIsInstance(results, list)
                self.assertEqual(len(results), 1)
            finally:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
    
    def test_process_document_unsupported_format(self):
        """Test processing unsupported file format"""
        unsupported_file = os.path.join(self.temp_dir, 'test.txt')
        with open(unsupported_file, 'w') as f:
            f.write("test content")
        
        try:
            with self.assertRaises(ValueError):
                self.parser.process_document(unsupported_file)
        finally:
            os.remove(unsupported_file)


if __name__ == '__main__':
    unittest.main()