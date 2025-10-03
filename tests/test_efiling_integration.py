"""
Test module for E-Filing Integration functionality
"""

import unittest
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.efiling_integration import (
    EFilingIntegration, 
    EFilingConfiguration, 
    EFilingSubmission,
    IRSMeFIntegration,
    SecurityHandler
)


class TestSecurityHandler(unittest.TestCase):
    """Test cases for Security Handler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.security = SecurityHandler("test-encryption-key-32-bytes-long!")
    
    def test_encrypt_decrypt_data(self):
        """Test data encryption and decryption"""
        original_data = "sensitive tax information"
        
        # Encrypt data
        encrypted_data = self.security.encrypt_data(original_data)
        self.assertNotEqual(encrypted_data, original_data)
        
        # Decrypt data
        decrypted_data = self.security.decrypt_data(encrypted_data)
        self.assertEqual(decrypted_data, original_data)
    
    def test_generate_digital_signature(self):
        """Test digital signature generation"""
        data = "tax form data"
        secret_key = "secret123"
        
        signature = self.security.generate_digital_signature(data, secret_key)
        
        self.assertIsInstance(signature, str)
        self.assertGreater(len(signature), 0)
    
    def test_verify_digital_signature(self):
        """Test digital signature verification"""
        data = "tax form data"
        secret_key = "secret123"
        
        signature = self.security.generate_digital_signature(data, secret_key)
        
        # Valid signature should verify
        self.assertTrue(self.security.verify_digital_signature(data, signature, secret_key))
        
        # Invalid signature should not verify
        self.assertFalse(self.security.verify_digital_signature(data, "invalid_signature", secret_key))
        
        # Wrong secret key should not verify
        self.assertFalse(self.security.verify_digital_signature(data, signature, "wrong_key"))


class TestIRSMeFIntegration(unittest.TestCase):
    """Test cases for IRS MeF Integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = EFilingConfiguration(
            service_provider='irs_mef',
            environment='test',
            api_endpoint='https://test.irs.gov/efile',
            username='test_user',
            password='test_password',
            encryption_key='test-key'
        )
        self.mef_integration = IRSMeFIntegration(self.config)
    
    def test_initialization(self):
        """Test IRS MeF integration initialization"""
        self.assertIsInstance(self.mef_integration, IRSMeFIntegration)
        self.assertEqual(self.mef_integration.config.service_provider, 'irs_mef')
    
    def test_get_filing_status_code(self):
        """Test filing status code conversion"""
        self.assertEqual(self.mef_integration._get_filing_status_code('single'), '1')
        self.assertEqual(self.mef_integration._get_filing_status_code('married_filing_jointly'), '2')
        self.assertEqual(self.mef_integration._get_filing_status_code('married_filing_separately'), '3')
        self.assertEqual(self.mef_integration._get_filing_status_code('head_of_household'), '4')
        self.assertEqual(self.mef_integration._get_filing_status_code('qualifying_widow'), '5')
        
        # Test unknown status defaults to single
        self.assertEqual(self.mef_integration._get_filing_status_code('unknown'), '1')
    
    def test_create_1040_return(self):
        """Test Form 1040 return XML creation"""
        submission = EFilingSubmission(
            submission_id='TEST_SUB_001',
            tax_year=2023,
            submission_data={
                'form_type': '1040',
                'name': 'John Doe',
                'ssn': '123-45-6789',
                'filing_status': 'single',
                'total_income': '50000',
                'standard_deduction': '13850',
                'taxable_income': '36150'
            }
        )
        
        return_element = self.mef_integration._create_1040_return(submission)
        
        self.assertEqual(return_element.tag, 'IndividualReturn')
        self.assertEqual(return_element.get('returnVersion'), '2023v1.0')
    
    def test_create_mef_transmission(self):
        """Test MeF transmission XML creation"""
        submission = EFilingSubmission(
            submission_id='TEST_SUB_001',
            tax_year=2023,
            submission_data={
                'form_type': '1040',
                'name': 'John Doe',
                'ssn': '123-45-6789',
                'filing_status': 'single',
                'total_income': '50000'
            }
        )
        
        transmission_xml = self.mef_integration.create_mef_transmission(submission)
        
        self.assertIn('Transmission', transmission_xml)
        self.assertIn('TransmissionHeader', transmission_xml)
        self.assertIn('ReturnData', transmission_xml)
    
    def test_create_soap_envelope(self):
        """Test SOAP envelope creation"""
        transmission_xml = "<Transmission>test</Transmission>"
        
        soap_envelope = self.mef_integration._create_soap_envelope(transmission_xml)
        
        self.assertIn('soap:Envelope', soap_envelope)
        self.assertIn('soap:Header', soap_envelope)
        self.assertIn('soap:Body', soap_envelope)
        self.assertIn(self.config.username, soap_envelope)
    
    def test_parse_mef_response_success(self):
        """Test parsing successful MeF response"""
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                       xmlns:efile="http://www.irs.gov/efile">
            <soap:Body>
                <efile:SubmissionStatus>accepted</efile:SubmissionStatus>
                <efile:AcknowledgmentId>ACK123456789</efile:AcknowledgmentId>
            </soap:Body>
        </soap:Envelope>"""
        
        result = self.mef_integration._parse_mef_response(response_xml)
        
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(result['acknowledgment_id'], 'ACK123456789')
        self.assertEqual(len(result['errors']), 0)
    
    def test_parse_mef_response_with_errors(self):
        """Test parsing MeF response with errors"""
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                       xmlns:efile="http://www.irs.gov/efile">
            <soap:Body>
                <efile:SubmissionStatus>rejected</efile:SubmissionStatus>
                <efile:Error>
                    <efile:ErrorCode>1001</efile:ErrorCode>
                    <efile:ErrorText>Invalid SSN format</efile:ErrorText>
                </efile:Error>
            </soap:Body>
        </soap:Envelope>"""
        
        result = self.mef_integration._parse_mef_response(response_xml)
        
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(len(result['errors']), 1)
        self.assertIn('1001: Invalid SSN format', result['errors'])
    
    @patch('requests.Session.post')
    def test_submit_transmission_success(self, mock_post):
        """Test successful transmission submission"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <soap:Envelope xmlns:efile="http://www.irs.gov/efile">
            <soap:Body>
                <efile:SubmissionStatus>accepted</efile:SubmissionStatus>
                <efile:AcknowledgmentId>ACK123456789</efile:AcknowledgmentId>
            </soap:Body>
        </soap:Envelope>"""
        mock_post.return_value = mock_response
        
        submission = EFilingSubmission(
            submission_id='TEST_SUB_001',
            submission_data={'form_type': '1040'}
        )
        
        transmission_xml = "<Transmission>test</Transmission>"
        result = self.mef_integration.submit_transmission(transmission_xml, submission)
        
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(result['acknowledgment_id'], 'ACK123456789')
        self.assertEqual(submission.submission_status, 'transmitted')
    
    @patch('requests.Session.post')
    def test_submit_transmission_failure(self, mock_post):
        """Test transmission submission failure"""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        submission = EFilingSubmission(
            submission_id='TEST_SUB_001',
            submission_data={'form_type': '1040'}
        )
        
        transmission_xml = "<Transmission>test</Transmission>"
        result = self.mef_integration.submit_transmission(transmission_xml, submission)
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_code'], 500)


class TestEFilingIntegration(unittest.TestCase):
    """Test cases for E-Filing Integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = EFilingConfiguration(
            service_provider='irs_mef',
            environment='test',
            api_endpoint='https://test.irs.gov/efile',
            username='test_user',
            password='test_password',
            encryption_key='test-encryption-key-32-bytes!'
        )
        
        with patch('src.efiling_integration.IRSMeFIntegration'):
            self.efiling = EFilingIntegration(self.config)
    
    def test_initialization(self):
        """Test E-Filing integration initialization"""
        self.assertIsInstance(self.efiling, EFilingIntegration)
        self.assertEqual(self.efiling.config.service_provider, 'irs_mef')
    
    def test_initialization_unsupported_provider(self):
        """Test initialization with unsupported provider"""
        config = EFilingConfiguration(
            service_provider='unsupported_provider',
            environment='test',
            api_endpoint='https://test.example.com',
            username='test',
            password='test'
        )
        
        with self.assertRaises(ValueError):
            EFilingIntegration(config)
    
    def test_prepare_submission(self):
        """Test submission preparation"""
        form_data = {
            'form_id': 'FORM_001',
            'form_type': '1040',
            'name': 'John Doe',
            'ssn': '123-45-6789',
            'filing_status': 'single',
            'total_income': '50000'
        }
        
        submission = self.efiling.prepare_submission(form_data, '1040', 2023)
        
        self.assertIsInstance(submission, EFilingSubmission)
        self.assertEqual(submission.form_id, 'FORM_001')
        self.assertEqual(submission.tax_year, 2023)
        self.assertIn(submission.submission_id, self.efiling.submissions)
    
    def test_validate_submission_valid(self):
        """Test submission validation with valid data"""
        submission = EFilingSubmission(
            submission_data={
                'form_type': '1040',
                'name': 'John Doe',
                'ssn': '123-45-6789',
                'filing_status': 'single',
                'total_income': '50000'
            },
            tax_year=2023
        )
        
        result = self.efiling._validate_submission(submission)
        
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
    
    def test_validate_submission_missing_fields(self):
        """Test submission validation with missing required fields"""
        submission = EFilingSubmission(
            submission_data={
                'form_type': '1040',
                'name': 'John Doe'
                # Missing ssn, filing_status, total_income
            },
            tax_year=2023
        )
        
        result = self.efiling._validate_submission(submission)
        
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_validate_submission_invalid_ssn(self):
        """Test submission validation with invalid SSN"""
        submission = EFilingSubmission(
            submission_data={
                'form_type': '1040',
                'name': 'John Doe',
                'ssn': 'invalid-ssn',
                'filing_status': 'single',
                'total_income': '50000'
            },
            tax_year=2023
        )
        
        result = self.efiling._validate_submission(submission)
        
        self.assertFalse(result['is_valid'])
        self.assertTrue(any('Invalid SSN format' in error for error in result['errors']))
    
    def test_validate_submission_future_tax_year(self):
        """Test submission validation with future tax year"""
        current_year = datetime.now().year
        future_year = current_year + 1
        
        submission = EFilingSubmission(
            submission_data={
                'form_type': '1040',
                'name': 'John Doe',
                'ssn': '123-45-6789',
                'filing_status': 'single',
                'total_income': '50000'
            },
            tax_year=future_year
        )
        
        result = self.efiling._validate_submission(submission)
        
        self.assertFalse(result['is_valid'])
        self.assertTrue(any(f'Invalid tax year: {future_year}' in error for error in result['errors']))
    
    def test_validate_ssn_valid(self):
        """Test SSN validation with valid SSN"""
        self.assertTrue(self.efiling._validate_ssn('123-45-6789'))
    
    def test_validate_ssn_invalid(self):
        """Test SSN validation with invalid SSN"""
        self.assertFalse(self.efiling._validate_ssn('123-456-789'))
        self.assertFalse(self.efiling._validate_ssn('123456789'))
        self.assertFalse(self.efiling._validate_ssn('invalid'))
    
    def test_generate_submission_id(self):
        """Test submission ID generation"""
        id1 = self.efiling._generate_submission_id()
        id2 = self.efiling._generate_submission_id()
        
        self.assertTrue(id1.startswith('SUB_'))
        self.assertTrue(id2.startswith('SUB_'))
        self.assertNotEqual(id1, id2)
    
    def test_check_submission_status_found(self):
        """Test checking status of existing submission"""
        # Create a mock submission
        submission = EFilingSubmission(
            submission_id='TEST_SUB_001',
            submission_status='transmitted',
            acknowledgment_id='ACK123456789'
        )
        
        self.efiling.submissions['TEST_SUB_001'] = submission
        
        with patch.object(self.efiling.provider, 'check_acknowledgment_status') as mock_check:
            mock_check.return_value = {'status': 'accepted'}
            
            result = self.efiling.check_submission_status('TEST_SUB_001')
            
            self.assertTrue(result['found'])
            self.assertEqual(result['submission_id'], 'TEST_SUB_001')
            self.assertEqual(result['status'], 'accepted')
    
    def test_check_submission_status_not_found(self):
        """Test checking status of non-existent submission"""
        result = self.efiling.check_submission_status('NONEXISTENT_ID')
        
        self.assertFalse(result['found'])
        self.assertIn('error', result)
    
    def test_get_submission_history_no_filters(self):
        """Test getting submission history without filters"""
        # Add test submissions
        submissions = [
            EFilingSubmission(
                submission_id='SUB_001',
                submission_data={'form_type': '1040'},
                tax_year=2023,
                submission_status='transmitted',
                created_date=datetime(2024, 1, 1)
            ),
            EFilingSubmission(
                submission_id='SUB_002',
                submission_data={'form_type': 'W2'},
                tax_year=2023,
                submission_status='pending',
                created_date=datetime(2024, 1, 2)
            )
        ]
        
        for sub in submissions:
            self.efiling.submissions[sub.submission_id] = sub
        
        history = self.efiling.get_submission_history()
        
        self.assertEqual(len(history), 2)
        # Should be sorted by date (newest first)
        self.assertEqual(history[0]['submission_id'], 'SUB_002')
        self.assertEqual(history[1]['submission_id'], 'SUB_001')
    
    def test_get_submission_history_with_filters(self):
        """Test getting submission history with filters"""
        # Add test submissions
        submissions = [
            EFilingSubmission(
                submission_id='SUB_001',
                submission_data={'form_type': '1040'},
                tax_year=2023,
                submission_status='transmitted'
            ),
            EFilingSubmission(
                submission_id='SUB_002',
                submission_data={'form_type': '1040'},
                tax_year=2023,
                submission_status='pending'
            ),
            EFilingSubmission(
                submission_id='SUB_003',
                submission_data={'form_type': 'W2'},
                tax_year=2023,
                submission_status='transmitted'
            )
        ]
        
        for sub in submissions:
            self.efiling.submissions[sub.submission_id] = sub
        
        # Filter by status
        filtered_history = self.efiling.get_submission_history({'status': 'transmitted'})
        self.assertEqual(len(filtered_history), 2)
        
        # Filter by form type
        filtered_history = self.efiling.get_submission_history({'form_type': '1040'})
        self.assertEqual(len(filtered_history), 2)
        
        # Filter by multiple criteria
        filtered_history = self.efiling.get_submission_history({
            'form_type': '1040',
            'status': 'pending'
        })
        self.assertEqual(len(filtered_history), 1)
        self.assertEqual(filtered_history[0]['submission_id'], 'SUB_002')


if __name__ == '__main__':
    unittest.main()