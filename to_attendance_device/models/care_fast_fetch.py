# -*- coding: utf-8 -*-
"""Performance override for the ZKTeco attendance download.

The vendor `attendance.device._fetch_attendance_data` deduplicates downloaded
punches with an O(n^2) loop (`duplicate_attends.filtered_domain(...)` per
record). On devices that accumulate tens/hundreds of thousands of records this
never finishes, and because the server runs with `max_cron_threads = 1` a single
stuck download silently starves EVERY scheduled job (it froze all crons for
days). This override replaces the dedup with an O(n) set-based check and a
chunked bulk insert -- the same approach proven during the 16-month backfill.
"""
import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class AttendanceDevice(models.Model):
    _inherit = 'attendance.device'

    def _fetch_attendance_data(self, attendance_data_icloud=None):
        # iCloud/ADMS devices keep the vendor path (push-based, different flow).
        icloud = self.filtered(lambda r: r.protocol == 'icloud')
        if icloud:
            super(AttendanceDevice, icloud)._fetch_attendance_data(attendance_data_icloud)
        for r in (self - icloud):
            try:
                r._care_fast_fetch_one()
            except Exception as e:
                # never let one device abort the whole (threaded) cron run
                _logger.warning("Fast attendance fetch failed for %s: %s", r.display_name, e)
        return True

    def _care_fast_fetch_one(self):
        self.ensure_one()
        r = self
        if r.map_before_dl:
            r._employee_map()
        states = {sl.attendance_state_id.code: sl.attendance_state_id.id
                  for sl in r.attendance_device_state_line_ids}

        att = r.getAttendance()  # hardened connect(); evicts poisoned cache on failure

        # device user_id (string) -> attendance.device.user.id
        self.env.cr.execute(
            "SELECT id, user_id FROM attendance_device_user WHERE device_id=%s", (r.id,))
        au_by_uid = {str(uid): adu_id for adu_id, uid in self.env.cr.fetchall()}

        # existing (au_id, timestamp) keys for O(1) dedup
        self.env.cr.execute(
            "SELECT user_id, timestamp FROM user_attendance WHERE device_id=%s", (r.id,))
        existing = set(self.env.cr.fetchall())

        rows = []
        for a in att:
            auid = au_by_uid.get(str(a.user_id))
            if not auid:
                continue
            sid = states.get(a.punch)
            if not sid:
                continue
            ts = r.convert_local_to_utc(a.timestamp, r.tz, naive=True)
            key = (auid, ts)
            if key in existing:
                continue
            existing.add(key)
            rows.append({
                'device_id': r.id, 'user_id': auid, 'timestamp': ts,
                'status': a.punch, 'attendance_state_id': sid,
            })

        UA = self.env['user.attendance']
        for i in range(0, len(rows), 5000):
            UA.create(rows[i:i + 5000])

        r.last_attendance_download = fields.Datetime.now()
        if r.auto_clear_attendance and r.auto_clear_attendance_schedule == 'on_download_complete':
            r._attendance_clear()
