from odoo import fields, models, api, Command
from odoo.exceptions import ValidationError


class Employee(models.Model):
    _inherit = 'hr.employee'

    category_ids = fields.Many2many('hr.employee.category', tracking=True)
    joining_ids = fields.One2many('hr.action.joining', 'employee_id')
    joining_date = fields.Date(compute='compute_joining_date', store=True)
    suspend_date = fields.Date(tracking=True)
    suspend_reason = fields.Text(tracking=True)
    suspend_by = fields.Many2one('res.users', tracking=True)
    can_print_reports = fields.Boolean()
    can_edit = fields.Boolean()

    def write(self, vals):
        if not self.env.context.get('ignore_suspend', False):
            for rec in self:
                if rec.suspend_date and not rec.can_edit:
                    raise ValidationError(f"you can't edit suspended employee {rec.name}!")
        res = super(Employee, self).write(vals)
        return res

    def button_suspend(self):
        return {
            'name': 'Suspend Employee',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'hr.employee.suspend',
            'context': {
                'default_employee_id': self.id,
                'default_date': fields.Date.today(),
            },
            'target': 'new',
        }

    def button_unsuspend(self):
        return {
            'name': 'Unsuspend Employee',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'hr.employee.suspend',
            'context': {
                'default_employee_id': self.id,
                'default_unsuspend': True,
            },
            'target': 'new',
        }

    @api.depends('joining_ids')
    def compute_joining_date(self):
        for rec in self:
            rec.joining_date = False
            if rec.joining_ids:
                rec.joining_date = rec.joining_ids.sorted(key='join_date', reverse=True)[0].join_date

    def _mail_track(self, tracked_fields, initial_values):
        changes, tracking_value_ids = super()._mail_track(tracked_fields, initial_values)
        # Many2many tracking
        if len(changes) > len(tracking_value_ids):
            for changed_field in changes:
                if tracked_fields[changed_field]['type'] == 'many2many':
                    field = self.env['ir.model.fields']._get(self._name, changed_field)
                    vals = {
                        'field': field.id,
                        'field_desc': field.field_description,
                        'field_type': field.ttype,
                        'tracking_sequence': field.tracking,
                        'old_value_char': ', '.join(initial_values[changed_field].mapped('name')),
                        'new_value_char': ', '.join(self[changed_field].mapped('name')),
                    }
                    tracking_value_ids.append(Command.create(vals))
        return changes, tracking_value_ids
