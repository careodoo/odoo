# -*- coding: utf-8 -*-
# مزوّد بيانات console OWL لمنظومة الصلاحيات (واجهة مطابقة للموكاب).
from odoo import api, models, _

TIERS = [('exec', 'القيادة التنفيذية', 'C-Suite'), ('manager', 'مدراء الإدارات', 'Department Managers'),
         ('deputy', 'المساعدون والكبار', 'Deputies & Seniors'),
         ('officer', 'المسؤولون والموظفون', 'Officers & Staff'),
         ('field', 'الميدان (منطَّق بالمشاريع)', 'Field · Project-scoped')]


class CareAccessConsole(models.AbstractModel):
    _name = 'care.access.console'
    _description = 'مزوّد بيانات منظومة الصلاحيات (OWL)'

    @api.model
    def get_data(self):
        Role = self.env['care.job.role'].sudo()
        Line = self.env['care.role.model.perm'].sudo()
        Ch = self.env['care.access.notify.channel'].sudo()
        roles = Role.search([])
        # المسمّيات
        rdata = []
        for r in roles:
            rdata.append({
                'id': r.id, 'name': r.name, 'code': r.code, 'tier': r.tier,
                'scope': r.data_scope, 'readonly': r.is_readonly, 'approve': r.can_approve,
                'users': len(r.user_ids), 'groups': len(r.odoo_group_ids),
            })
        # المصفوفة لكل مسمّى {role_id: [{model,label,module,level,mask}]}
        matrix = {}
        for l in Line.search([], order='role_id, sequence'):
            matrix.setdefault(l.role_id.id, []).append({
                'id': l.id, 'model': l.model_name, 'label': l.model_label,
                'module': l.module, 'level': l.level, 'mask': l.mask_count,
            })
        # الإشعارات
        channels = [{'id': c.id, 'key': c.key, 'name': c.name, 'icon': c.icon,
                     'channel': c.channel, 'mandatory': c.mandatory}
                    for c in Ch.search([], order='sequence')]
        # KPIs
        internal = self.env['res.users'].sudo().search_count([('share', '=', False)])
        kpis = {
            'roles': len(roles),
            'approvals': len(channels),
            'models': len(set(Line.search([]).mapped('model_name'))),
            'notify_mandatory': Ch.search_count([('mandatory', '=', True)]),
        }
        # إحصاءات الترحيل (الفوضى الحالية)
        mig = {
            'groups': self.env['res.groups'].sudo().search_count([]),
            'acls': self.env['ir.model.access'].sudo().search_count([]),
            'rules': self.env['ir.rule'].sudo().search_count([]),
            'assigned': Role.search_count([('user_ids', '!=', False)]) and sum(len(r.user_ids) for r in roles),
            'internal': internal,
        }
        # مراحل الاعتماد (من care.approval.type إن وُجدت)
        atypes = []
        AT = self.env.get('care.approval.type')
        if AT is not None:
            for t in AT.sudo().search([]):
                atypes.append({
                    'id': t.id, 'name': t.name,
                    'stages': [{'name': s.name, 'label': s.approver_label or '',
                                'is_approval': s.is_approval} for s in t.stage_ids],
                })
        return {
            'tiers': [{'key': k, 'ar': ar, 'en': en} for k, ar, en in TIERS],
            'roles': rdata, 'matrix': matrix, 'channels': channels,
            'kpis': kpis, 'migrate': mig, 'atypes': atypes,
            'levels': [['0', '—'], ['1', 'قراءة'], ['2', 'قراءة+كتابة']],
        }

    @api.model
    def set_level(self, line_id, level):
        self.env['care.role.model.perm'].sudo().browse(int(line_id)).write({'level': str(level)})
        return True

    @api.model
    def set_channel(self, channel_id, channel):
        self.env['care.access.notify.channel'].sudo().browse(int(channel_id)).write({'channel': channel})
        return True

    @api.model
    def toggle_mandatory(self, channel_id):
        c = self.env['care.access.notify.channel'].sudo().browse(int(channel_id))
        c.mandatory = not c.mandatory
        return c.mandatory

    @api.model
    def derive_all(self):
        self.env['care.job.role'].sudo().cron_or_action_derive_all()
        return True

    @api.model
    def sync_channels(self):
        return self.env['care.access.notify.channel'].sudo().sync_from_registry()
