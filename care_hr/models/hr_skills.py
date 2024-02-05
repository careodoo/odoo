from odoo import fields, models, api, _


class Skill(models.Model):
    _inherit = 'hr.skill'

    employee_ids = fields.Many2many('hr.employee', compute='compute_employee_ids')
    employee_count = fields.Integer(compute='compute_employee_ids')

    def compute_employee_ids(self):
        for rec in self:
            rec.employee_ids = False
            rec.employee_count = 0
            employee_skills = self.env['hr.employee.skill'].search([('skill_id', '=', rec.id)])
            if employee_skills:
                rec.employee_ids = [(6, 0, employee_skills.mapped('employee_id').mapped('id'))]
                rec.employee_count = len(employee_skills)

    def action_view_employees(self):
        return {
            'name': _('Employees'),
            'view_mode': 'tree,form',
            'res_model': 'hr.employee',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.employee_ids.ids)]
        }


class SkillLevel(models.Model):
    _inherit = 'hr.skill.level'

    employee_ids = fields.Many2many('hr.employee', compute='compute_employee_ids')
    employee_count = fields.Integer(compute='compute_employee_ids')

    def compute_employee_ids(self):
        for rec in self:
            rec.employee_ids = False
            rec.employee_count = 0
            employee_levels = self.env['hr.employee.skill'].search([('skill_level_id', '=', rec.id)])
            if employee_levels:
                rec.employee_ids = [(6, 0, employee_levels.mapped('employee_id').mapped('id'))]
                rec.employee_count = len(employee_levels)

    def action_view_employees(self):
        return {
            'name': _('Employees'),
            'view_mode': 'tree,form',
            'res_model': 'hr.employee',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.employee_ids.ids)]
        }
