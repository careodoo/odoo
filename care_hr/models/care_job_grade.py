# -*- coding: utf-8 -*-
from odoo import fields, models, api


class CareJobGrade(models.Model):
    """Organizational job grade / wage tier (e.g. 75 / 80 / 85 base for labour).

    Foundation object referenced by contracts and workforce planning.
    """
    _name = 'care.job.grade'
    _description = 'Job Grade / Wage Tier'
    _order = 'sequence, code'

    name = fields.Char(string='Grade', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    base_wage = fields.Monetary(string='Default Base Wage',
                                help='Default monthly basic salary for this grade.')
    wage_min = fields.Monetary(string='Min Wage')
    wage_max = fields.Monetary(string='Max Wage')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    note = fields.Text(string='Scope / Notes')
    employee_count = fields.Integer(string='Employees', compute='_compute_employee_count')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Job grade code must be unique.'),
    ]

    @api.depends('name')
    def _compute_employee_count(self):
        Emp = self.env['hr.employee']
        has_field = 'job_grade_id' in Emp._fields
        for grade in self:
            grade.employee_count = Emp.search_count(
                [('job_grade_id', '=', grade.id)]) if has_field else 0
