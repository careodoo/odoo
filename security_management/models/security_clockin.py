from odoo import api, fields, models, _
from datetime import datetime, timedelta


class SecurityClockin(models.Model):
    _name = 'security.clockin'
    _description = 'Security Clock-in'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('security.employee', string='Employee', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    clock_in = fields.Float(string='Clock In', required=True, default=lambda self: float(datetime.now().hour) + float(datetime.now().minute) / 60)
    clock_out = fields.Float(string='Clock Out')
    location_id = fields.Many2one('security.location', string='Location')
    premise_id = fields.Many2one('security.premise', string='Premise')
    shift_id = fields.Many2one('security.shift', string='Shift')
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('clocked_in', 'Clocked In'),
        ('clocked_out', 'Clocked Out'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.clockin') or _('New')
        return super(SecurityClockin, self).create(vals_list)
    
    def action_clock_in(self):
        self.write({
            'state': 'clocked_in',
            'clock_in': float(datetime.now().hour) + float(datetime.now().minute) / 60
        })
    
    def action_clock_out(self):
        self.write({
            'state': 'clocked_out',
            'clock_out': float(datetime.now().hour) + float(datetime.now().minute) / 60
        })
    
    def action_cancel(self):
        self.write({'state': 'cancelled'})
    
    def action_draft(self):
        self.write({'state': 'draft'})
