from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class TestPatrolling(TransactionCase):
    def setUp(self):
        super(TestPatrolling, self).setUp()

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

        # Create test employee
        self.test_guard = self.env['hr.employee'].create({
            'name': 'Test Guard',
            'work_email': 'guard@example.com',
        })

        # Create test patrol points
        self.test_points = self.env['security.patrol.point'].create([
            {
                'name': 'Front Gate',
                'code': 'PT001',
                'premise_id': self.test_premise.id,
                'point_type': 'checkpoint',
                'check_interval': 2.0,
            },
            {
                'name': 'Main Entrance',
                'code': 'PT002',
                'premise_id': self.test_premise.id,
                'point_type': 'entrance',
            },
            {
                'name': 'Back Door',
                'code': 'PT003',
                'premise_id': self.test_premise.id,
                'point_type': 'patrol',
            },
        ])

        # Create test patrol route
        self.test_route = self.env['security.patrol.route'].create({
            'name': 'Perimeter Route',
            'premise_id': self.test_premise.id,
            'point_ids': [(6, 0, self.test_points.ids)],
            'frequency': 'daily',
            'start_time': 8.0,
            'end_time': 9.0,
        })

        # Create test patrol
        self.test_patrol = self.env['security.patrol'].create({
            'route_id': self.test_route.id,
            'guard_id': self.test_guard.id,
            'scheduled_start': datetime.now(),
        })

    def test_patrol_creation(self):
        """Test patrol creation and computed fields"""
        self.assertEqual(self.test_patrol.points_total, 3)
        self.assertEqual(self.test_patrol.points_covered, 0)
        self.assertEqual(self.test_patrol.completion_rate, 0)
        self.assertEqual(self.test_patrol.state, 'scheduled')

    def test_patrol_workflow(self):
        """Test complete patrol workflow"""
        # Start patrol
        self.test_patrol.action_start()
        self.assertEqual(self.test_patrol.state, 'in_progress')
        self.assertTrue(self.test_patrol.start_time)

        # Scan points
        for point in self.test_points:
            # Create patrol log for each point
            self.env['security.patrol.log'].create({
                'patrol_id': self.test_patrol.id,
                'point_id': point.id,
                'guard_id': self.test_guard.id,
                'notes': f'Scanned point {point.name}',
            })

        # Check progress
        self.assertEqual(self.test_patrol.points_covered, 3)
        self.assertEqual(self.test_patrol.completion_rate, 100.0)

        # Complete patrol
        self.test_patrol.action_complete()
        self.assertEqual(self.test_patrol.state, 'completed')
        self.assertTrue(self.test_patrol.end_time)

        # Check that the checkpoint's last_check_time is updated
        checkpoint = self.test_points.filtered(lambda p: p.point_type == 'checkpoint')
        self.assertTrue(checkpoint.last_check_time)

    def test_incomplete_patrol_completion(self):
        """Test completion of an incomplete patrol"""
        # Start patrol
        self.test_patrol.action_start()

        # Scan only 1 point
        self.env['security.patrol.log'].create({
            'patrol_id': self.test_patrol.id,
            'point_id': self.test_points[0].id,
            'guard_id': self.test_guard.id,
            'notes': 'Scanned one point',
        })

        # Check progress
        self.assertEqual(self.test_patrol.points_covered, 1)
        self.assertEqual(self.test_patrol.completion_rate, 33.33333333333333)

        # Try to complete - should open a wizard
        result = self.test_patrol.action_complete()
        self.assertEqual(result['res_model'], 'security.patrol.complete.wizard')

    def test_patrol_issue_reporting(self):
        """Test reporting issues during patrol"""
        # Start patrol
        self.test_patrol.action_start()

        # Create patrol log with issue
        patrol_log = self.env['security.patrol.log'].create({
            'patrol_id': self.test_patrol.id,
            'point_id': self.test_points[0].id,
            'guard_id': self.test_guard.id,
            'issue_detected': True,
            'issue_description': 'Broken window detected',
        })

        # Check if inspection was created automatically
        inspection = self.env['security.inspection'].search([
            ('patrol_log_id', '=', patrol_log.id)
        ])

        self.assertTrue(inspection)
        self.assertEqual(inspection.issue_description, 'Broken window detected')
        self.assertEqual(inspection.guard_id.id, self.test_guard.id)
        self.assertEqual(inspection.premise_id.id, self.test_premise.id)
