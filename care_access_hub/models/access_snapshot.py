# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CareAccessSnapshot(models.Model):
    """لقطة قابلة للعكس من إسناد المستخدمين↔المجموعات — شبكة أمان الترحيل.
    إنشاء اللقطة آمن تمامًا (قراءة + تخزين). الاستعادة تُعيد الوضع المحفوظ (rollback)."""
    _name = 'care.access.snapshot'
    _description = 'لقطة صلاحيات (نسخة احتياطية)'
    _order = 'create_date desc'

    name = fields.Char(string='اللقطة', required=True, default=lambda s: _('لقطة %s') % fields.Datetime.now())
    snapshot_date = fields.Datetime(string='التاريخ', default=fields.Datetime.now, readonly=True)
    note = fields.Char(string='ملاحظة')
    line_ids = fields.One2many('care.access.snapshot.line', 'snapshot_id', string='السطور')
    user_count = fields.Integer(string='المستخدمون', compute='_compute_stats', store=True)
    group_total = fields.Integer(string='إجمالي الإسنادات', compute='_compute_stats', store=True)
    restored = fields.Boolean(string='استُعيدت', readonly=True, copy=False)

    @api.depends('line_ids')
    def _compute_stats(self):
        for r in self:
            r.user_count = len(r.line_ids)
            r.group_total = sum(len(l.group_ids) for l in r.line_ids)

    @api.model
    def action_take_snapshot(self, internal_only=True):
        """ينشئ لقطة لكل المستخدمين الداخليين (آمن: قراءة فقط ثم تخزين)."""
        dom = [('share', '=', False)] if internal_only else []
        users = self.env['res.users'].sudo().search(dom)
        snap = self.create({'name': _('لقطة %s') % fields.Datetime.now(),
                            'note': _('%s مستخدمًا داخليًّا') % len(users)})
        self.env['care.access.snapshot.line'].create([{
            'snapshot_id': snap.id, 'user_id': u.id,
            'group_ids': [(6, 0, u.groups_id.ids)],
        } for u in users])
        return snap

    def action_restore(self):
        """استعادة الوضع المحفوظ — rollback آمن (خاص بمدير المنظومة)."""
        self.ensure_one()
        if not self.env.user.has_group('care_access_hub.group_access_manager') \
                and not self.env.user.has_group('base.group_system'):
            raise UserError(_('الاستعادة خاصّة بمدير منظومة الصلاحيات.'))
        for l in self.line_ids:
            if l.user_id:
                l.user_id.sudo().write({'groups_id': [(6, 0, l.group_ids.ids)]})
        self.restored = True
        self.env['care.access.audit'].sudo().log(
            'restore', _('استُعيدت اللقطة %s (%s مستخدمًا)') % (self.name, len(self.line_ids)))
        return True


class CareAccessSnapshotLine(models.Model):
    _name = 'care.access.snapshot.line'
    _description = 'سطر لقطة صلاحيات'

    snapshot_id = fields.Many2one('care.access.snapshot', ondelete='cascade', required=True)
    user_id = fields.Many2one('res.users', string='المستخدم', required=True)
    group_ids = fields.Many2many('res.groups', string='المجموعات وقت اللقطة')
    group_count = fields.Integer(string='عدد المجموعات', compute='_compute_gc', store=True)

    @api.depends('group_ids')
    def _compute_gc(self):
        for l in self:
            l.group_count = len(l.group_ids)


class CareAccessAudit(models.Model):
    """سجلّ تدقيق (الفكرة ah_audit): كل تغيير صلاحية/ترحيل يُسجَّل — غير قابل للحذف."""
    _name = 'care.access.audit'
    _description = 'سجلّ تدقيق الصلاحيات'
    _order = 'create_date desc'

    name = fields.Char(string='الحدث', required=True)
    action_type = fields.Char(string='النوع')
    user_id = fields.Many2one('res.users', string='بواسطة', default=lambda s: s.env.user, readonly=True)
    detail = fields.Text(string='التفاصيل')

    @api.model
    def log(self, action_type, detail, name=None):
        if not (self.env.company.ah_audit if 'ah_audit' in self.env.company._fields else True):
            return False
        return self.sudo().create({'name': name or detail[:60], 'action_type': action_type, 'detail': detail})

    def unlink(self):
        raise UserError(_('سجلّ التدقيق غير قابل للحذف.'))
