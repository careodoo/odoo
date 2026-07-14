# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields, models, api, _


class CareKiosk(models.Model):
    """A self-service kiosk terminal (mockup 54) placed at housing/site next to
    a ZK fingerprint device. A worker scans their finger on the device, which
    creates an hr.attendance punch stamped with that device; the kiosk page
    detects the fresh punch and opens that worker's session — no smartphone,
    no login, worker identified only by their own physical fingerprint scan."""
    _name = 'care.kiosk'
    _description = 'Worker Self-Service Kiosk'

    name = fields.Char(required=True, default='كشك العمال')
    device_id = fields.Many2one(
        'attendance.device', string='جهاز البصمة', required=True,
        help='الجهاز الذي يمسح العامل بصمته عليه للدخول على هذا الكشك.')
    scan_window_seconds = fields.Integer(
        string='نافذة التعرّف (ثانية)', default=15,
        help='أقصى مدة بين مسح البصمة وفتح الجلسة على الكشك.')
    timeout_seconds = fields.Integer(
        string='مهلة الجلسة (ثانية)', default=90,
        help='تُغلق الجلسة تلقائياً بعد هذه المدة من الخمول.')
    active = fields.Boolean(default=True)
    access_url = fields.Char(string='رابط الكشك', compute='_compute_access_url')

    def _compute_access_url(self):
        base = self.get_base_url()
        for rec in self:
            rec.access_url = '%s/care/kiosk/%s' % (base, rec.id) if rec.id else False

    def _find_scanned_employee(self):
        """Return the employee who scanned on this kiosk's device within the
        scan window (most recent punch). Runs as sudo; the identity is proven
        by the physical fingerprint scan on the device."""
        self.ensure_one()
        Att = self.env['hr.attendance'].sudo()
        now = fields.Datetime.now()
        window = now - timedelta(seconds=max(self.scan_window_seconds, 5))
        att = Att.search([
            '|', ('checkin_device_id', '=', self.device_id.id),
                 ('checkout_device_id', '=', self.device_id.id),
            '|', ('check_in', '>=', window), ('check_out', '>=', window),
        ], order='id desc', limit=1)
        return att.employee_id
