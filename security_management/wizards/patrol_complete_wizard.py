from odoo import api, fields, models, _

class PatrolCompleteConfirm(models.TransientModel):
    _name = 'security.patrol.confirm'
    _description = 'Patrol Completion Confirmation'

    patrol_id = fields.Many2one('security.patrol', string='Patrol', required=True)
    guard_id = fields.Many2one('security.guard', string='Guard', readonly=True)
    message = fields.Text(string='Message', readonly=True)
    reason = fields.Text(string='Reason for Incomplete Patrol')
    
    @api.onchange('patrol_id')
    def _onchange_patrol_id(self):
        """Set message based on uncovered points"""
        if self.patrol_id:
            # Set the guard_id from the patrol
            self.guard_id = self.patrol_id.guard_id.id
            
            uncovered_points = self.patrol_id.get_uncovered_points()
            if uncovered_points:
                point_names = ', '.join(uncovered_points.mapped('name'))
                self.message = _("The following patrol points have not been covered: %s\n\nDo you want to complete the patrol anyway?") % point_names
            else:
                self.message = _("All patrol points have been covered.")
    
    def action_confirm(self):
        """Confirm patrol completion"""
        self.ensure_one()
        if self.patrol_id:
            # Apply proper company context
            self = self.with_context(company_id=self.env.company.id)
            patrol = self.patrol_id.with_context(company_id=self.env.company.id)
            
            # Record the reason if provided
            if self.reason:
                patrol.message_post(body=_("Patrol completed with missing points. Reason: %s") % self.reason)
            
            # Complete the patrol and return the result
            return patrol._complete_patrol()
            
        return {'type': 'ir.actions.act_window_close'}
    
    def action_cancel(self):
        """Cancel patrol completion"""
        return {'type': 'ir.actions.act_window_close'}
