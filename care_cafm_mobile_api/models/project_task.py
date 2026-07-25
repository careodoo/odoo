# -*- coding: utf-8 -*-
"""Task commitment flag.

When a task is raised, the requester states whether it carries a firm execution
deadline commitment or is open-ended — surfaced and captured natively in the app.
"""
from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    x_time_committed = fields.Boolean(
        string='ملتزم بوقت التنفيذ', tracking=True,
        help='هل لهذه المهمة التزام بموعد تنفيذ محدّد؟')
