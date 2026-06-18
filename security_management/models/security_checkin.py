from odoo import api, fields, models, _
from datetime import datetime, timedelta


class SecurityCheckin(models.Model):
    _name = 'security.checkin'
    _description = 'Security Check-in'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('security.employee', string='Employee', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    time = fields.Float(string='Time', required=True, default=lambda self: float(datetime.now().hour) + float(datetime.now().minute) / 60)
    location_id = fields.Many2one('security.location', string='Location')
    premise_id = fields.Many2one('security.premise', string='Premise')
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.checkin') or _('New')
        return super(SecurityCheckin, self).create(vals_list)
    
    def action_confirm(self):
        self.write({'state': 'confirmed'})
    
    def action_cancel(self):
        self.write({'state': 'cancelled'})
    
    def action_draft(self):
        self.write({'state': 'draft'})
