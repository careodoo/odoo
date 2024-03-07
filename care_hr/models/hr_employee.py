from odoo import fields, models, api, Command


class Employee(models.Model):
    _inherit = 'hr.employee'

    category_ids = fields.Many2many('hr.employee.category', tracking=True)
    joining_ids = fields.One2many('hr.action.joining', 'employee_id')
    joining_date = fields.Date(compute='compute_joining_date', store=True)

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
