# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CafmObservation(models.Model):
    """A quality/supervisor corrective note: location (by QR scan), a correction
    deadline, and an assignee — closed only with proof + re-inspection."""
    _name = 'care.cafm.observation'
    _description = 'CAFM Corrective Observation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    title = fields.Char(string='الملاحظة', required=True, tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع (بمسح QR)', tracking=True,
                                  domain="[('facility_id','=',facility_id)]")
    service_id = fields.Many2one('care.cafm.service', string='الخدمة', tracking=True)
    project_id = fields.Many2one(related='facility_id.project_id', store=True)
    description = fields.Text(string='الوصف')
    severity = fields.Selection([
        ('low', 'منخفضة'), ('medium', 'متوسطة'), ('high', 'عالية'), ('critical', 'حرجة'),
    ], string='الخطورة', default='medium', required=True, tracking=True)
    raised_by = fields.Many2one('res.users', string='رصدها', default=lambda s: s.env.user, tracking=True)
    assignee_id = fields.Many2one('hr.employee', string='مُسنَدة إلى (للتصحيح)', tracking=True)
    deadline = fields.Datetime(string='موعد التصحيح', tracking=True)
    state = fields.Selection([
        ('open', 'مفتوحة'), ('assigned', 'مُسنَدة'), ('fixing', 'قيد التصحيح'),
        ('reinspect', 'إعادة تفتيش'), ('closed', 'مغلقة'), ('cancelled', 'ملغاة'),
    ], default='open', tracking=True)
    workorder_id = fields.Many2one('care.cafm.workorder', string='أمر عمل مرتبط', readonly=True, copy=False)
    is_overdue = fields.Boolean(compute='_compute_overdue')
    closed_datetime = fields.Datetime(readonly=True, copy=False)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _compute_overdue(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_overdue = bool(rec.deadline and rec.deadline < now
                                  and rec.state not in ('closed', 'cancelled'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.cafm.observation') or '/'
        return super().create(vals_list)

    def action_assign(self):
        for rec in self:
            if not rec.assignee_id or not rec.deadline:
                raise UserError(_('حدّد المسؤول وموعد التصحيح أولاً.'))
            rec.state = 'assigned'
            if rec.assignee_id.user_id:
                rec.activity_schedule('mail.mail_activity_data_todo',
                                      summary=_('تصحيح ملاحظة: %s') % (rec.title or ''),
                                      date_deadline=rec.deadline and rec.deadline.date(),
                                      user_id=rec.assignee_id.user_id.id)

    def action_start_fix(self):
        self.write({'state': 'fixing'})

    def action_reinspect(self):
        self.write({'state': 'reinspect'})

    def action_close(self):
        self.write({'state': 'closed', 'closed_datetime': fields.Datetime.now()})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    @api.model
    def _cron_obs_escalate(self):
        """Alert on overdue corrective observations (deadline passed, not closed)."""
        now = fields.Datetime.now()
        overdue = self.search([('deadline', '!=', False), ('deadline', '<', now),
                               ('state', 'not in', ('closed', 'cancelled'))])
        for obs in overdue:
            if obs.state == 'assigned' or obs.state == 'open':
                obs.state = 'assigned'
            mgr = obs.assignee_id.parent_id.user_id if obs.assignee_id.parent_id else obs.raised_by
            if mgr and not obs.activity_ids.filtered(lambda a: 'تصعيد' in (a.summary or '')):
                obs.activity_schedule('mail.mail_activity_data_todo',
                                      summary=_('تصعيد ملاحظة متأخّرة: %s') % (obs.title or ''),
                                      user_id=mgr.id)
                obs.message_post(body=_('⏱ تجاوزت الملاحظة موعد التصحيح — تصعيد.'))

    def action_make_workorder(self):
        """Turn the observation into a work order for the assigned worker."""
        self.ensure_one()
        wo = self.env['care.cafm.workorder'].create({
            'title': self.title, 'facility_id': self.facility_id.id,
            'location_id': self.location_id.id, 'service_id': self.service_id.id,
            'wo_type': 'inspection', 'description': self.description,
            'employee_id': self.assignee_id.id,
            'priority': {'low': '0', 'medium': '1', 'high': '2', 'critical': '3'}.get(self.severity, '1'),
        })
        self.workorder_id = wo.id
        self.state = 'fixing'
        return {'type': 'ir.actions.act_window', 'res_model': 'care.cafm.workorder',
                'res_id': wo.id, 'view_mode': 'form'}
