# -*- coding: utf-8 -*-
# CARE: proactive health monitoring for biometric devices.
# A confirmed device refreshes `last_attendance_download` on every successful
# 30-min download (even with 0 new punches); the timestamp only freezes when the
# device becomes unreachable. So a stale timestamp is a reliable "device down"
# signal -- surfaced here as a badge on the device + a throttled alert to the
# technician, instead of being noticed days later.
import logging
from datetime import timedelta

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class AttendanceDevice(models.Model):
    _inherit = 'attendance.device'

    health_alert_hours = fields.Integer(
        string='Down Alert (hours)', default=3, tracking=True,
        help="Raise a 'device down' alert when no successful download has "
             "happened for this many hours. The download cron runs every 30 "
             "minutes, so 3h = 6 missed runs (a real outage, not a blip).")
    last_health_alert = fields.Datetime(string='Last Down Alert', readonly=True, copy=False)
    hours_since_download = fields.Float(
        string='Hours Since Last Sync', compute='_compute_health', store=False)
    is_stalled = fields.Boolean(
        string='Device Down', compute='_compute_health', store=False, search='_search_is_stalled')

    @api.depends('last_attendance_download', 'health_alert_hours', 'state')
    def _compute_health(self):
        now = fields.Datetime.now()
        for r in self:
            if r.state == 'confirmed' and r.last_attendance_download:
                delta = now - r.last_attendance_download
                r.hours_since_download = delta.total_seconds() / 3600.0
                r.is_stalled = r.hours_since_download >= (r.health_alert_hours or 3)
            elif r.state == 'confirmed' and not r.last_attendance_download:
                r.hours_since_download = 0.0
                r.is_stalled = True
            else:
                r.hours_since_download = 0.0
                r.is_stalled = False

    def _search_is_stalled(self, operator, value):
        # allow filtering stalled devices in list/search views
        devices = self.search([('state', '=', 'confirmed')])
        stalled_ids = devices.filtered('is_stalled').ids
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('id', 'in', stalled_ids)]
        return [('id', 'not in', stalled_ids)]

    def _health_alert_recipient_ids(self):
        """Who to notify: the device technician + the Attendance managers group."""
        self.ensure_one()
        users = self.user_id
        grp = self.env.ref('to_attendance_device.group_attendance_devices_manager', raise_if_not_found=False) \
            or self.env.ref('hr_attendance.group_hr_attendance_manager', raise_if_not_found=False)
        if grp:
            users |= grp.users.filtered(lambda u: u.company_id == self.company_id or self.company_id in u.company_ids)
        return users

    @api.model
    def _cron_device_health_alert(self):
        """Alert once per outage when a confirmed device stops downloading."""
        now = fields.Datetime.now()
        devices = self.search([('state', '=', 'confirmed'), ('protocol', '!=', 'icloud')])
        for dev in devices:
            if not dev.is_stalled:
                # recovered -> clear the throttle so the next outage alerts again
                if dev.last_health_alert:
                    dev.last_health_alert = False
                continue
            # throttle: don't re-alert more than once per 12h for the same outage
            if dev.last_health_alert and (now - dev.last_health_alert) < timedelta(hours=12):
                continue
            dev.last_health_alert = now
            if dev.last_attendance_download:
                since = _('%.1f hours ago (%s)') % (
                    dev.hours_since_download,
                    fields.Datetime.to_string(dev.last_attendance_download))
            else:
                since = _('never')
            body = _(
                "<p>⚠️ <b>Attendance device not responding</b></p>"
                "<ul>"
                "<li>Device: <b>%s</b></li>"
                "<li>IP: %s</li>"
                "<li>Last successful sync: <b>%s</b></li>"
                "</ul>"
                "<p>The device is unreachable — check power, network cable and IP on site.</p>"
            ) % (dev.display_name, dev.ip or _('n/a'), since)
            recipients = dev._health_alert_recipient_ids()
            dev.message_post(
                body=body,
                subject=_('Attendance device down: %s') % dev.display_name,
                partner_ids=recipients.partner_id.ids,
                message_type='notification',
                subtype_xmlid='mail.mt_comment')
            for u in recipients:
                dev.activity_schedule(
                    'mail.mail_activity_data_warning' if self.env.ref('mail.mail_activity_data_warning', raise_if_not_found=False) else 'mail.mail_activity_data_todo',
                    summary=_('Device down: %s') % dev.display_name,
                    note=_('No biometric data received for %.1f hours. Check the device on site.') % dev.hours_since_download,
                    user_id=u.id)
            _logger.warning("CARE health: device %s stalled (%.1fh since last sync)",
                            dev.display_name, dev.hours_since_download)
