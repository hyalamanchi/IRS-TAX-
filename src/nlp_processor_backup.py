"""
NLP Processor Module for IRS Tax Forms

This module provides NLP functionality for extracting structured data from tax forms
using spaCy and regex patterns.
"""

import spacy
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NLPProcessor:
    """
    NLP processor for extracting structured data from tax form text using spaCy
    """
    
    def __init__(self):
        """Initialize NLP Processor with spaCy model"""
        try:
            # Load spaCy English model
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("Successfully loaded spaCy en_core_web_sm model")
        except OSError:
            logger.error("spaCy en_core_web_sm model not found. Install with: python -m spacy download en_core_web_sm")
            raise
    
    def extract_fields(self, raw_text):
        """
        Extract specific fields from raw text using regex patterns
        
        Args:
            raw_text (str): Raw text from tax form
            
        Returns:
            dict: Dictionary with extracted fields
        """
        extracted_data = {}
        
        # Define regex patterns for common tax form fields
        patterns = {
            'name': r'Name[:\s]+([A-Za-z\s]+?)(?:\n|SSN|Social Security)',
            'ssn': r'(?:SSN|Social Security Number)[:\s]*(\d{3}-?\d{2}-?\d{4})',
            'wages': r'(?:Wages|Income)[:\s]*\$?([0-9,]+(?:\.\d{2})?)',
            'filing_status': r'Filing Status[:\s]*(Single|Married Filing Jointly|Married Filing Separately|Head of Household|Qualifying Widow)',
            'address': r'Address[:\s]+([A-Za-z0-9\s,]+?)(?:\n|City)',
            'city': r'City[:\s]+([A-Za-z\s]+)',
            'state': r'State[:\s]+([A-Z]{2})',
            'zip_code': r'(?:ZIP|Zip Code)[:\s]*(\d{5}(?:-\d{4})?)',
            'tax_year': r'(?:Tax Year|Year)[:\s]*(\d{4})',
            'federal_tax_withheld': r'Federal Tax Withheld[:\s]*\$?([0-9,]+(?:\.\d{2})?)'
        }
        
        for field_name, pattern in patterns.items():
            match = re.search(pattern, raw_text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                # Clean up extracted value
                if field_name in ['wages', 'federal_tax_withheld']:
                    # Remove commas and convert to float for monetary values
                    value = value.replace(',', '')
                    try:
                        extracted_data[field_name] = float(value)
                    except ValueError:
                        extracted_data[field_name] = value
                else:
                    extracted_data[field_name] = value
                
                logger.info(f"Extracted {field_name}: {value}")
        
        return extracted_data
    
    def process_with_spacy(self, text):
        """
        Process text with spaCy for additional NLP analysis
        
        Args:
            text (str): Text to process
            
        Returns:
            dict: Dictionary with spaCy analysis results
        """
        try:
            # Process text with spaCy
            doc = self.nlp(text)
            
            # Extract entities
            entities = []
            for ent in doc.ents:
                entities.append({
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char
                })
            
            # Extract numbers (potential amounts)
            numbers = []
            for token in doc:
                if token.like_num:
                    numbers.append({
                        'text': token.text,
                        'position': token.idx
                    })
            
            # Extract money amounts using spaCy's MONEY entity
            money_entities = [ent.text for ent in doc.ents if ent.label_ == "MONEY"]
            
            # Extract person names using spaCy's PERSON entity
            person_names = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
            
            return {
                'entities': entities,
                'numbers': numbers,
                'money_entities': money_entities,
                'person_names': person_names
            }
            
        except Exception as e:
            logger.error(f"Error processing text with spaCy: {str(e)}")
            return {}
    
    def validate_extracted_data(self, extracted_data):
        """
        Validate extracted data for consistency and format
        
        Args:
            extracted_data (dict): Extracted data to validate
            
        Returns:
            dict: Validated data with status
        """
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate SSN format
        if 'ssn' in extracted_data:
            ssn = extracted_data['ssn']
            if not re.match(r'^\d{3}-?\d{2}-?\d{4}$', ssn):
                validation_results['errors'].append(f"Invalid SSN format: {ssn}")
                validation_results['valid'] = False
        
        # Validate monetary amounts
        for field in ['wages', 'federal_tax_withheld']:
            if field in extracted_data:
                try:
                    amount = float(str(extracted_data[field]).replace(',', ''))
                    if amount < 0:
                        validation_results['warnings'].append(f"Negative amount for {field}: {amount}")
                except (ValueError, TypeError):
                    validation_results['errors'].append(f"Invalid monetary value for {field}: {extracted_data[field]}")
                    validation_results['valid'] = False
        
        # Validate tax year
        if 'tax_year' in extracted_data:
            year = extracted_data['tax_year']
            try:
                year_int = int(year)
                if year_int < 1900 or year_int > 2030:
                    validation_results['warnings'].append(f"Unusual tax year: {year}")
            except ValueError:
                validation_results['errors'].append(f"Invalid tax year format: {year}")
                validation_results['valid'] = False
        
        return validation_results


if __name__ == "__main__":
    # Example usage
    processor = NLPProcessor()
    
    # Sample tax form text
    sample_text = """
    U.S. Individual Income Tax Return Form 1040
    Name: John Smith
    SSN: 123-45-6789
    Filing Status: Single
    Wages: $45,000.00
    Federal Tax Withheld: $5,400.00
    Tax Year: 2023
    """
    
    try:
        # Extract fields
        extracted = processor.extract_fields(sample_text)
        print("Extracted Fields:")
        for field, value in extracted.items():
            print(f"  {field}: {value}")
        
        # Process with spaCy
        spacy_results = processor.process_with_spacy(sample_text)
        print("\nspaCy Analysis:")
        print(f"  Entities: {spacy_results.get('entities', [])}")
        print(f"  Money Entities: {spacy_results.get('money_entities', [])}")
        print(f"  Person Names: {spacy_results.get('person_names', [])}")
        
        # Validate data
        validation = processor.validate_extracted_data(extracted)
        print(f"\nValidation: {'PASSED' if validation['valid'] else 'FAILED'}")
        if validation['errors']:
            print(f"  Errors: {validation['errors']}")
        if validation['warnings']:
            print(f"  Warnings: {validation['warnings']}")
            
    except Exception as e:
        print(f"Error: {e}")