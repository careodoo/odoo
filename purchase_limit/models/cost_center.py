from odoo import fields, models, api
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import date


class CostCenter(models.Model):
    _inherit = 'cost.center'

    purchase_limit = fields.Float()
    annual_budget = fields.Float()
    remaining_annual_budget = fields.Float(compute='compute_remaining_annual_budget', store=True)
    budget_start_date = fields.Date()
    month_ids = fields.One2many('cost.center.month', 'cost_center_id')
    extra_budget_ids = fields.One2many('cost.center.extra.budget', 'cost_center_id')

    @api.depends('month_ids.remaining_budget')
    def compute_remaining_annual_budget(self):
        for rec in self:
            rec.remaining_annual_budget = sum(rec.month_ids.mapped('remaining_budget')) if rec.month_ids else False

    def get_monthly_budget(self, date):
        budget = 0
        if date:
            month = self.month_ids.filtered(lambda m: m.sequence == date.month)
            if month:
                budget = month[0].total_budget
        return budget

    def get_remaining_monthly_budget(self, date):
        budget = 0
        if date:
            month = self.month_ids.filtered(lambda m: m.sequence == date.month)
            if month:
                budget = month[0].remaining_budget
        return budget

    def generate_monthly_budget(self):
        if self.annual_budget <= 0 or not self.budget_start_date:
            raise UserError("please add Budget and Start Sate")
        self.month_ids = [(5, 0, 0)]
        for i in range(12):
            self.env['cost.center.month'].create({
                'cost_center_id': self.id,
                'sequence': i + 1,
                'date': (self.budget_start_date + relativedelta(months=i)),
                'date_string': (self.budget_start_date + relativedelta(months=i)).strftime('%B %Y'),
                'budget': self.annual_budget / 12,
            })

    def transfer_budget(self):
        return {
            'name': 'Transfer Budget',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'cost.center.transfer.budget',
            'target': 'new',
            'context': {
                'default_cost_center_id': self.id
            }
        }

    def add_extra_budget(self):
        return {
            'name': 'Add Extra Budget',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'cost.center.extra.budget',
            'target': 'new',
            'context': {
                'default_cost_center_id': self.id
            }
        }


class MonthlyCostCenter(models.Model):
    _name = 'cost.center.month'
    _description = 'Monthly Cost Center'
    _rec_name = 'date'

    cost_center_id = fields.Many2one('cost.center')
    sequence = fields.Integer()
    date = fields.Date(required=True)
    date_string = fields.Char()
    budget = fields.Float(required=True)
    transfer_budget = fields.Float()
    extra_budget = fields.Float()
    total_budget = fields.Float(compute='compute_total_budget', store=True)
    used_budget = fields.Float()
    remaining_budget = fields.Float(compute='compute_remaining_budget', store=True)
    extra_budget_ids = fields.One2many('cost.center.extra.budget', 'month_id')
    transfer_budget_ids = fields.One2many('cost.center.transfer.budget', 'to_month')
    purchase_order_ids = fields.Many2many('purchase.order', string='Purchase Orders')

    @api.depends('budget', 'extra_budget', 'transfer_budget')
    def compute_total_budget(self):
        for rec in self:
            rec.total_budget = rec.budget + rec.extra_budget + rec.transfer_budget

    @api.depends('total_budget', 'used_budget')
    def compute_remaining_budget(self):
        for rec in self:
            rec.remaining_budget = rec.total_budget - rec.used_budget


class CostCenterExtraBudget(models.Model):
    _name = 'cost.center.extra.budget'
    _description = 'Cost Center Extra Budget'
    _rec_name = 'extra'

    def get_default_sign_lines(self):
        return [(0, 0, {'employee_id': rec.user_id.employee_id.id}) for rec in self.env['default.cost.center.sign'].search([])]

    cost_center_id = fields.Many2one('cost.center')
    month_id = fields.Many2one('cost.center.month', domain="[('cost_center_id', '=', cost_center_id)]")
    extra = fields.Float(required=True)
    signature_lines = fields.One2many('purchase.sign', 'extra_budget_id', default=get_default_sign_lines)
    signature_users = fields.Many2many('res.users', compute='compute_signature_users', store=True)
    user_confirmed = fields.Boolean(compute='compute_user_confirmed')
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('sent', 'Sent'), ('confirm', 'Confirm')
    ], default='draft')

    def compute_user_confirmed(self):
        for rec in self:
            rec.user_confirmed = False
            if rec.signature_lines and rec.signature_users:
                if self.env.uid in rec.signature_users.ids:
                    employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
                    if rec.signature_lines.filtered(lambda l: l.employee_id.id == employee.id and l.confirm):
                        rec.user_confirmed = True

    @api.depends('signature_lines')
    def compute_signature_users(self):
        for rec in self:
            rec.signature_users = False
            if rec.signature_lines:
                rec.signature_users = [(6, 0, [u.id for u in rec.signature_lines.mapped('employee_id').mapped('user_id')])]

    def button_confirm(self):
        for extra in self:
            extra.signature_lines.filtered(lambda l: l.employee_id.user_id.id == self.env.uid).write({
                'confirm': True,
                'date_confirm': fields.Datetime.now(),
            })
            if extra.signature_lines.filtered(lambda l: not l.confirm):
                return
            extra.month_id.extra_budget += extra.extra
            extra.write({'state': 'confirm'})

    def button_request_approval(self):
        if not self.signature_users:
            raise UserError("Ask your admin to configure extra budget approvers!")
        if self.extra <= 0:
            raise UserError("amount must be more than 0!")
        template = self.env.ref('purchase_limit.purchase_sign_template_extra_budget')
        for line in self.signature_lines:
            self.env['mail.template'].browse(template.id).send_mail(
                line.id, force_send=True, notif_layout='mail.mail_notification_light'
            )
            line.sudo().activity_schedule(
                'purchase_report.mail_act_purchase_sign_create',
                summary='Extra Budget Sign',
                note='Sign Extra Budget for cost center {} for {}'.format(self.cost_center_id.name, self.month_id.date_string),
                user_id=line.employee_id.user_id.id)
        self.write({'state': 'sent'})


class CostCenterTransferBudget(models.Model):
    _name = 'cost.center.transfer.budget'
    _description = 'Cost Center Transfer Budget'

    cost_center_id = fields.Many2one('cost.center')
    from_month = fields.Many2one('cost.center.month', domain="[('cost_center_id', '=', cost_center_id)]", required=True)
    to_month = fields.Many2one('cost.center.month', domain="[('cost_center_id', '=', cost_center_id)]", required=True)
    amount = fields.Float(required=True)
    comment = fields.Text()

    @api.onchange('from_month')
    def onchange_from_month(self):
        self.amount = self.from_month.remaining_budget

    @api.constrains('amount')
    def check_amount(self):
        if self.amount <= 0:
            raise UserError("please enter valid value!")
        if self.amount > self.from_month.remaining_budget:
            raise UserError("Amount is more than remaining budget!")

    def button_transfer(self):
        self.from_month.remaining_budget -= self.amount
        self.to_month.transfer_budget += self.amount


class DefaultCostCenterSign(models.Model):
    _name = 'default.cost.center.sign'
    _description = 'Default Cost Center Sign Employee'
    _rec_name = 'user_name'

    user_id = fields.Many2one('res.users', required=True)
    user_name = fields.Char(related='user_id.name', store=True)


class PurchaseSign(models.Model):
    _inherit = 'purchase.sign'

    extra_budget_id = fields.Many2one('cost.center.extra.budget')

    @api.depends('purchase_order_id', 'request_id', 'extra_budget_id')
    def compute_rec_name(self):
        for rec in self:
            rec.rec_name = ''
            if rec.purchase_order_id:
                rec.rec_name = 'Ask to Sign PO {}'.format(rec.purchase_order_id.name)
            elif rec.request_id:
                rec.rec_name = 'Ask to Sign PR {}'.format(rec.request_id.name)
            elif rec.extra_budget_id:
                rec.rec_name = 'Ask to Sign Extra Budget for Cost Center {} for {}'.format(
                    rec.extra_budget_id.cost_center_id.name, rec.extra_budget_id.month_id.date_string
                )

