# -*- coding: utf-8 -*-
"""Portal / app section registry + per-client visibility.

A CAFM client should only see the sections that concern them. Waste transfer,
for example, is a standalone booked service with nothing to do with facilities —
a waste-only client should see *only* that. This registry lists every section
the app/portal can show; each client either inherits sections automatically from
the services actually delivered to them (``auto``) or is given an explicit
allow-list (``custom``). Adding a new ``care.cafm.portal.section`` record makes
it appear in the config screen automatically."""
from odoo import api, fields, models

# base sections every facilities client gets under 'auto' mode
BASE_AUTO = {'overview', 'facilities', 'workorders', 'inventory', 'shop', 'reports', 'team'}


class CafmPortalSection(models.Model):
    _name = 'care.cafm.portal.section'
    _description = 'قسم البوابة / التطبيق'
    _order = 'sequence, id'

    name = fields.Char(string='القسم', required=True, translate=True)
    code = fields.Char(string='الرمز', required=True,
                       help='معرّف ثابت يستخدمه التطبيق لإظهار/إخفاء القسم.')
    icon = fields.Char(string='الأيقونة', default='🧩')
    sequence = fields.Integer(default=10)
    service_type = fields.Selection(selection='_service_type_selection',
                                    string='نوع الخدمة المرتبط',
                                    help='إن كان القسم خدمةً، اربطه بنوعها ليظهر تلقائيًا لعملائها.')
    is_service = fields.Boolean(string='قسم خدمة', compute='_compute_is_service', store=True)
    always_on = fields.Boolean(string='ظاهر دائمًا',
                               help='يظهر لكل العملاء بغضّ النظر عن الخدمات (مثل نظرة عامة).')
    active = fields.Boolean(default=True)

    _sql_constraints = [('code_uniq', 'unique(code)', 'رمز القسم يجب أن يكون فريدًا.')]

    @api.model
    def _service_type_selection(self):
        return self.env['care.cafm.service']._fields['service_type'].selection

    @api.depends('service_type')
    def _compute_is_service(self):
        for s in self:
            s.is_service = bool(s.service_type)

    @api.model
    def auto_codes_for_types(self, service_types):
        """Codes visible in 'auto' mode for a client delivered these services."""
        codes = set(self.search([('always_on', '=', True)]).mapped('code')) | BASE_AUTO
        if service_types:
            svc = self.search([('service_type', 'in', list(service_types))])
            codes |= set(svc.mapped('code'))
        return codes
