# -*- coding: utf-8 -*-
"""Task commitment flag.

When a task is raised, the requester states whether it carries a firm execution
deadline commitment or is open-ended — surfaced and captured natively in the app.
"""
from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    x_time_committed = fields.Boolean(
        string='ملتزم بوقت التنفيذ', tracking=True,
        help='هل لهذه المهمة التزام بموعد تنفيذ محدّد؟')

    # تاريخ إنشاء التاسك — قابل للتعديل (create_date حقل نظام للقراءة فقط، فنوفّر
    # حقلاً بديلاً يبدأ بتاريخ الإنشاء ويمكن تغييره).
    task_date = fields.Datetime(
        string='تاريخ إنشاء التاسك', default=fields.Datetime.now, tracking=True,
        help='تاريخ إنشاء التاسك — قابل للتعديل.')

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for r in recs:
            if not r.task_date:
                r.task_date = r.create_date
        return recs
