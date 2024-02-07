from odoo import fields, models, api, _
from datetime import date
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _order = 'id desc'

    def get_default_sign_lines(self):
        return [
            (0, 0, {'employee_id': rec.employee_id.id}) for rec in self.env['default.sign.employee'].search([
                ('option_online', '=', True)
            ])
        ]

    lines = fields.One2many('purchase.request.line', 'request_id')
    signature_lines = fields.One2many('purchase.sign', 'request_id', default=get_default_sign_lines)
    name = fields.Char(required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'), string='PR Number')
    suggested_supplier = fields.Many2many('res.partner', domain=[('supplier_rank', '>=', 1)])
    department_id = fields.Many2one('hr.department', required=True)
    suggested_po = fields.Many2many('purchase.order', domain="[('department_id', '=', department_id)]")
    pr_date = fields.Date(default=fields.Date.today)
    project_id = fields.Many2one('project.project', string='Project Name')
    cost_center = fields.Many2one('cost.center', domain="[('department_id', '=', department_id)]")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    phone = fields.Char(related='company_id.phone')
    address = fields.Char(related='company_id.partner_id.contact_address_complete')
    country = fields.Many2one('res.country', related='company_id.country_id')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, default=lambda self: self.env.company.currency_id)
    terms = fields.Html()
    notes = fields.Html()
    # print options
    show_signature = fields.Boolean(default=True)
    show_terms = fields.Boolean(default=True)
    show_notes = fields.Boolean(default=True)
    show_budget = fields.Boolean(default=True)
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('confirm', 'Confirm')
    ], default='draft')
    signature_users = fields.Many2many('res.users', compute='compute_signature_users', store=True)
    user_confirmed = fields.Boolean(compute='compute_user_confirmed')

    def check_print_option(self, employee):
        return self.env['default.sign.employee'].search([
            ('employee_id', '=', employee.id), ('option_print', '=', True)
        ])

    def get_sign_lines(self):
        lines = [[l.employee_id, l.date_confirm] for l in self.signature_lines if self.check_print_option(l.employee_id)]

        print_employees = self.env['default.sign.employee'].search([('option_print', '=', True)]).mapped('employee_id').mapped('id')
        sign_employees = [l.employee_id.id for l in self.signature_lines if self.check_print_option(l.employee_id)]
        delta = list(set(print_employees) - set(sign_employees))
        if delta:
            employees = self.env['hr.employee'].browse(delta)
            for emp in employees:
                lines.append([emp, False])
        return lines

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

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            department_id = vals.get('department_id')
            department = self.env['hr.department'].browse(department_id)
            if not department.short_code:
                raise UserError(_("Department {} has no short code".format(department.name)))
            vals['name'] = department.short_code + '/' + self.env['ir.sequence'].next_by_code('purchase.request') + '/' + str(date.today().year) or _('New')

        result = super(PurchaseRequest, self).create(vals)
        return result

    def show_results(self):
        domain = []
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        if self.suggested_supplier:
            domain.append(('partner_id', 'in', self.suggested_supplier.ids))
        if self.suggested_po:
            domain.append(('id', 'in', self.suggested_po.ids))
        results = self.env['purchase.order'].search(domain)
        # if self.pr_date:
        #     results.filtered(lambda p: p.date_approve).filtered(lambda p: p.date_approve.date() == self.pr_date)

        request_line_ids = []
        if results:
            if self.lines:
                self.lines.unlink()
            for purchase in results:
                request_line_ids.append(self.env['purchase.request.line'].create({
                    'purchase_id': purchase.id,
                    'user_id': purchase.user_id.id,
                    'partner_id': purchase.partner_id.id,
                    'request_id': self.id,
                }).id)
            self.lines = [(6, 0, request_line_ids)]

    def print_report(self):
        return self.env.ref('purchase_report.action_report_purchase_request').report_action(self)

    def button_confirm(self):
        for order in self:
            order.signature_lines.filtered(lambda l: l.employee_id.user_id.id == self.env.uid).write({
                'confirm': True,
                'date_confirm': fields.Datetime.now(),
            })
            if order.signature_lines.filtered(lambda l: not l.confirm):
                return
            order.write({'state': 'confirm'})
            for line in self.lines:
                line.purchase_id.button_confirm()

    def button_revise(self):
        for order in self.filtered(lambda o: o.state != 'confirm'):
            order.signature_lines.filtered(lambda l: l.employee_id.user_id.id == self.env.uid).write({
                'confirm': False,
                'date_confirm': False,
            })


class PurchaseRequestLine(models.Model):
    _name = 'purchase.request.line'
    _order = 'id desc'

    request_id = fields.Many2one('purchase.request')
    purchase_id = fields.Many2one('purchase.order')
    reference = fields.Char(related='purchase_id.name')
    confirmation_date = fields.Datetime(related='purchase_id.date_approve')
    partner_id = fields.Many2one('res.partner', string='Vendor')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    receipt_date = fields.Datetime(related='purchase_id.date_planned')
    user_id = fields.Many2one('res.partner')
    amount_total = fields.Monetary(related='purchase_id.amount_total')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, default=lambda self: self.env.company.currency_id)
    state = fields.Selection(related='purchase_id.state')


class CostCenter(models.Model):
    _name = 'cost.center'
    _order = 'id desc'

    name = fields.Char()
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    department_id = fields.Many2one('hr.department')
    active = fields.Boolean(default=True)


class PurchaseSign(models.Model):
    _name = 'purchase.sign'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'rec_name'
    _description = 'Purchase Sign'

    request_id = fields.Many2one('purchase.request')
    purchase_order_id = fields.Many2one('purchase.order')
    employee_id = fields.Many2one('hr.employee')
    employee_title = fields.Char(related='employee_id.job_title')
    signature = fields.Binary()
    confirm = fields.Boolean(string='Approved Online')
    date_confirm = fields.Datetime('Confirmation Date')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    rec_name = fields.Char(compute='compute_rec_name', store=True)

    @api.depends('purchase_order_id')
    def compute_rec_name(self):
        for rec in self:
            rec.rec_name = ''
            if rec.purchase_order_id:
                rec.rec_name = 'Ask to Sign PO {}'.format(rec.purchase_order_id.name)
            elif rec.request_id:
                rec.rec_name = 'Ask to Sign PR {}'.format(rec.request_id.name)

    def send_sign_request(self):
        if self.request_id:
            template = self.env.ref('purchase_report.purchase_sign_template_pr')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True,
                                                                    notif_layout='mail.mail_notification_light')
            self.sudo().activity_schedule(
                'purchase_report.mail_act_purchase_sign_create',
                summary='PO {} Sign'.format(self.request_id.name),
                note='PO {} Sign'.format(self.request_id.name),
                user_id=self.employee_id.user_id.id)
        elif self.purchase_order_id:
            template = self.env.ref('purchase_report.purchase_sign_template_po')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True,
                                                                    notif_layout='mail.mail_notification_light')
            self.sudo().activity_schedule(
                'purchase_report.mail_act_purchase_sign_create',
                summary='PR{} Sign'.format(self.purchase_order_id.name),
                note='PR {} Sign'.format(self.purchase_order_id.name),
                user_id=self.employee_id.user_id.id)
