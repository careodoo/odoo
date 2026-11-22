# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class CareApprovalType(models.Model):
    """نوع اعتماد = موديل له سير عمل. المراحل تُقرأ من حقل الحالة الفعلي (ليست عشوائية)."""
    _name = 'care.approval.type'
    _description = 'نوع اعتماد'
    _order = 'sequence, id'

    name = fields.Char(string='النوع', required=True, translate=True)
    model_id = fields.Many2one('ir.model', string='الموديل', ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='الموديل (تقني)', store=True)
    state_field = fields.Char(string='حقل الحالة', default='state',
                              help='الحقل الذي تُقرأ منه المراحل الفعلية.')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    stage_ids = fields.One2many('care.approval.stage', 'type_id', string='المراحل')
    stage_count = fields.Integer(compute='_compute_sc')

    @api.depends('stage_ids')
    def _compute_sc(self):
        for r in self:
            r.stage_count = len(r.stage_ids)

    def action_sync_stages(self):
        """يقرأ مراحل الحالة الفعلية من الموديل (dry-run آمن — لا يمسّ البيانات)."""
        for r in self:
            if not r.model_name or r.model_name not in self.env:
                continue
            fld = self.env[r.model_name]._fields.get(r.state_field)
            if not fld:
                continue
            try:
                sel = fld.selection if isinstance(fld.selection, list) else fld._description_selection(self.env)
            except Exception:
                sel = []
            existing = {s.state_key: s for s in r.stage_ids}
            seq = 10
            for key, label in (sel or []):
                if key in existing:
                    existing[key].sequence = seq
                else:
                    self.env['care.approval.stage'].create({
                        'type_id': r.id, 'state_key': key, 'name': label, 'sequence': seq})
                seq += 10
        return True


class CareApprovalStage(models.Model):
    """مرحلة اعتماد: المسمّى المعتمِد (أو أكثر) + مستخدمون محدّدون (استثناء) + سقف + نمط."""
    _name = 'care.approval.stage'
    _description = 'مرحلة اعتماد'
    _order = 'type_id, sequence, id'

    type_id = fields.Many2one('care.approval.type', string='النوع', required=True, ondelete='cascade')
    name = fields.Char(string='المرحلة', required=True)
    state_key = fields.Char(string='مفتاح الحالة', help='قيمة حقل الحالة المقابلة لهذه المرحلة.')
    sequence = fields.Integer(default=10)
    is_approval = fields.Boolean(string='مرحلة اعتماد فعلية', default=True,
                                 help='ميّز المراحل التشغيلية (RFQ/Locked...) بإلغاء هذا.')

    # المعتمِدون بالمسمّى الوظيفي (الأساس)
    role_ids = fields.Many2many('care.job.role', 'care_stage_role_rel', 'stage_id', 'role_id',
                                string='المسمّيات المعتمِدة')
    # مستخدمون محدّدون من خارج المسمّيات (استثناء)
    extra_user_ids = fields.Many2many('res.users', 'care_stage_user_rel', 'stage_id', 'user_id',
                                      string='مستخدمون محدّدون (استثناء)')
    # شرط المبلغ (يُفعَّل عند تجاوز السقف)
    amount_threshold = fields.Float(string='سقف المبلغ (د.ك)',
                                    help='تنشط المرحلة فقط إذا تجاوز المبلغ هذا السقف.')
    mode = fields.Selection(
        [('any', 'أيّ واحد يكفي'), ('all', 'يتطلب موافقة الكل')],
        string='النمط', default='any', required=True)
    approver_label = fields.Char(string='المعتمِدون', compute='_compute_label')

    @api.depends('role_ids', 'extra_user_ids')
    def _compute_label(self):
        for r in self:
            parts = r.role_ids.mapped('name') + ['👤 ' + u.name for u in r.extra_user_ids]
            r.approver_label = ' · '.join(parts) or '—'
