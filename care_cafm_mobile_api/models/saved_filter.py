# -*- coding: utf-8 -*-
from odoo import fields, models


class CarePmsSavedFilter(models.Model):
    """A user's saved worker/record filter (a named set of search terms) for a
    project section, so a filtered list can be recalled with one tap."""
    _name = 'care.pms.saved.filter'
    _description = 'قائمة/فلتر محفوظ'
    _order = 'name'

    name = fields.Char(string='الاسم', required=True)
    user_id = fields.Many2one('res.users', string='المستخدم', required=True,
                              default=lambda s: s.env.user, index=True, ondelete='cascade')
    project_id = fields.Many2one('project.project', string='المشروع', index=True, ondelete='cascade')
    section_code = fields.Char(string='القسم', index=True)
    terms = fields.Char(string='الكلمات', help='كلمات البحث المثبّتة مفصولة بفاصلة.')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
