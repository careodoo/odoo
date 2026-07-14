# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CareDmsDocument(models.Model):
    """A stored/archived document with classification, versioning, access
    scope, retention deadline, legal hold and documented disposal (mockup 90)."""
    _name = 'care.dms.document'
    _description = 'DMS Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='عنوان الوثيقة', required=True, tracking=True)
    reference = fields.Char(string='المرجع', default='/', copy=False, readonly=True)
    category_id = fields.Many2one('care.dms.category', string='التصنيف',
                                  required=True, tracking=True, index=True)
    attachment = fields.Binary(string='الملف', attachment=True)
    attachment_name = fields.Char(string='اسم الملف')
    version = fields.Integer(string='الإصدار', default=1, readonly=True, tracking=True)
    previous_version_id = fields.Many2one('care.dms.document', string='الإصدار السابق', readonly=True)
    is_current = fields.Boolean(string='الإصدار الحالي', default=True, tracking=True)

    employee_id = fields.Many2one('hr.employee', string='الموظف', tracking=True)
    department_id = fields.Many2one('hr.department', string='القسم')
    owner_id = fields.Many2one('res.users', string='المسؤول',
                               default=lambda self: self.env.user, tracking=True)

    issue_date = fields.Date(string='تاريخ الوثيقة', default=fields.Date.context_today, tracking=True)
    retention_until = fields.Date(string='تُحفظ حتى', compute='_compute_retention',
                                  store=True, tracking=True)
    legal_hold = fields.Boolean(string='تحت حجز قانوني', tracking=True)
    legal_hold_reason = fields.Char(string='سبب الحجز')
    disposed = fields.Boolean(string='أُتلفت', readonly=True, tracking=True)
    disposal_date = fields.Date(string='تاريخ الإتلاف', readonly=True)

    state = fields.Selection([
        ('active', 'فعّالة'),
        ('expiring', 'تقترب من الإتلاف'),
        ('due_disposal', 'مستحقة الإتلاف'),
        ('legal_hold', 'محجوزة قانونياً'),
        ('disposed', 'مُتلفة'),
    ], string='الحالة', default='active', readonly=True, tracking=True, index=True)
    note = fields.Text(string='ملاحظات')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('issue_date', 'category_id.retention_years')
    def _compute_retention(self):
        for rec in self:
            years = rec.category_id.retention_years or 0
            if rec.issue_date and years > 0:
                rec.retention_until = rec.issue_date + relativedelta(years=years)
            else:
                rec.retention_until = False

    def _eval_state(self):
        """Return the correct state for this record given today's date."""
        self.ensure_one()
        if self.disposed:
            return 'disposed'
        if self.legal_hold:
            return 'legal_hold'
        today = fields.Date.today()
        if self.retention_until:
            if self.retention_until < today:
                return 'due_disposal'
            if (self.retention_until - today).days <= 30:
                return 'expiring'
        return 'active'

    def _sync_state(self):
        for rec in self:
            new = rec._eval_state()
            if rec.state != new:
                rec.state = new

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', '/') == '/':
                vals['reference'] = self.env['ir.sequence'].next_by_code('care.dms.document') or '/'
        recs = super().create(vals_list)
        recs._sync_state()
        return recs

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('dms_skip_sync'):
            watched = {'issue_date', 'category_id', 'legal_hold', 'disposed', 'retention_until'}
            if watched & set(vals):
                self.with_context(dms_skip_sync=True)._sync_state()
        return res

    # --- actions ---
    def action_toggle_legal_hold(self):
        for rec in self:
            rec.legal_hold = not rec.legal_hold

    def action_dispose(self):
        for rec in self:
            if rec.disposed:
                continue
            if rec.legal_hold:
                raise UserError(_('لا يمكن الإتلاف: الوثيقة تحت حجز قانوني.'))
            if not rec.retention_until or rec.retention_until >= fields.Date.today():
                raise UserError(_('لا يمكن الإتلاف قبل انتهاء مدة الاحتفاظ.'))
            rec.write({
                'disposed': True,
                'disposal_date': fields.Date.today(),
            })
            rec.message_post(body=_('تم الإتلاف بأثر موثّق بواسطة %s.') % self.env.user.name)

    def action_new_version(self):
        """Supersede this document with a new version (kept in the chain)."""
        self.ensure_one()
        new = self.copy({
            'version': self.version + 1,
            'previous_version_id': self.id,
            'reference': '/',
            'issue_date': fields.Date.context_today(self),
            'attachment': False, 'attachment_name': False,
            'disposed': False, 'disposal_date': False,
        })
        self.with_context(dms_skip_sync=True).write({'is_current': False})
        return {
            'type': 'ir.actions.act_window', 'name': _('إصدار جديد'),
            'res_model': 'care.dms.document', 'res_id': new.id,
            'view_mode': 'form', 'target': 'current',
        }

    @api.model
    def _cron_refresh_state(self):
        """Daily: move documents across active→expiring→due_disposal as time
        passes (legal hold and disposed are respected by _eval_state)."""
        self.search([('disposed', '=', False)])._sync_state()
