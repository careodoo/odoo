# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class BankGuarantee(models.Model):
    """Bank guarantee (letter of guarantee) attached to a contract — bid,
    performance or advance — with issue/expiry tracking and status."""
    _name = 'care.bank.guarantee'
    _inherit = ['mail.thread']
    _description = 'Bank Guarantee'
    _order = 'expiry_date, id desc'

    name = fields.Char(string='المرجع', default='/', copy=False, readonly=True)
    experience_id = fields.Many2one('care.experience', string='العقد',
                                    ondelete='cascade', index=True, tracking=True)
    partner_id = fields.Many2one(related='experience_id.partner_id', string='الجهة', store=True)
    guarantee_number = fields.Char(string='رقم الكفالة', tracking=True)
    bank_name = fields.Char(string='البنك', tracking=True)
    guarantee_type = fields.Selection([
        ('bid', 'ابتدائية (دخول مناقصة)'),
        ('performance', 'نهائية (حسن تنفيذ)'),
        ('advance', 'دفعة مقدمة'),
    ], string='نوع الكفالة', default='performance', tracking=True)
    amount = fields.Monetary(string='القيمة', tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    issue_date = fields.Date(string='تاريخ الإصدار', tracking=True)
    expiry_date = fields.Date(string='تاريخ الانتهاء', tracking=True)
    days_to_expiry = fields.Integer(compute='_compute_expiry', store=True)
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('active', 'سارية'),
        ('expiring', 'تقترب من الانتهاء'),
        ('expired', 'منتهية'),
        ('released', 'مُفرَج عنها'),
        ('returned', 'مُعادة'),
    ], default='draft', compute='_compute_state', store=True, tracking=True, readonly=False)
    sent_to_client = fields.Boolean(string='أُرسلت للجهة', tracking=True)
    sent_date = fields.Date(string='تاريخ الإرسال')
    attachment = fields.Binary(string='نسخة الكفالة')
    attachment_name = fields.Char()
    note = fields.Text(string='ملاحظات')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('expiry_date')
    def _compute_expiry(self):
        today = fields.Date.today()
        for rec in self:
            rec.days_to_expiry = (rec.expiry_date - today).days if rec.expiry_date else 0

    @api.depends('expiry_date', 'issue_date')
    def _compute_state(self):
        today = fields.Date.today()
        for rec in self:
            if rec.state in ('released', 'returned'):
                continue
            if not rec.issue_date and not rec.expiry_date:
                rec.state = 'draft'
            elif rec.expiry_date and rec.expiry_date < today:
                rec.state = 'expired'
            elif rec.expiry_date and (rec.expiry_date - today).days <= 30:
                rec.state = 'expiring'
            else:
                rec.state = 'active'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.bank.guarantee') or '/'
        return super().create(vals_list)

    def action_mark_sent(self):
        self.write({'sent_to_client': True, 'sent_date': fields.Date.today()})

    def action_release(self):
        self.write({'state': 'released'})

    @api.model
    def _cron_expiry_alerts(self):
        today = fields.Date.today()
        soon = fields.Date.add(today, days=30)
        for g in self.search([('state', 'in', ('active', 'expiring')),
                              ('expiry_date', '!=', False), ('expiry_date', '<=', soon)]):
            users = g.experience_id.notify_user_ids | g.experience_id.manager_id
            for u in users:
                g.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('كفالة بنكية تقترب من الانتهاء: %s') % (g.guarantee_number or g.name),
                    date_deadline=g.expiry_date, user_id=u.id)
