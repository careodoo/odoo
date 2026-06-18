from odoo import api, fields, models, _


class SecurityEquipment(models.Model):
    _name = 'security.equipment'
    _description = 'Security Equipment'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    category = fields.Selection([
        ('communication', 'Communication'),
        ('weapon', 'Weapon'),
        ('protective', 'Protective Gear'),
        ('surveillance', 'Surveillance'),
        ('vehicle', 'Vehicle'),
        ('other', 'Other')
    ], string='Category', default='other')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    
    # Inventory tracking
    quantity = fields.Integer(string='Available Quantity', default=1)
    serial_number = fields.Char(string='Serial Number')
    purchase_date = fields.Date(string='Purchase Date')
    expiry_date = fields.Date(string='Expiry Date')
    
    # Maintenance
    last_maintenance_date = fields.Date(string='Last Maintenance')
    next_maintenance_date = fields.Date(string='Next Maintenance')
    maintenance_notes = fields.Text(string='Maintenance Notes')
    
    # Assignment
    is_assigned = fields.Boolean(string='Currently Assigned', compute='_compute_is_assigned', store=True)
    assigned_employee_id = fields.Many2one('security.employee', string='Assigned To')
    assignment_date = fields.Date(string='Assignment Date')
    
    @api.depends('assigned_employee_id')
    def _compute_is_assigned(self):
        for equipment in self:
            equipment.is_assigned = bool(equipment.assigned_employee_id)
    
    def action_assign(self):
        return {
            'name': _('Assign Equipment'),
            'type': 'ir.actions.act_window',
            'res_model': 'security.equipment.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_equipment_id': self.id},
        }
    
    def action_unassign(self):
        self.write({
            'assigned_employee_id': False,
            'assignment_date': False,
            'is_assigned': False
        })
