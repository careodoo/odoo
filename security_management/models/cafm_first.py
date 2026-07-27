# -*- coding: utf-8 -*-
"""جعل خدمة الأمن «تعمل من داخل إدارة المرافق أولاً»:
1) فتح الوردية للحارس يعتمد على مرافق فرقه الأمنية (لا أوامر العمل فقط).
2) البلاغ الأمني يُختار موقعه من مرافق CAFM مباشرةً، ويُضبط الموقع الأمني القديم
   تلقائياً خلف الكواليس (توافقاً مع بقية المكدس والتطبيق)."""
from odoo import api, fields, models, _


class CafmShiftSecurity(models.Model):
    """توسيع مرشّحي فتح الوردية ليشمل مرافق فِرَق الأمن — لأن الحارس يُربط بفريق
    (security.team) لا بأمر عمل، فبدون هذا يبقى دائماً «خارج النطاق»."""
    _inherit = 'care.cafm.shift'

    @api.model
    def _candidate_facilities(self, employee):
        facs = super()._candidate_facilities(employee)
        if 'security.employee' not in self.env:
            return facs
        se = self.env['security.employee'].sudo().search(
            [('employee_id', '=', employee.id)], limit=1)
        if not se:
            return facs
        teams = se.team_ids if 'team_ids' in se._fields else se.browse()
        # طبقة الحرّاس (security.guard) هي المعبّأة فعلياً عند الإضافة من واجهة الفريق
        if 'security.guard' in self.env:
            G = self.env['security.guard'].sudo()
            guards = G.search([('security_employee_id', '=', se.id)])
            if 'security_employee_team_ids' in G._fields:
                teams |= guards.mapped('security_employee_team_ids')
        prem = teams.mapped('premise_id') if teams else None
        if prem:
            facs |= prem.mapped('cafm_facility_id')
        return facs


class SecurityIncidentCafmFirst(models.Model):
    """اختيار موقع البلاغ من مرافق إدارة المرافق مباشرةً بدل قائمة المواقع القديمة."""
    _inherit = 'security.incident.report'

    cafm_facility_id = fields.Many2one(
        'care.cafm.facility', string='موقع إدارة المرافق',
        help='اختر الموقع من نظام إدارة المرافق؛ يُضبط الموقع الأمني تلقائياً.')

    @api.onchange('cafm_facility_id')
    def _onchange_cafm_facility_id(self):
        """عند اختيار مرفق CAFM، اضبط الموقع الأمني المقابل (المجسور) إن وُجد."""
        if self.cafm_facility_id:
            prem = self.env['security.premise'].sudo().search(
                [('cafm_facility_id', '=', self.cafm_facility_id.id)], limit=1)
            if prem:
                self.premise_id = prem.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # لو أتى المرفق من CAFM دون موقع أمني، اربط الموقع المجسور تلقائياً
            if vals.get('cafm_facility_id') and not vals.get('premise_id'):
                prem = self.env['security.premise'].sudo().search(
                    [('cafm_facility_id', '=', vals['cafm_facility_id'])], limit=1)
                if prem:
                    vals['premise_id'] = prem.id
            # وبالعكس: اعرض مرفق CAFM على البلاغ القادم من الموقع الأمني
            elif vals.get('premise_id') and not vals.get('cafm_facility_id'):
                prem = self.env['security.premise'].sudo().browse(vals['premise_id'])
                if prem.exists() and prem.cafm_facility_id:
                    vals['cafm_facility_id'] = prem.cafm_facility_id.id
        return super().create(vals_list)
