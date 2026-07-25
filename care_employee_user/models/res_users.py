# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    # When set, this user may open the Project Management app even if they are a
    # portal / public (non-internal) user. Honoured by the mobile `interfaces`.
    pms_app_user = fields.Boolean(
        string='مستخدم إدارة المشاريع',
        help='يسمح لهذا المستخدم (حتى لو كان بورتال/عام) بالدخول إلى تطبيق إدارة المشاريع.')
