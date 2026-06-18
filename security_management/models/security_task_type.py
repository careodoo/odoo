from odoo import models, fields, api, _

class SecurityTaskType(models.Model):
    _name = 'security.task.type'
    _description = 'Security Task Type'
    
    name = fields.Char(string='Task Type Name', required=True)
    code = fields.Char(string='Task Type Code', required=True)
    description = fields.Text(string='Description')
    color = fields.Char(string='Color', default='#007bff')
    sequence = fields.Integer(string='Sequence', default=1)
    active = fields.Boolean('Active', default=True)
    default_deadline_days = fields.Integer(string='Default Deadline (Days)', default=7,
                                         help='Default number of days to set for task deadline')
    requires_approval = fields.Boolean(string='Requires Approval', default=False,
                                     help='Whether tasks of this type require approval')
    approver_id = fields.Many2one('res.users', string='Default Approver',
                                help='Default user who will approve tasks of this type')
    default_checklist_item_ids = fields.One2many('security.task.checklist.template', 'task_type_id', 
                                               string='Default Checklist Items')
    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', 'Task type code must be unique!')
    ]
