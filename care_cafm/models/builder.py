# -*- coding: utf-8 -*-
from odoo import fields, models


class CafmLocationGeometry(models.Model):
    """2D plan geometry for the CAD-style building builder — each location is a
    room drawn on its floor's grid (units = grid cells). Feeds the 3D view."""
    _inherit = 'care.cafm.location'

    plan_x = fields.Integer(string='س', default=0)
    plan_y = fields.Integer(string='ص', default=0)
    plan_w = fields.Integer(string='العرض', default=4)
    plan_h = fields.Integer(string='الطول', default=3)
    plan_color = fields.Char(string='اللون', default='#dbeafe')
    room_type = fields.Selection([
        ('office', 'مكتب'), ('corridor', 'ممر'), ('restroom', 'دورة مياه'),
        ('lobby', 'لوبي'), ('technical', 'غرفة فنية'), ('store', 'مخزن'),
        ('stairs', 'سلالم'), ('elevator', 'مصعد'), ('parking', 'موقف'),
        ('open', 'مساحة مفتوحة'), ('other', 'أخرى'),
    ], string='نوع الغرفة', default='office')


class CafmFloorGrid(models.Model):
    _inherit = 'care.cafm.floor'

    grid_cols = fields.Integer(string='أعمدة الشبكة', default=20)
    grid_rows = fields.Integer(string='صفوف الشبكة', default=14)
    plan_image_url = fields.Char(string='رابط مخطط الدور',
                                 help='مخطط الدور (صورة) يُرسم فوقه في مصمّم المبنى.')
