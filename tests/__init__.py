"""
Test initialization module for the tests package
"""

import sys
import os

# Add the src directory to the Python path for testing
src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Test configuration constants
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
TEST_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_output')

# Ensure test directories exist
os.makedirs(TEST_DATA_DIR, exist_ok=True)
os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)