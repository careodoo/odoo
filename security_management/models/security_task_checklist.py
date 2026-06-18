from odoo import api, fields, models, _


class SecurityTaskChecklist(models.Model):
    _name = 'security.task.checklist'
    _description = 'Security Task Checklist Item'
    _order = 'sequence, id'

    name = fields.Char(string='Item Name', required=True)
    task_id = fields.Many2one('security.task', string='Task', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    
    is_completed = fields.Boolean(string='Completed', default=False)
    completed_by_id = fields.Many2one('security.employee', string='Completed By')
    completion_date = fields.Datetime(string='Completion Date')
    completion_notes = fields.Text(string='Completion Notes')
    
    is_required = fields.Boolean(string='Required', default=True)
    
    @api.onchange('is_completed')
    def _onchange_is_completed(self):
        if self.is_completed and not self.completed_by_id:
            self.completed_by_id = self.env.user.employee_id.id if self.env.user.employee_id else False
            self.completion_date = fields.Datetime.now()
        elif not self.is_completed:
            self.completed_by_id = False
            self.completion_date = False
            self.completion_notes = False
