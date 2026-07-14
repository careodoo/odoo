# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    performance_logged = fields.Boolean(default=False, copy=False, index=True)

    @api.model
    def cron_scan_attendance_performance(self):
        Log = self.env['care.performance.log']
        present_pts = Log._get_param('att_present')
        short_pts = Log._get_param('att_short')
        min_hours = Log._get_param('att_min_hours')
        ot_bonus = Log._get_param('att_overtime_bonus')
        atts = self.search([('performance_logged', '=', False),
                            ('check_out', '!=', False)], limit=5000)
        for att in atts:
            if not att.employee_id:
                att.performance_logged = True
                continue
            worked = att.worked_hours or 0.0
            if worked < min_hours:
                pts = short_pts
                label = _('Short day (%.1fh)') % worked
            else:
                pts = present_pts
                label = _('Full attendance')
            if att.overtime_hours and att.overtime_hours > 0:
                pts += ot_bonus
                label += _(' + overtime')
            Log.record_event(
                att.employee_id.id, pts, 'attendance', label,
                res_model='hr.attendance', res_id=att.id,
                date=att.check_in and att.check_in.date())
            att.performance_logged = True
        return True
