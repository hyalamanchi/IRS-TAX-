"""
OCR Parser Module for IRS Tax Forms

This module provides OCR functionality for extracting text from tax forms,
reading from CSV files and processing PDF documents.
"""

import pandas as pd
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OCRParser:
    """
    OCR parser for processing tax forms from CSV files and PDF documents
    """
    
    def __init__(self):
        """Initialize OCR Parser"""
        pass
    
    def read_csv(self, data_path):
        """
        Read CSV file and return list of dicts with form_id and raw_text
        
        Args:
            data_path (str): Path to CSV file
            
        Returns:
            list: List of dictionaries with form_id and raw_text
            
        Raises:
            FileNotFoundError: If CSV file is not found
        """
        try:
            # Read CSV file using pandas
            df = pd.read_csv(data_path)
            
            # Convert to list of dictionaries
            forms_data = []
            for _, row in df.iterrows():
                forms_data.append({
                    'form_id': row['form_id'],
                    'raw_text': row['raw_text']
                })
            
            logger.info(f"Successfully read {len(forms_data)} forms from {data_path}")
            return forms_data
            
        except FileNotFoundError:
            logger.error(f"CSV file not found: {data_path}")
            raise FileNotFoundError(f"CSV file not found: {data_path}")
        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}")
            raise
    
    def extract_from_pdf(self, pdf_path):
        """
        Extract text from PDF file using OCR
        
        Args:
            pdf_path (str): Path to PDF file
            
        Returns:
            str: Extracted raw text from all pages
            
        Raises:
            FileNotFoundError: If PDF file is not found
        """
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            # Convert PDF pages to images
            pages = convert_from_path(pdf_path, dpi=300)
            
            # Extract text from each page
            all_text = []
            for i, page in enumerate(pages):
                # Use pytesseract to extract text from image
                text = pytesseract.image_to_string(page)
                all_text.append(text.strip())
                logger.info(f"Extracted text from page {i+1}")
            
            # Combine all pages
            raw_text = '\n\n'.join(all_text)
            logger.info(f"Successfully extracted text from {len(pages)} pages")
            
            return raw_text
            
        except FileNotFoundError:
            logger.error(f"PDF file not found: {pdf_path}")
            raise
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise


if __name__ == "__main__":
    # Example usage
    parser = OCRParser()
    
    try:
        # Test CSV reading
        forms = parser.read_csv('data/tax_forms.csv')
        print(f"Read {len(forms)} forms from CSV")
        
        # Print first form
        if forms:
            print(f"First form ID: {forms[0]['form_id']}")
            print(f"Raw text preview: {forms[0]['raw_text'][:100]}...")
            
    except Exception as e:
        print(f"Error: {e}")