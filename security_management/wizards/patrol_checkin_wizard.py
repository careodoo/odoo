from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import datetime

_logger = logging.getLogger(__name__)

class SecurityPatrolCheckinWizard(models.TransientModel):
    _name = 'security.patrol.checkin.wizard'
    _description = 'Patrol Checkpoint Check-in Wizard'
    
    patrol_id = fields.Many2one('security.patrol', string='Patrol', required=True, readonly=True)
    checkpoint_id = fields.Many2one('security.patrol.point', string='Checkpoint', required=True,
                                  domain="[('id', 'in', available_checkpoint_ids)]")
    available_checkpoint_ids = fields.Many2many('security.patrol.point', compute='_compute_available_checkpoints')
    notes = fields.Text(string='Notes')
    status = fields.Selection([
        ('normal', 'Normal'),
        ('issue', 'Issue Detected'),
        ('emergency', 'Emergency'),
    ], string='Status', default='normal', required=True)
    issue_description = fields.Text(string='Issue Description', 
                                  help="Describe any issues or emergencies encountered")
    image = fields.Binary(string='Photo Evidence')
    
    @api.depends('patrol_id')
    def _compute_available_checkpoints(self):
        for wizard in self:
            if wizard.patrol_id:
                wizard.available_checkpoint_ids = wizard.patrol_id.route_id.point_ids.ids
            else:
                wizard.available_checkpoint_ids = []
    
    @api.model
    def default_get(self, fields):
        res = super(SecurityPatrolCheckinWizard, self).default_get(fields)
        if self.env.context.get('active_model') == 'security.patrol' and self.env.context.get('active_id'):
            patrol = self.env['security.patrol'].browse(self.env.context.get('active_id'))
            if patrol.exists():
                res['patrol_id'] = patrol.id
                # Try to determine the next checkpoint based on the patrol's progress
                if patrol.route_id and patrol.route_id.point_ids:
                    completed_points = patrol.log_ids.mapped('checkpoint_id')
                    next_points = patrol.route_id.point_ids.filtered(lambda p: p not in completed_points)
                    if next_points:
                        res['checkpoint_id'] = next_points[0].id
        return res
    
    def action_checkin(self):
        """Process patrol checkpoint check-in"""
        self.ensure_one()
        
        if not self.patrol_id:
            raise UserError(_("No patrol selected"))
            
        if self.patrol_id.state not in ['in_progress']:
            raise UserError(_("This patrol is not currently in progress"))
            
        # Create patrol log
        log_vals = {
            'patrol_id': self.patrol_id.id,
            'checkpoint_id': self.checkpoint_id.id,
            'check_time': fields.Datetime.now(),
            'status': self.status,
            'notes': self.notes,
            'image': self.image,
        }
        
        if self.status in ['issue', 'emergency']:
            log_vals['issue_description'] = self.issue_description
            
        log = self.env['security.patrol.log'].create(log_vals)
        
        # Update patrol progress
        total_points = len(self.patrol_id.route_id.point_ids)
        completed_points = len(self.patrol_id.log_ids)
        progress = (completed_points / total_points) * 100 if total_points else 0
        
        self.patrol_id.write({
            'progress': progress,
            'last_checkpoint_id': self.checkpoint_id.id,
            'last_checkpoint_time': fields.Datetime.now(),
        })
        
        # If all checkpoints are completed, mark patrol as completed
        if completed_points >= total_points:
            self.patrol_id.write({
                'state': 'completed',
                'completion_time': fields.Datetime.now(),
            })
            
        # If there's an emergency, notify security managers
        if self.status == 'emergency':
            managers = self.env.ref('security_management.group_security_manager').users
            for manager in managers:
                self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': _('Emergency at Checkpoint: %s') % self.checkpoint_id.name,
                    'note': _('Emergency reported during patrol %s at checkpoint %s. Details: %s') % 
                            (self.patrol_id.name, self.checkpoint_id.name, self.issue_description or 'No details provided'),
                    'res_model_id': self.env.ref('security_management.model_security_patrol').id,
                    'res_id': self.patrol_id.id,
                    'user_id': manager.id,
                    'deadline': fields.Date.today(),
                })
        
        return {
            'type': 'ir.actions.act_window_close',
            'infos': {'success': True, 'message': _("Checkpoint checked successfully")}
        }
