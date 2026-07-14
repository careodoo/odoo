# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CareAnnouncement(models.Model):
    """Company announcement / policy. Policies can require an electronic
    acknowledgment from the targeted workers (recorded as legal proof)."""
    _name = 'care.announcement'
    _description = 'Announcement / Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'publish_date desc, id desc'

    name = fields.Char(string='Title', required=True, tracking=True)
    body = fields.Html(string='Content')
    kind = fields.Selection([
        ('announcement', 'Announcement'),
        ('policy', 'Policy (requires acknowledgment)'),
    ], default='announcement', required=True, tracking=True)
    audience = fields.Selection([
        ('all', 'All Employees'),
        ('department', 'Specific Departments'),
    ], default='all', required=True)
    department_ids = fields.Many2many('hr.department', string='Departments')
    publish_date = fields.Date(tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ], default='draft', tracking=True)
    ack_ids = fields.One2many('care.announcement.ack', 'announcement_id', string='Acknowledgments')
    ack_required = fields.Integer(compute='_compute_ack_stats')
    ack_done = fields.Integer(compute='_compute_ack_stats')
    ack_pending = fields.Integer(compute='_compute_ack_stats')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('ack_ids.state')
    def _compute_ack_stats(self):
        for rec in self:
            rec.ack_required = len(rec.ack_ids)
            rec.ack_done = len(rec.ack_ids.filtered(lambda a: a.state == 'acked'))
            rec.ack_pending = rec.ack_required - rec.ack_done

    def _target_employees(self):
        self.ensure_one()
        domain = [('active', '=', True)]
        if self.audience == 'department' and self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        return self.env['hr.employee'].search(domain)

    def action_publish(self):
        for rec in self:
            rec.state = 'published'
            rec.publish_date = fields.Date.today()
            if rec.kind == 'policy':
                existing = rec.ack_ids.mapped('employee_id')
                to_add = rec._target_employees() - existing
                self.env['care.announcement.ack'].create([
                    {'announcement_id': rec.id, 'employee_id': e.id} for e in to_add])

    def action_archive_ann(self):
        self.write({'state': 'archived'})

    def action_reset(self):
        self.write({'state': 'draft'})


class CareAnnouncementAck(models.Model):
    _name = 'care.announcement.ack'
    _description = 'Announcement Acknowledgment'
    _order = 'announcement_id, employee_id'

    announcement_id = fields.Many2one('care.announcement', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    user_id = fields.Many2one(related='employee_id.user_id', store=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('acked', 'Acknowledged'),
    ], default='pending', required=True)
    ack_date = fields.Datetime(readonly=True)

    _sql_constraints = [
        ('uniq', 'unique(announcement_id, employee_id)', 'Already targeted.'),
    ]

    def action_acknowledge(self):
        for rec in self:
            rec.write({'state': 'acked', 'ack_date': fields.Datetime.now()})
