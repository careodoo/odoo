# -*- coding: utf-8 -*-
"""إنهاء التحاق عامل — a request (by the client, a supervisor, or an admin) to
remove a worker from a site, with reasons. It is an approval request that CARE
(the operator) must accept or reject."""
from odoo import api, fields, models, _


class CafmOffboardRequest(models.Model):
    _name = 'care.cafm.offboard.request'
    _description = 'طلب إنهاء التحاق عامل'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='الرقم', copy=False, readonly=True, default=lambda s: _('جديد'))
    request_type = fields.Selection([
        ('onboard', 'طلب التحاق'),
        ('offboard', 'طلب إنهاء التحاق'),
    ], string='نوع الطلب', default='offboard', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='العامل', required=True, tracking=True)
    job_title = fields.Char(related='employee_id.job_title', string='المسمّى الحالي', readonly=True)
    job_requested = fields.Char(string='الوظيفة المطلوبة', tracking=True,
                                help='الوظيفة المطلوب التحاق العامل بها (لطلب الالتحاق).')
    start_date = fields.Date(string='تاريخ بداية الالتحاق', tracking=True)
    end_date = fields.Date(string='تاريخ نهاية الالتحاق', tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', tracking=True)
    partner_id = fields.Many2one('res.partner', string='العميل', tracking=True)
    requested_by = fields.Many2one('res.users', string='مقدّم الطلب', default=lambda s: s.env.user, tracking=True)
    request_date = fields.Datetime(string='تاريخ الطلب', default=fields.Datetime.now, tracking=True)
    reason = fields.Text(string='الأسباب / ملاحظات', tracking=True)
    state = fields.Selection([
        ('pending', 'بانتظار موافقة CARE'),
        ('approved', 'مقبول'),
        ('rejected', 'مرفوض'),
    ], string='الحالة', default='pending', tracking=True, index=True)
    decision_by = fields.Many2one('res.users', string='القرار بواسطة', readonly=True)
    decision_date = fields.Datetime(string='تاريخ القرار', readonly=True)
    decision_note = fields.Text(string='ملاحظة القرار')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', _('جديد')) in (_('جديد'), 'New', '/', False):
                code = 'care.cafm.onboard.request' if v.get('request_type') == 'onboard' else 'care.cafm.offboard.request'
                v['name'] = self.env['ir.sequence'].next_by_code(code) or '/'
        recs = super().create(vals_list)
        for r in recs:
            lbl = _('طلب التحاق') if r.request_type == 'onboard' else _('طلب إنهاء التحاق')
            r.message_post(body=_('%s — %s — بانتظار موافقة CARE.') % (lbl, r.employee_id.name or ''))
        return recs

    def action_approve(self):
        for r in self:
            r.write({'state': 'approved', 'decision_by': self.env.user.id,
                     'decision_date': fields.Datetime.now()})
            r.message_post(body=_('✅ وافقت CARE على الطلب.'))

    def action_reject(self):
        for r in self:
            r.write({'state': 'rejected', 'decision_by': self.env.user.id,
                     'decision_date': fields.Datetime.now()})
            r.message_post(body=_('⛔ رفضت CARE الطلب.'))
