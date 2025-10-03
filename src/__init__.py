"""
IRS Tax Form Parser Package

A comprehensive Python package for parsing and processing IRS tax forms
using OCR, NLP, and database integration capabilities.
"""

__version__ = "1.0.0"
__author__ = "Tax Form Parser Team"
__email__ = "contact@taxformparser.com"

from .ocr_parser import OCRParser
from .nlp_processor import NLPProcessor
from .db_handler import DatabaseHandler
from .efiling_integration import EFilingIntegration

__all__ = [
    "OCRParser",
    "NLPProcessor", 
    "DatabaseHandler",
    "EFilingIntegration"
]