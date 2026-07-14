import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class AttendanceDeviceFtImportLine(models.Model):
    """One queued unit of work for the staged (background) finger template
    import: a single device user whose finger templates must be read from the
    machine.  The worker cron processes these in small, time-boxed batches so
    the import never blocks the server nor times out on slow/empty slots."""

    _name = 'attendance.device.ft.import.line'
    _description = 'Finger Template Import Queue Line'
    _order = 'sequence, id'

    device_id = fields.Many2one(
        'attendance.device', string='Attendance Machine',
        required=True, ondelete='cascade', index=True)
    device_user_id = fields.Many2one(
        'attendance.device.user', string='Machine User',
        required=True, ondelete='cascade')
    user_name = fields.Char(related='device_user_id.name', string='Name', store=True, readonly=True)
    uid = fields.Integer(string='UID', readonly=True)
    sequence = fields.Integer(string='Sequence', default=10)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('error', 'Error'),
        ('skipped', 'Skipped'),
    ], string='Status', default='pending', required=True, index=True)
    fingers_count = fields.Integer(string='Templates', readonly=True)
    message = fields.Char(string='Message', readonly=True)
    processed_on = fields.Datetime(string='Processed On', readonly=True)
