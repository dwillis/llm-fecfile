#!/usr/bin/env python3
"""
Basic tests for the llm-fecfile plugin

Run this after installing the plugin to verify it works correctly.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add the current directory to Python path so we can import the module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import llm_fecfile
    from llm_fecfile import fec_fragment_loader
except ImportError as e:
    print(f"Error importing llm_fecfile: {e}")
    print("Make sure llm_fecfile.py is in the same directory as this test file")
    sys.exit(1)

class TestFecFragmentLoader(unittest.TestCase):
    """Test the FEC fragment loader functionality"""
    
    def test_filing_id_validation(self):
        """Test filing ID validation"""
        # Valid filing ID
        self.assertTrue(True)  # Basic test that imports work
        
        # Test invalid filing IDs
        with self.assertRaises(ValueError):
            fec_fragment_loader("invalid")
        
        with self.assertRaises(ValueError):
            fec_fragment_loader("-123")
        
        with self.assertRaises(ValueError):
            fec_fragment_loader("0")
    
    @patch('fecfile.from_http')
    def test_fragment_creation(self, mock_from_http):
        """Test that fragments are created correctly"""
        # Mock the fecfile response
        mock_filing_data = {
            'filing': {
                'committee_name': 'Test Committee',
                'form_type': 'F3',
                'fec_committee_id_number': 'C00123456',
                'col_a_total_receipts': 10000.0,
                'col_a_total_disbursements': 5000.0,
                'col_a_cash_on_hand_close_of_period': 5000.0,
                'coverage_from_date': '2023-01-01',
                'coverage_through_date': '2023-03-31',
                'amendment_indicator': ''
            },
            'itemizations': {
                'Schedule A': [
                    {
                        'contributor_organization_name': 'Test Corp',
                        'contribution_amount': 1000.0,
                        'contributor_city': 'New York',
                        'contributor_state': 'NY',
                        'contribution_date': '2023-02-15'
                    }
                ],
                'Schedule B': [
                    {
                        'payee_organization_name': 'Ad Agency',
                        'expenditure_amount': 2000.0,
                        'expenditure_purpose_descrip': 'Advertising',
                        'expenditure_date': '2023-02-20'
                    }
                ]
            }
        }
        mock_from_http.return_value = mock_filing_data
        
        # Test fragment creation
        fragment = fec_fragment_loader("1234567")
        
        # Verify fragment properties
        self.assertEqual(fragment.source, "fec:1234567")
        
        # Try to find the correct way to access content
        fragment_content = self._get_fragment_content(fragment)
        self.assertIsInstance(fragment_content, str)
        self.assertIn("RESPONSE STYLE INSTRUCTIONS", fragment_content)
        self.assertIn("FEC FILING ANALYSIS INSTRUCTIONS", fragment_content)
        self.assertIn("RAW FILING DATA", fragment_content)
        
        # Verify JSON data is included
        self.assertIn('"committee_name": "Test Committee"', fragment_content)
        self.assertIn('"form_type": "F3"', fragment_content)
    
    def _get_fragment_content(self, fragment):
        """Helper method to get fragment content regardless of attribute name"""
        # The Fragment class is a string subclass - the fragment itself IS the content
        if isinstance(fragment, str):
            return fragment
        
        # Try different possible attributes (fallback)
        for attr in ['text', 'content', 'data', 'value', 'body']:
            if hasattr(fragment, attr):
                content = getattr(fragment, attr)
                if isinstance(content, str):
                    return content
        
        # Try converting to string
        try:
            content = str(fragment)
            if len(content) > 100:  # Likely to be the actual content
                return content
        except:
            pass
            
        # If all else fails, raise an error with debug info
        raise AttributeError(f"Could not find content in Fragment. Type: {type(fragment)}, Available attributes: {dir(fragment)}")
    
    @patch('fecfile.from_http')
    def test_f1_form_type_instructions(self, mock_from_http):
        """Test that F1 forms get correct instructions"""
        mock_filing_data = {
            'filing': {
                'form_type': 'F1',
                'committee_name': 'Test PAC',
                'committee_type': 'Independent Expenditure Committee'
            }
        }
        mock_from_http.return_value = mock_filing_data
        
        fragment = fec_fragment_loader("1234567")
        fragment_content = self._get_fragment_content(fragment)
        
        # Should include F1-specific instructions
        self.assertIn("Committee registration/organization details", fragment_content)
        self.assertIn("committee_name, committee_type, treasurer_name", fragment_content)
    
    @patch('fecfile.from_http')
    def test_f99_form_type_instructions(self, mock_from_http):
        """Test that F99 forms get correct instructions"""
        mock_filing_data = {
            'filing': {
                'form_type': 'F99',
                'committee_name': 'Test Committee'
            },
            'text': 'This is a test F99 filing text content.'
        }
        mock_from_http.return_value = mock_filing_data
        
        fragment = fec_fragment_loader("1234567")
        fragment_content = self._get_fragment_content(fragment)
        
        # Should include F99-specific instructions
        self.assertIn("Miscellaneous text communications", fragment_content)
        self.assertIn("'text' field contains the substantive content", fragment_content)
    
    @patch('fecfile.from_http')
    def test_financial_form_instructions(self, mock_from_http):
        """Test that financial forms get detailed instructions"""
        mock_filing_data = {
            'filing': {
                'form_type': 'F3X',
                'committee_name': 'Test PAC',
                'col_a_total_receipts': 50000.0
            },
            'itemizations': {
                'Schedule A': [],
                'Schedule B': []
            }
        }
        mock_from_http.return_value = mock_filing_data
        
        fragment = fec_fragment_loader("1234567")
        fragment_content = self._get_fragment_content(fragment)
        
        # Should include financial reporting instructions
        self.assertIn("Financial report showing money raised and spent", fragment_content)
        self.assertIn("FINANCIAL SUMMARY COLUMNS", fragment_content)
        self.assertIn("ITEMIZATION SCHEDULES", fragment_content)
        self.assertIn("contributor_organization_name", fragment_content)
        self.assertIn("payee_organization_name", fragment_content)
    
    @patch('fecfile.from_http')
    def test_amendment_instructions(self, mock_from_http):
        """Test amendment detection instructions"""
        mock_filing_data = {
            'filing': {
                'form_type': 'F3',
                'amendment_indicator': 'A',
                'previous_report_amendment_indicator': '7654321'
            }
        }
        mock_from_http.return_value = mock_filing_data
        
        fragment = fec_fragment_loader("1234567")
        fragment_content = self._get_fragment_content(fragment)
        
        # Should include amendment instructions
        self.assertIn("AMENDMENT DETECTION", fragment_content)
        self.assertIn("'A' = Standard Amendment", fragment_content)
        self.assertIn("'T' = Termination Amendment", fragment_content)
        self.assertIn("previous_report_amendment_indicator", fragment_content)
    
    @patch('fecfile.from_http')
    def test_response_style_instructions(self, mock_from_http):
        """Test that response style instructions are included"""
        mock_filing_data = {
            'filing': {
                'form_type': 'F3',
                'committee_name': 'Test Committee'
            }
        }
        mock_from_http.return_value = mock_filing_data
        
        fragment = fec_fragment_loader("1234567")
        fragment_content = self._get_fragment_content(fragment)
        
        # Should include style instructions
        self.assertIn("RESPONSE STYLE INSTRUCTIONS", fragment_content)
        self.assertIn("Start with your best judgment about whether this filing has unusual aspects", fragment_content)
        self.assertIn("Avoid excessive use of asterisks or bold text", fragment_content)
        self.assertIn("Write in a simple, direct style", fragment_content)
        self.assertIn("Don't provide a summary at the end", fragment_content)
    
    @patch('fecfile.from_http')
    def test_error_handling(self, mock_from_http):
        """Test error handling in fragment loader"""
        # Test HTTP error
        mock_from_http.side_effect = Exception("Network error")
        
        with self.assertRaises(ValueError) as context:
            fec_fragment_loader("1234567")
        
        self.assertIn("Error loading FEC filing 1234567", str(context.exception))
        self.assertIn("Network error", str(context.exception))

class TestHelperFunctions(unittest.TestCase):
    """Test helper functions (if they're still used)"""
    
    def test_json_serialization(self):
        """Test that complex objects can be JSON serialized"""
        test_data = {
            'string': 'test',
            'number': 123,
            'float': 123.45,
            'list': [1, 2, 3],
            'nested': {
                'key': 'value'
            }
        }
        
        # Should not raise an exception
        json_str = json.dumps(test_data, indent=2, default=str)
        self.assertIsInstance(json_str, str)
        self.assertIn('"string": "test"', json_str)

def run_manual_test():
    """Manual test function - requires actual FEC filing"""
    print("Running manual test with real FEC filing...")
    print("Note: This requires internet connection and valid FEC filing ID")
    
    try:
        fragment = fec_fragment_loader("1690664")
        
        print("SUCCESS: Fragment created without errors")
        print(f"Fragment type: {type(fragment)}")
        print(f"Fragment source: {fragment.source}")
        
        # The Fragment is a string subclass - the fragment itself IS the content
        print(f"Fragment is string-like: {isinstance(fragment, str)}")
        print(f"Content length: {len(fragment)}")
        print("Sample content (first 500 chars):")
        print(fragment[:500] + "...")
        
        # Check for key sections
        if "RESPONSE STYLE INSTRUCTIONS" in fragment:
            print("✓ Response style instructions found")
        if "FEC FILING ANALYSIS INSTRUCTIONS" in fragment:
            print("✓ FEC analysis instructions found")
        if "RAW FILING DATA" in fragment:
            print("✓ Raw filing data found")
        
    except Exception as e:
        print(f"ERROR: {e}")
        print("This might be expected if filing doesn't exist or network issues")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("Running LLM-FECFile Fragment Plugin Tests")
    print("=" * 40)
    
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n" + "=" * 40)
    
    # Run manual test
    run_manual_test()