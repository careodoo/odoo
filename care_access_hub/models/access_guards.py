# -*- coding: utf-8 -*-
# «الجاردات والقيود»: لوحة موحّدة احترافية لمدير الصلاحيات — تفعيل/تعطيل الحُرّاس (ah_*)
# ورؤية القيود النشطة (أقنعة الحقول، حدود المبالغ، الصلاحيات المؤقّتة، التفويضات) + قفزات سريعة لإدارتها.
from odoo import api, fields, models, _


class CareAccessGuards(models.TransientModel):
    _name = 'care.access.guards'
    _description = 'لوحة الجاردات والقيود'

    company_id = fields.Many2one('res.company', string='الشركة',
                                 default=lambda s: s.env.company, required=True)

    # ===== الحُرّاس (مرتبطة بالشركة — قابلة للتعديل) =====
    ah_sod = fields.Boolean(related='company_id.ah_sod', readonly=False,
                            string='فصل الواجبات (SoD)')
    ah_thresholds = fields.Boolean(related='company_id.ah_thresholds', readonly=False,
                                   string='حدود مبالغ الاعتماد')
    ah_delegation = fields.Boolean(related='company_id.ah_delegation', readonly=False,
                                   string='التفويض المؤقّت (الإنابة)')
    ah_field_mask = fields.Boolean(related='company_id.ah_field_mask', readonly=False,
                                   string='إخفاء الحقول الحسّاسة')
    ah_simulator = fields.Boolean(related='company_id.ah_simulator', readonly=False,
                                  string='محاكي الصلاحيات')
    ah_auto_scope = fields.Boolean(related='company_id.ah_auto_scope', readonly=False,
                                   string='نطاق البيانات التلقائي')
    ah_audit = fields.Boolean(related='company_id.ah_audit', readonly=False,
                              string='سجلّ تدقيق كامل')
    ah_odoo_sync = fields.Boolean(related='company_id.ah_odoo_sync', readonly=False,
                                  string='مزامنة أودو التلقائية')
    ah_emergency = fields.Boolean(related='company_id.ah_emergency', readonly=False,
                                  string='صلاحية الطوارئ (Break-glass)')
    ah_heatmap = fields.Boolean(related='company_id.ah_heatmap', readonly=False,
                                string='الخريطة الحرارية للاعتماد')
    ah_bulk_assign = fields.Boolean(related='company_id.ah_bulk_assign', readonly=False,
                                    string='الإسناد الجماعي بالمسمّى')
    ah_temp_grant = fields.Boolean(related='company_id.ah_temp_grant', readonly=False,
                                   string='صلاحيات مؤقّتة بتاريخ انتهاء')
    ah_stage_approval = fields.Boolean(related='company_id.ah_stage_approval', readonly=False,
                                       string='الاعتماد بمرحلة محدّدة')
    ah_multi_approver = fields.Boolean(related='company_id.ah_multi_approver', readonly=False,
                                       string='عدّة معتمِدين لكل مرحلة')
    ah_notify_prefs = fields.Boolean(related='company_id.ah_notify_prefs', readonly=False,
                                     string='لوحة إشعارات الموظف')

    # ===== عدّادات القيود النشطة (للعرض + القفز) =====
    mask_count = fields.Integer(string='حقول مقنّعة', compute='_compute_counts')
    threshold_count = fields.Integer(string='حدود مبالغ مُفعّلة', compute='_compute_counts')
    temp_active_count = fields.Integer(string='صلاحيات مؤقّتة نشطة', compute='_compute_counts')
    emergency_active_count = fields.Integer(string='صلاحيات طوارئ نشطة', compute='_compute_counts')
    deleg_active_count = fields.Integer(string='تفويضات نشطة', compute='_compute_counts')
    role_count = fields.Integer(string='المسمّيات', compute='_compute_counts')

    @api.depends('company_id')
    def _compute_counts(self):
        Mask = self.env['care.role.field.mask'].sudo()
        Stage = self.env['care.approval.stage'].sudo()
        Req = self.env['care.access.request'].sudo()
        Deleg = self.env['care.user.delegation'].sudo()
        Role = self.env['care.job.role'].sudo()
        for w in self:
            w.mask_count = Mask.search_count([('hidden', '=', True)])
            w.threshold_count = Stage.search_count([('amount_threshold', '>', 0)])
            w.temp_active_count = Req.search_count([('state', '=', 'applied'),
                                                    ('duration_type', '=', 'temporary')])
            w.emergency_active_count = Req.search_count([('state', '=', 'applied'),
                                                         ('request_type', '=', 'emergency')])
            w.deleg_active_count = len(Deleg.search([]).filtered(lambda d: d.state == 'active'))
            w.role_count = Role.search_count([])

    # ===== قفزات سريعة =====
    def _act(self, name, model, domain=None, context=None):
        return {'type': 'ir.actions.act_window', 'name': name, 'res_model': model,
                'view_mode': 'tree,form', 'domain': domain or [], 'context': context or {},
                'target': 'current'}

    def open_masks(self):
        return self._act(_('الحقول المقنّعة'), 'care.role.field.mask', [('hidden', '=', True)])

    def open_thresholds(self):
        return self._act(_('حدود المبالغ'), 'care.approval.stage', [('amount_threshold', '>', 0)])

    def open_temp_grants(self):
        return self._act(_('الصلاحيات المؤقّتة النشطة'), 'care.access.request',
                         [('state', '=', 'applied'), ('duration_type', '=', 'temporary')])

    def open_delegations(self):
        return self._act(_('التفويضات'), 'care.user.delegation', [])

    def open_audit(self):
        return self._act(_('سجلّ التدقيق'), 'care.access.audit', [])

    @api.model
    def action_open(self):
        """يفتح اللوحة (سجلّ جديد لشركة المستخدم)."""
        w = self.create({})
        return {'type': 'ir.actions.act_window', 'name': _('الجاردات والقيود'),
                'res_model': self._name, 'res_id': w.id, 'view_mode': 'form',
                'views': [(False, 'form')], 'target': 'current'}
