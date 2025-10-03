"""
OCR Parser Module for IRS Tax Forms

This module provides OCR (Optical Character Recognition) capabilities
for extracting text and structured data from tax form images and PDFs.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
import pytesseract
from PIL import Image
import pdf2image
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Data class for OCR extraction results"""
    text: str
    confidence: float
    bounding_boxes: List[Dict]
    form_type: Optional[str] = None
    extracted_fields: Optional[Dict] = None


class OCRParser:
    """
    Advanced OCR parser specifically designed for IRS tax forms
    """
    
    def __init__(self, tesseract_path: str = None):
        """
        Initialize OCR Parser
        
        Args:
            tesseract_path: Path to Tesseract executable (if not in PATH)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Form-specific patterns for field extraction
        self.form_patterns = {
            '1040': {
                'name_pattern': r'Name\s*([A-Za-z\s]+)',
                'ssn_pattern': r'Social security number\s*(\d{3}-\d{2}-\d{4})',
                'income_pattern': r'Total income\s*\$?([0-9,]+)',
                'filing_status_pattern': r'Filing Status.*?(Single|Married filing jointly|Married filing separately|Head of household|Qualifying widow)'
            },
            'W2': {
                'employee_name_pattern': r'Employee.*?([A-Za-z\s]+)',
                'employer_ein_pattern': r'Employer.*?(\d{2}-\d{7})',
                'wages_pattern': r'Wages.*?\$?([0-9,]+)',
                'federal_tax_pattern': r'Federal income tax withheld.*?\$?([0-9,]+)'
            },
            '1099': {
                'recipient_pattern': r'RECIPIENT.*?([A-Za-z\s]+)',
                'payer_pattern': r'PAYER.*?([A-Za-z\s]+)',
                'amount_pattern': r'Nonemployee compensation.*?\$?([0-9,]+)'
            }
        }
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for better OCR results
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Preprocessed image as numpy array
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply noise reduction
            denoised = cv2.medianBlur(gray, 3)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Deskew if needed (basic implementation)
            coords = np.column_stack(np.where(thresh > 0))
            angle = cv2.minAreaRect(coords)[-1]
            
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
                
            if abs(angle) > 0.5:  # Only correct if angle is significant
                (h, w) = thresh.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                thresh = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            
            return thresh
            
        except Exception as e:
            logger.error(f"Error preprocessing image {image_path}: {str(e)}")
            raise
    
    def extract_text_from_image(self, image_path: str) -> OCRResult:
        """
        Extract text from image using OCR
        
        Args:
            image_path: Path to the image file
            
        Returns:
            OCRResult object with extracted text and metadata
        """
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image_path)
            
            # Configure Tesseract for better accuracy
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,()[]{}/$%-'
            
            # Extract text with confidence scores
            data = pytesseract.image_to_data(processed_image, config=custom_config, output_type=pytesseract.Output.DICT)
            
            # Calculate overall confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Extract bounding boxes for words with high confidence
            bounding_boxes = []
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 60:  # Only include high-confidence words
                    bounding_boxes.append({
                        'text': data['text'][i],
                        'confidence': data['conf'][i],
                        'x': data['left'][i],
                        'y': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i]
                    })
            
            # Get full text
            full_text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            return OCRResult(
                text=full_text,
                confidence=avg_confidence / 100.0,
                bounding_boxes=bounding_boxes
            )
            
        except Exception as e:
            logger.error(f"Error extracting text from {image_path}: {str(e)}")
            raise
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[OCRResult]:
        """
        Extract text from PDF document
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of OCRResult objects, one for each page
        """
        try:
            # Convert PDF to images
            pages = pdf2image.convert_from_path(pdf_path, dpi=300)
            results = []
            
            for i, page in enumerate(pages):
                # Save page as temporary image
                temp_image_path = f"temp_page_{i}.png"
                page.save(temp_image_path, 'PNG')
                
                try:
                    # Extract text from page
                    result = self.extract_text_from_image(temp_image_path)
                    results.append(result)
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_image_path):
                        os.remove(temp_image_path)
            
            return results
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
            raise
    
    def identify_form_type(self, text: str) -> str:
        """
        Identify the type of tax form based on extracted text
        
        Args:
            text: Extracted text from the form
            
        Returns:
            Identified form type (e.g., '1040', 'W2', '1099')
        """
        text_upper = text.upper()
        
        # Form identification patterns
        if 'FORM 1040' in text_upper or 'U.S. INDIVIDUAL INCOME TAX RETURN' in text_upper:
            return '1040'
        elif 'FORM W-2' in text_upper or 'WAGE AND TAX STATEMENT' in text_upper:
            return 'W2'
        elif 'FORM 1099' in text_upper or 'MISCELLANEOUS INCOME' in text_upper:
            return '1099'
        elif 'SCHEDULE C' in text_upper or 'PROFIT OR LOSS FROM BUSINESS' in text_upper:
            return 'Schedule C'
        elif 'FORM 941' in text_upper or 'QUARTERLY FEDERAL TAX RETURN' in text_upper:
            return '941'
        elif 'FORM 1120' in text_upper or 'CORPORATION INCOME TAX RETURN' in text_upper:
            return '1120'
        else:
            return 'Unknown'
    
    def extract_structured_data(self, ocr_result: OCRResult) -> OCRResult:
        """
        Extract structured data from OCR result based on form type
        
        Args:
            ocr_result: OCR result to process
            
        Returns:
            OCRResult with extracted structured data
        """
        # Identify form type
        form_type = self.identify_form_type(ocr_result.text)
        ocr_result.form_type = form_type
        
        if form_type in self.form_patterns:
            extracted_fields = {}
            patterns = self.form_patterns[form_type]
            
            for field_name, pattern in patterns.items():
                import re
                match = re.search(pattern, ocr_result.text, re.IGNORECASE)
                if match:
                    extracted_fields[field_name.replace('_pattern', '')] = match.group(1).strip()
            
            ocr_result.extracted_fields = extracted_fields
        
        return ocr_result
    
    def process_document(self, file_path: str) -> List[OCRResult]:
        """
        Main method to process a document (image or PDF)
        
        Args:
            file_path: Path to the document
            
        Returns:
            List of OCRResult objects with extracted and structured data
        """
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension == '.pdf':
                results = self.extract_text_from_pdf(file_path)
            elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                results = [self.extract_text_from_image(file_path)]
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            # Extract structured data from each page
            processed_results = []
            for result in results:
                processed_result = self.extract_structured_data(result)
                processed_results.append(processed_result)
            
            logger.info(f"Successfully processed {file_path}")
            return processed_results
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise


if __name__ == "__main__":
    # Example usage
    parser = OCRParser()
    
    # Test with a sample document
    try:
        results = parser.process_document("sample_form.pdf")
        for i, result in enumerate(results):
            print(f"Page {i+1}:")
            print(f"Form Type: {result.form_type}")
            print(f"Confidence: {result.confidence:.2f}")
            print(f"Extracted Fields: {result.extracted_fields}")
            print("-" * 50)
    except Exception as e:
        print(f"Error: {e}")