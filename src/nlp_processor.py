"""
NLP Processor Module for Tax Form Analysis

This module provides natural language processing capabilities for
analyzing and extracting meaningful information from tax form text data.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import spacy
import numpy as np
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EntityExtraction:
    """Data class for extracted entities"""
    entity_type: str
    entity_value: str
    confidence: float
    start_pos: int
    end_pos: int


@dataclass
class ValidationResult:
    """Data class for validation results"""
    is_valid: bool
    confidence: float
    errors: List[str]
    warnings: List[str]


class NLPProcessor:
    """
    Advanced NLP processor for tax form text analysis and validation
    """
    
    def __init__(self, model_name: str = "dbmdz/bert-large-cased-finetuned-conll03-english"):
        """
        Initialize NLP Processor
        
        Args:
            model_name: Pre-trained model for named entity recognition
        """
        try:
            # Load spaCy model for general NLP tasks
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy English model not found. Please install with: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Load transformer model for enhanced NER
        try:
            self.ner_pipeline = pipeline("ner", 
                                        model=model_name, 
                                        tokenizer=model_name,
                                        aggregation_strategy="simple")
        except Exception as e:
            logger.warning(f"Could not load transformer model: {e}")
            self.ner_pipeline = None
        
        # Tax-specific patterns and validations
        self.tax_patterns = {
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'ein': r'\b\d{2}-\d{7}\b',
            'phone': r'\b\d{3}-\d{3}-\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'currency': r'\$[0-9,]+(?:\.\d{2})?',
            'percentage': r'\d+(?:\.\d+)?%',
            'date': r'\d{1,2}[/-]\d{1,2}[/-]\d{4}',
            'zip_code': r'\b\d{5}(?:-\d{4})?\b'
        }
        
        # IRS form field mappings
        self.form_field_mappings = {
            '1040': {
                'required_fields': ['name', 'ssn', 'filing_status', 'total_income'],
                'optional_fields': ['spouse_name', 'spouse_ssn', 'dependents'],
                'validation_rules': {
                    'total_income': {'min': 0, 'max': 10000000},
                    'federal_tax_withheld': {'min': 0, 'max': 5000000}
                }
            },
            'W2': {
                'required_fields': ['employee_name', 'employee_ssn', 'employer_ein', 'wages'],
                'optional_fields': ['state_wages', 'state_tax_withheld'],
                'validation_rules': {
                    'wages': {'min': 0, 'max': 5000000},
                    'federal_tax_withheld': {'min': 0, 'max': 2000000}
                }
            }
        }
        
        # Initialize TF-IDF vectorizer for text similarity
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
    
    def extract_entities(self, text: str) -> List[EntityExtraction]:
        """
        Extract named entities from text using multiple approaches
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of extracted entities
        """
        entities = []
        
        try:
            # Pattern-based extraction for tax-specific entities
            pattern_entities = self._extract_pattern_entities(text)
            entities.extend(pattern_entities)
            
            # spaCy-based entity extraction
            if self.nlp:
                spacy_entities = self._extract_spacy_entities(text)
                entities.extend(spacy_entities)
            
            # Transformer-based entity extraction
            if self.ner_pipeline:
                transformer_entities = self._extract_transformer_entities(text)
                entities.extend(transformer_entities)
            
            # Remove duplicates and merge overlapping entities
            entities = self._merge_overlapping_entities(entities)
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            return []
    
    def _extract_pattern_entities(self, text: str) -> List[EntityExtraction]:
        """Extract entities using regex patterns"""
        entities = []
        
        for entity_type, pattern in self.tax_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append(EntityExtraction(
                    entity_type=entity_type,
                    entity_value=match.group(),
                    confidence=0.95,  # High confidence for pattern matches
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        return entities
    
    def _extract_spacy_entities(self, text: str) -> List[EntityExtraction]:
        """Extract entities using spaCy NLP model"""
        entities = []
        
        doc = self.nlp(text)
        for ent in doc.ents:
            entities.append(EntityExtraction(
                entity_type=ent.label_,
                entity_value=ent.text,
                confidence=0.8,  # Medium confidence for spaCy
                start_pos=ent.start_char,
                end_pos=ent.end_char
            ))
        
        return entities
    
    def _extract_transformer_entities(self, text: str) -> List[EntityExtraction]:
        """Extract entities using transformer model"""
        entities = []
        
        try:
            results = self.ner_pipeline(text)
            for result in results:
                entities.append(EntityExtraction(
                    entity_type=result['entity_group'],
                    entity_value=result['word'],
                    confidence=result['score'],
                    start_pos=result['start'],
                    end_pos=result['end']
                ))
        except Exception as e:
            logger.warning(f"Transformer entity extraction failed: {e}")
        
        return entities
    
    def _merge_overlapping_entities(self, entities: List[EntityExtraction]) -> List[EntityExtraction]:
        """Merge overlapping entities, keeping the highest confidence"""
        if not entities:
            return entities
        
        # Sort by start position
        entities.sort(key=lambda x: x.start_pos)
        
        merged = []
        current = entities[0]
        
        for next_entity in entities[1:]:
            # Check for overlap
            if (next_entity.start_pos <= current.end_pos and 
                next_entity.end_pos >= current.start_pos):
                # Overlapping entities - keep the one with higher confidence
                if next_entity.confidence > current.confidence:
                    current = next_entity
            else:
                merged.append(current)
                current = next_entity
        
        merged.append(current)
        return merged
    
    def validate_extracted_data(self, form_type: str, extracted_data: Dict) -> ValidationResult:
        """
        Validate extracted data against form-specific rules
        
        Args:
            form_type: Type of tax form (e.g., '1040', 'W2')
            extracted_data: Dictionary of extracted field values
            
        Returns:
            ValidationResult with validation status and issues
        """
        errors = []
        warnings = []
        confidence = 1.0
        
        try:
            if form_type in self.form_field_mappings:
                form_config = self.form_field_mappings[form_type]
                
                # Check required fields
                for required_field in form_config['required_fields']:
                    if required_field not in extracted_data or not extracted_data[required_field]:
                        errors.append(f"Required field '{required_field}' is missing")
                        confidence -= 0.2
                
                # Validate field values
                if 'validation_rules' in form_config:
                    for field, rules in form_config['validation_rules'].items():
                        if field in extracted_data:
                            value = extracted_data[field]
                            
                            # Try to convert to numeric if it's a string
                            if isinstance(value, str):
                                try:
                                    # Remove currency symbols and commas
                                    cleaned_value = re.sub(r'[$,]', '', value)
                                    value = float(cleaned_value)
                                except ValueError:
                                    warnings.append(f"Could not validate numeric field '{field}': {value}")
                                    confidence -= 0.1
                                    continue
                            
                            # Apply validation rules
                            if 'min' in rules and value < rules['min']:
                                errors.append(f"Field '{field}' value {value} is below minimum {rules['min']}")
                                confidence -= 0.3
                            
                            if 'max' in rules and value > rules['max']:
                                warnings.append(f"Field '{field}' value {value} seems unusually high (max: {rules['max']})")
                                confidence -= 0.1
                
                # Additional validation checks
                confidence = self._perform_additional_validations(extracted_data, errors, warnings, confidence)
            
            is_valid = len(errors) == 0
            confidence = max(0.0, min(1.0, confidence))
            
            return ValidationResult(
                is_valid=is_valid,
                confidence=confidence,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error validating data: {str(e)}")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                errors=[f"Validation error: {str(e)}"],
                warnings=[]
            )
    
    def _perform_additional_validations(self, data: Dict, errors: List, warnings: List, confidence: float) -> float:
        """Perform additional validation checks"""
        
        # SSN validation
        if 'ssn' in data:
            ssn = data['ssn']
            if not re.match(r'^\d{3}-\d{2}-\d{4}$', ssn):
                errors.append(f"Invalid SSN format: {ssn}")
                confidence -= 0.3
            else:
                # Check for common invalid SSNs
                invalid_ssns = ['000-00-0000', '123-45-6789', '111-11-1111']
                if ssn in invalid_ssns:
                    warnings.append(f"SSN appears to be a placeholder: {ssn}")
                    confidence -= 0.2
        
        # EIN validation
        if 'ein' in data:
            ein = data['ein']
            if not re.match(r'^\d{2}-\d{7}$', ein):
                errors.append(f"Invalid EIN format: {ein}")
                confidence -= 0.3
        
        # Date validation
        date_fields = ['date_of_birth', 'hire_date', 'termination_date']
        for field in date_fields:
            if field in data:
                try:
                    date_str = data[field]
                    # Try different date formats
                    for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%Y-%m-%d']:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            # Check if date is reasonable
                            current_year = datetime.now().year
                            if parsed_date.year > current_year:
                                warnings.append(f"Future date in field '{field}': {date_str}")
                                confidence -= 0.1
                            elif parsed_date.year < 1900:
                                warnings.append(f"Very old date in field '{field}': {date_str}")
                                confidence -= 0.1
                            break
                        except ValueError:
                            continue
                    else:
                        warnings.append(f"Could not parse date in field '{field}': {date_str}")
                        confidence -= 0.1
                except Exception:
                    pass
        
        return confidence
    
    def classify_form_content(self, text: str) -> Dict[str, float]:
        """
        Classify the content type of a tax form
        
        Args:
            text: Text content to classify
            
        Returns:
            Dictionary with form types and confidence scores
        """
        form_keywords = {
            '1040': ['individual income tax return', 'filing status', 'standard deduction', 'taxable income'],
            'W2': ['wage and tax statement', 'employer', 'employee', 'federal income tax withheld'],
            '1099': ['miscellaneous income', 'nonemployee compensation', 'payer', 'recipient'],
            'Schedule C': ['profit or loss', 'business income', 'business expenses', 'net profit'],
            '941': ['quarterly return', 'employer', 'payroll tax', 'employment tax'],
            '1120': ['corporation income tax', 'corporate tax', 'c corporation', 'net income']
        }
        
        text_lower = text.lower()
        scores = {}
        
        for form_type, keywords in form_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            
            # Normalize score
            scores[form_type] = score / len(keywords)
        
        return scores
    
    def extract_financial_amounts(self, text: str) -> List[Dict]:
        """
        Extract and classify financial amounts from text
        
        Args:
            text: Text to analyze
            
        Returns:
            List of financial amounts with context
        """
        amounts = []
        
        # Pattern for currency amounts
        currency_pattern = r'\$([0-9,]+(?:\.\d{2})?)'
        matches = re.finditer(currency_pattern, text)
        
        for match in matches:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                
                # Extract context around the amount
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                amounts.append({
                    'amount': amount,
                    'formatted_amount': f"${amount:,.2f}",
                    'context': context,
                    'position': match.start()
                })
            except ValueError:
                continue
        
        return amounts
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text documents
        
        Args:
            text1: First text document
            text2: Second text document
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            # Fit and transform texts
            tfidf_matrix = self.vectorizer.fit_transform([text1, text2])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return similarity
            
        except Exception as e:
            logger.error(f"Error calculating text similarity: {str(e)}")
            return 0.0
    
    def process_tax_form_text(self, text: str, form_type: str = None) -> Dict[str, Any]:
        """
        Main method to process tax form text with comprehensive analysis
        
        Args:
            text: Text content to process
            form_type: Optional form type hint
            
        Returns:
            Dictionary with all analysis results
        """
        try:
            # Extract entities
            entities = self.extract_entities(text)
            
            # Classify form content if type not provided
            if not form_type:
                form_scores = self.classify_form_content(text)
                form_type = max(form_scores, key=form_scores.get) if form_scores else 'Unknown'
            
            # Extract financial amounts
            financial_amounts = self.extract_financial_amounts(text)
            
            # Create structured data from entities
            structured_data = {}
            for entity in entities:
                if entity.entity_type not in structured_data:
                    structured_data[entity.entity_type] = []
                structured_data[entity.entity_type].append(entity.entity_value)
            
            # Validate the extracted data
            validation_result = self.validate_extracted_data(form_type, structured_data)
            
            return {
                'form_type': form_type,
                'entities': entities,
                'structured_data': structured_data,
                'financial_amounts': financial_amounts,
                'validation': validation_result,
                'processing_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing tax form text: {str(e)}")
            raise


if __name__ == "__main__":
    # Example usage
    processor = NLPProcessor()
    
    sample_text = """
    Form 1040 - U.S. Individual Income Tax Return
    
    Name: John Doe
    Social Security Number: 123-45-6789
    Filing Status: Married Filing Jointly
    
    Income:
    Wages: $85,000
    Interest: $1,200
    Total Income: $86,200
    
    Deductions:
    Standard Deduction: $27,700
    Taxable Income: $58,500
    """
    
    try:
        result = processor.process_tax_form_text(sample_text)
        print("Processing Results:")
        print(f"Form Type: {result['form_type']}")
        print(f"Validation: Valid={result['validation'].is_valid}, Confidence={result['validation'].confidence:.2f}")
        print(f"Entities Found: {len(result['entities'])}")
        print(f"Financial Amounts: {len(result['financial_amounts'])}")
    except Exception as e:
        print(f"Error: {e}")