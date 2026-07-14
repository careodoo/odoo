# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from dateutil.relativedelta import relativedelta


class CareManpowerFile(models.Model):
    """Social Contract / Manpower File opened at the Public Authority for
    Manpower (PAM) or Social Affairs. Iqamas & work permits are registered
    against these files, and each file carries a visa quota.
    """
    _name = 'care.manpower.file'
    _description = 'Manpower File (Social Contract / PAM)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='File Number', required=True, tracking=True)
    authority = fields.Selection([
        ('pam', 'Public Authority for Manpower'),
        ('social', 'Social Affairs'),
        ('other', 'Other'),
    ], string='Authority', default='pam', required=True, tracking=True)
    activity = fields.Char(string='Activity / Sector', tracking=True)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True)

    quota = fields.Integer(string='Visa Quota', tracking=True,
                           help='Total work permits / visas allowed on this file.')
    used_count = fields.Integer(string='Used', compute='_compute_usage', store=True)
    available_count = fields.Integer(string='Available', compute='_compute_usage', store=True)
    utilization = fields.Float(string='Utilization %', compute='_compute_usage', store=True,
                               group_operator='avg')

    open_date = fields.Date(string='Open Date', tracking=True)
    renewal_date = fields.Date(string='File Renewal/Expiry', tracking=True)
    days_to_renewal = fields.Integer(string='Days to Renewal', compute='_compute_renewal')

    employee_ids = fields.One2many('hr.employee', 'manpower_file_id', string='Registered Workers')
    state = fields.Selection([
        ('ok', 'Available'),
        ('high', 'Near Full'),
        ('full', 'Full'),
    ], string='Quota Status', compute='_compute_usage', store=True)
    active = fields.Boolean(default=True)
    note = fields.Text(string='Notes')

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'File number must be unique per company.'),
    ]

    @api.depends('quota', 'employee_ids', 'employee_ids.active')
    def _compute_usage(self):
        for rec in self:
            used = len(rec.employee_ids.filtered('active'))
            rec.used_count = used
            rec.available_count = max(0, (rec.quota or 0) - used)
            rec.utilization = (used / rec.quota * 100.0) if rec.quota else 0.0
            if rec.quota and used >= rec.quota:
                rec.state = 'full'
            elif rec.quota and rec.utilization >= 90.0:
                rec.state = 'high'
            else:
                rec.state = 'ok'

    @api.depends('renewal_date')
    def _compute_renewal(self):
        today = fields.Date.today()
        for rec in self:
            rec.days_to_renewal = (rec.renewal_date - today).days if rec.renewal_date else 0

    def action_view_workers(self):
        self.ensure_one()
        return {
            'name': _('Registered Workers'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'domain': [('manpower_file_id', '=', self.id)],
            'context': {'default_manpower_file_id': self.id},
        }

    @api.model
    def get_manpower_stats(self):
        """Dashboard statistics for Manpower Files / visa quota."""
        files = self.search([])
        total_quota = sum(files.mapped('quota'))
        used = sum(files.mapped('used_count'))
        today = fields.Date.today()
        soon = today + relativedelta(days=60)
        expiring = files.filtered(
            lambda f: f.renewal_date and today <= f.renewal_date <= soon)
        return {
            'files': len(files),
            'total_quota': total_quota,
            'used': used,
            'available': max(0, total_quota - used),
            'utilization': round(used / total_quota * 100.0, 1) if total_quota else 0.0,
            'full_files': len(files.filtered(lambda f: f.state == 'full')),
            'expiring_files': len(expiring),
        }
