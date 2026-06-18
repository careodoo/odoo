from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date, timedelta

class TestSecurityClient(TransactionCase):
    def setUp(self):
        super(TestSecurityClient, self).setUp()
        
        # Create test partner
        self.test_partner = self.env['res.partner'].create({
            'name': 'Test Client Contact',
            'email': 'test@example.com',
            'phone': '1234567890',
        })
        
        # Create test client
        self.test_client = self.env['security.client'].create({
            'name': 'Test Client',
            'contact_id': self.test_partner.id,
            'contract_start_date': date.today(),
            'contract_end_date': date.today() + timedelta(days=365),
        })
    
    def test_client_creation(self):
        """Test client creation and computed fields"""
        self.assertEqual(self.test_client.name, 'Test Client')
        self.assertEqual(self.test_client.team_count, 0)
        self.assertEqual(self.test_client.premise_count, 0)
        self.assertEqual(self.test_client.contract_state, 'active')
        
    def test_contract_dates_constraint(self):
        """Test contract dates constraint"""
        with self.assertRaises(ValidationError):
            self.env['security.client'].create({
                'name': 'Invalid Client',
                'contact_id': self.test_partner.id,
                'contract_start_date': date.today(),
                'contract_end_date': date.today() - timedelta(days=1),
            })
    
    def test_contract_expiry(self):
        """Test contract expiry logic"""
        # Create a client with contract expiring soon
        expiring_client = self.env['security.client'].create({
            'name': 'Expiring Client',
            'contact_id': self.test_partner.id,
            'contract_start_date': date.today() - timedelta(days=365),
            'contract_end_date': date.today() + timedelta(days=15),
        })
        
        self.assertEqual(expiring_client.contract_state, 'expiring')
        
        # Create an expired client
        expired_client = self.env['security.client'].create({
            'name': 'Expired Client',
            'contact_id': self.test_partner.id,
            'contract_start_date': date.today() - timedelta(days=365),
            'contract_end_date': date.today() - timedelta(days=1),
        })
        
        self.assertEqual(expired_client.contract_state, 'expired')
        
    def test_extend_contract(self):
        """Test contract extension"""
        original_end_date = self.test_client.contract_end_date
        self.test_client.extend_contract(months=6)
        
        # Check that contract end date was extended by 6 months
        expected_end_date = original_end_date + timedelta(days=30*6)
        self.assertEqual(self.test_client.contract_end_date, expected_end_date)
