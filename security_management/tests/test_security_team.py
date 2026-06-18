from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class TestSecurityTeam(TransactionCase):
    def setUp(self):
        super(TestSecurityTeam, self).setUp()
        
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
        
        # Create test employees
        self.test_leader = self.env['hr.employee'].create({
            'name': 'Team Leader',
            'work_email': 'leader@example.com',
        })
        
        self.test_guards = self.env['hr.employee'].create([
            {
                'name': 'Guard 1',
                'work_email': 'guard1@example.com',
            },
            {
                'name': 'Guard 2',
                'work_email': 'guard2@example.com',
            },
            {
                'name': 'Guard 3',
                'work_email': 'guard3@example.com',
            },
        ])
        
        # Create test team
        self.test_team = self.env['security.team'].create({
            'name': 'Alpha Team',
            'code': 'ALPHA-1',
            'client_id': self.test_client.id,
            'leader_id': self.test_leader.id,
            'member_ids': [(6, 0, self.test_guards.ids + [self.test_leader.id])],
        })
    
    def test_team_creation(self):
        """Test team creation and computed fields"""
        self.assertEqual(self.test_team.name, 'Alpha Team')
        self.assertEqual(self.test_team.member_count, 4)  # 3 guards + 1 leader
        self.assertEqual(self.test_team.task_count, 0)
        self.assertEqual(self.test_team.patrol_count, 0)
    
    def test_task_assignment(self):
        """Test task assignment to team members"""
        # Create a task category
        test_category = self.env['security.task.category'].create({
            'name': 'Security Check',
            'description': 'Regular security checks',
        })
        
        # Create a task assigned to a team member
        test_task = self.env['security.task'].create({
            'name': 'Check Main Gate',
            'description': 'Ensure main gate is secured',
            'category_id': test_category.id,
            'priority': '2',
            'assigned_to': self.test_guards[0].id,
            'client_id': self.test_client.id,
            'assigned_team_id': self.test_team.id,
        })
        
        # Check that the task is counted in team's task_count
        self.assertEqual(self.test_team.task_count, 1)
        
        # Test task workflow
        test_task.action_accept()
        self.assertEqual(test_task.state, 'accepted')
        
        test_task.action_start_progress()
        self.assertEqual(test_task.state, 'in_progress')
        
        test_task.action_complete()
        self.assertEqual(test_task.state, 'completed')
        self.assertTrue(test_task.date_completed)
    
    def test_task_forwarding(self):
        """Test forwarding a task to another team member"""
        # Create a task category
        test_category = self.env['security.task.category'].create({
            'name': 'Security Check',
            'description': 'Regular security checks',
        })
        
        # Create a task assigned to a team member
        test_task = self.env['security.task'].create({
            'name': 'Check Main Gate',
            'description': 'Ensure main gate is secured',
            'category_id': test_category.id,
            'priority': '2',
            'assigned_to': self.test_guards[0].id,
            'client_id': self.test_client.id,
            'assigned_team_id': self.test_team.id,
        })
        
        # Forward the task using wizard
        forward_wizard = self.env['security.task.forward.wizard'].create({
            'task_id': test_task.id,
            'employee_id': self.test_guards[1].id,
            'reason': 'Not available today',
        })
        
        forward_wizard.action_forward()
        
        # Check task state and delegation
        self.assertEqual(test_task.state, 'forwarded')
        self.assertEqual(test_task.delegated_to.id, self.test_guards[1].id)