# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HREmployee(models.Model):
    _inherit = "hr.employee"

    resigned = fields.Boolean(default=False)
    resignation_type = fields.Selection(
        [('resignation', 'Resignation'), ('termination', 'Termination'), ('death', 'Death')])
    date_of_leave = fields.Date('Leaving Date', tracking=True)

    @api.model
    def get_employee(self):
        """
            Get Employee record depends on current user.
        """
        employee_ids = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        return employee_ids[0] if employee_ids else False

    def get_active_contracts(self, date=fields.Date.today()):
        """
            get active contracts of employee
        """
        active_contract_ids = self.env['hr.contract'].search([
            '&',
            ('employee_id', '=', self.id),
            '|',
            '&',
            ('date_start', '<=', date),
            '|',
            ('date_end', '>=', date),
            ('date_end', '=', False),
            '|',
            ('trial_date_end', '=', False),
            ('trial_date_end', '>=', date),
        ])
        if active_contract_ids and len(active_contract_ids) > 1:
            raise UserError(_('Too many active contracts for employee %s') % self.name)
        return active_contract_ids
