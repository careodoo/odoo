from odoo import fields, models, api, _


class ProjectTask(models.Model):
    _inherit = 'project.task'

    forward_ids = fields.One2many('project.task.forward', 'task_id')

    def button_forward(self):
        return {
            'name': _('Forward Task'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'project.task.forward',
            'context': {
                'default_task_id': self.id,
            },
            'target': 'new',
        }
