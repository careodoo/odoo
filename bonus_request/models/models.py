# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning, ValidationError


class BonusRequest(models.Model):
    _name = "bonus.request"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", default="New", readonly=True, copy=False)

    state = fields.Selection(string="", selection=[('d_manager', 'Direct Manager'),
                                                   ('hr_manager', 'HR Manager'), ('accounting', 'Accounting'),
                                                   ('confirm', 'Confirmed'), ('rejected', 'Rejected')], required=False, default='d_manager')

    @api.model
    def create(self, vals):
        vals['name'] = (self.env['ir.sequence'].next_by_code('bonus.request')) or 'New'
        return super(BonusRequest, self).create(vals)

    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee Name", required=False, )

    request_date = fields.Date(string="Today Date", required=False, default=fields.Date.context_today)

    bonus_amount = fields.Float(string="Bonus Amount", required=False, compute="get_bonus_amount")
    bonus_type = fields.Selection(string="", selection=[('amount', 'Amount'), ('days', 'Days'), ], required=False, )
    bonus_amount_amount = fields.Float(string="Bonus Amount", required=False, )
    bonus_amount_days = fields.Float(string="Bonus Days", required=False, )

    reason = fields.Text(string="Reason", required=False, )

    refundable_bonus = fields.Float(string="A Refundable Bonus", required=False, readonly=True, )

    contract_id = fields.Many2one(comodel_name="hr.contract", string="", required=False,
                                  related="employee_id.contract_id")

    day_value = fields.Float(string="", required=False, compute="_compute_day_value")

    @api.depends('employee_id', 'contract_id')
    def _compute_day_value(self):
        for rec in self:
            if rec.employee_id and rec.contract_id:
                rec.day_value = rec.contract_id.wage / 26
            else:
                rec.day_value = 0.0
    #
    # @api.constrains('bonus_amount')
    # def loan_type_constrains(self):
    #     if self.bonus_amount > 0:
    #         the_rest = self.bonus_amount * 0.10
    #         self.refundable_bonus = the_rest

    @api.depends('bonus_amount', 'bonus_type', 'bonus_amount_amount', 'bonus_amount_days', 'employee_id')
    def get_bonus_amount(self):
        for rec in self:
            if rec.bonus_type == 'amount':
                rec.bonus_amount = rec.bonus_amount_amount
            elif rec.bonus_type == 'days':
                rec.bonus_amount = rec.bonus_amount_days * rec.day_value
            else:
                rec.bonus_amount = 0.0

    def d_manager_confirm(self):
        for rec in self:
            res_user = rec.env['res.users'].search([('id', '=', rec._uid)])
            if rec.env.user.id == rec.employee_id.parent_id.user_id.id:
                rec.write({
                    'state': 'hr_manager'
                })
            elif res_user.has_group('hr.group_hr_user'):
                rec.write({
                    'state': 'hr_manager'
                })
            else:
                raise ValidationError("Only Employee Manger OR HR Manager Can Create That! ")

    def hr_manager_confirm(self):
        for rec in self:
            rec.state = 'accounting'

    def accounting_confirm(self):
        for rec in self:
            res_user = rec.env['res.users'].search([('id', '=', rec._uid)])
            if res_user.has_group('account.group_account_manager'):
                rec.state = 'confirm'
            else:
                raise ValidationError("Only Account Manger Can Approve That! ")

    def reject(self):
        self.state = 'rejected'

