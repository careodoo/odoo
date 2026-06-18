from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class TestKeyManagement(TransactionCase):
    def setUp(self):
        super(TestKeyManagement, self).setUp()

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
            'contract_start_date': datetime.today().date(),
            'contract_end_date': (datetime.today() + timedelta(days=365)).date(),
        })

        # Create test premise
        self.test_premise = self.env['security.premise'].create({
            'name': 'Test Premise',
            'code': 'TP001',
            'client_id': self.test_client.id,
            'address': '123 Test Slistt',
        })

        # Create test floor
        self.test_floor = self.env['security.floor'].create({
            'name': 'Ground Floor',
            'number': 0,
            'premise_id': self.test_premise.id,
        })

        # Create test unit
        self.test_unit = self.env['security.unit'].create({
            'name': 'Test Unit',
            'unit_number': 'U001',
            'floor_id': self.test_floor.id,
            'unit_type': 'office',
        })

        # Create test key hub
        self.test_key_hub = self.env['security.key.hub'].create({
            'name': 'Main Hub',
            'code': 'HUB001',
            'location': 'Reception',
            'premise_id': self.test_premise.id,
        })

        # Create test employee
        self.test_employee = self.env['hr.employee'].create({
            'name': 'Test Guard',
            'work_email': 'guard@example.com',
        })

        # Create test key
        self.test_key = self.env['security.key'].create({
            'name': 'Office Main Door',
            'door_number': 'D001',
            'key_number': 'K001',
            'unit_id': self.test_unit.id,
            'key_hub_id': self.test_key_hub.id,
            'description': 'Main door key for test unit',
        })

    def test_key_creation(self):
        """Test key creation and default state"""
        self.assertEqual(self.test_key.state, 'available')
        self.assertTrue(self.test_key.barcode)
        self.assertTrue(self.test_key.qr_code)
        self.assertEqual(self.test_key.log_count, 0)

    def test_key_checkout_process(self):
        """Test key checkout process"""
        # Create checkout wizard
        checkout_wizard = self.env['security.key.checkout.wizard'].create({
            'key_id': self.test_key.id,
            'employee_id': self.test_employee.id,
            'expected_return_time': datetime.now() + timedelta(hours=8),
            'reason': 'Testing key checkout',
        })

        # Process checkout
        checkout_wizard.action_checkout()

        # Check key state
        self.assertEqual(self.test_key.state, 'checked_out')
        self.assertEqual(self.test_key.current_holder_id.id, self.test_employee.id)
        self.assertTrue(self.test_key.check_out_time)
        self.assertTrue(self.test_key.expected_return_time)

        # Check log creation
        self.assertEqual(self.test_key.log_count, 1)
        log = self.test_key.log_ids[0]
        self.assertEqual(log.operation, 'check_out')
        self.assertEqual(log.employee_id.id, self.test_employee.id)

    def test_key_checkin_process(self):
        """Test key check-in process"""
        # First checkout the key
        checkout_wizard = self.env['security.key.checkout.wizard'].create({
            'key_id': self.test_key.id,
            'employee_id': self.test_employee.id,
            'expected_return_time': datetime.now() + timedelta(hours=8),
            'reason': 'Testing key checkout',
        })
        checkout_wizard.action_checkout()

        # Create checkin wizard
        checkin_wizard = self.env['security.key.checkin.wizard'].create({
            'key_id': self.test_key.id,
            'notes': 'Testing key checkin',
        })

        # Process checkin
        checkin_wizard.action_checkin()

        # Check key state
        self.assertEqual(self.test_key.state, 'available')
        self.assertFalse(self.test_key.current_holder_id)

        # Check log creation
        self.assertEqual(self.test_key.log_count, 2)
        log = self.test_key.log_ids[0]  # Most recent log
        self.assertEqual(log.operation, 'check_in')

    def test_invalid_checkout(self):
        """Test invalid key checkout scenarios"""
        # First checkout the key
        checkout_wizard = self.env['security.key.checkout.wizard'].create({
            'key_id': self.test_key.id,
            'employee_id': self.test_employee.id,
            'expected_return_time': datetime.now() + timedelta(hours=8),
            'reason': 'First checkout',
        })
        checkout_wizard.action_checkout()

        # Try to check out again
        checkout_wizard2 = self.env['security.key.checkout.wizard'].create({
            'key_id': self.test_key.id,
            'employee_id': self.test_employee.id,
            'expected_return_time': datetime.now() + timedelta(hours=8),
            'reason': 'Second checkout',
        })

        with self.assertRaises(UserError):
            checkout_wizard2.action_checkout()

    def test_key_lost_process(self):
        """Test marking a key as lost"""
        # Create lost key wizard
        lost_wizard = self.env['security.key.lost.wizard'].create({
            'key_id': self.test_key.id,
            'reason': 'Key lost during testing',
        })

        # Mark as lost
        lost_wizard.action_mark_lost()

        # Check key state
        self.assertEqual(self.test_key.state, 'lost')

        # Check log creation
        self.assertEqual(self.test_key.log_count, 1)
        log = self.test_key.log_ids[0]
        self.assertEqual(log.operation, 'lost')
