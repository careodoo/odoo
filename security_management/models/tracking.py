from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SecurityTracking(models.Model):
    _name = 'security.tracking'
    _description = 'Security Tracking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'timestamp desc'
    
    name = fields.Char(string='Tracking Reference', readonly=True, copy=False)
    
    guard_id = fields.Many2one('security.guard', string='Guard', required=True, tracking=True)
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now, required=True)
    
    # Location data
    latitude = fields.Float(string='Latitude', digits=(16, 8))
    longitude = fields.Float(string='Longitude', digits=(16, 8))
    premise_id = fields.Many2one('security.premise', string='Nearest Premise')
    client_id = fields.Many2one(related='premise_id.client_id', string='Client', store=True)
    
    # Device info
    device_id = fields.Char(string='Device ID')
    battery_level = fields.Float(string='Battery Level (%)')
    
    # Status
    status = fields.Selection([
        ('on_duty', 'On Duty'),
        ('patrol', 'On Patrol'),
        ('break', 'On Break'),
        ('emergency', 'Emergency'),
        ('idle', 'Idle')
    ], string='Status', default='on_duty')
    
    notes = fields.Text(string='Notes')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.tracking')
                
            # Try to find nearest premise based on coordinates
            if vals.get('latitude') and vals.get('longitude') and not vals.get('premise_id'):
                nearest_premise = self._find_nearest_premise(vals.get('latitude'), vals.get('longitude'))
                if nearest_premise:
                    vals['premise_id'] = nearest_premise.id
                    
        return super().create(vals_list)
    
    def _find_nearest_premise(self, latitude, longitude):
        """Find the nearest premise based on coordinates"""
        # This is a simplified version - in reality, you would need to calculate distances
        # between the current point and all premises, then return the closest one
        # This would require premises to have latitude/longitude fields
        
        # For now, just return None
        return None