from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SecurityGateCashDrawerCountWizard(models.TransientModel):
    _name = 'security.gate.cash.drawer.count.wizard'
    _description = 'Count Cash Drawer Wizard'
    
    cash_drawer_id = fields.Many2one('security.gate.cash.drawer', string='Cash Drawer', required=True)
    cashier_id = fields.Many2one('security.gate.cashier', string='Cashier', 
                               default=lambda self: self.env['security.gate.cashier'].search([
                                   ('user_id', '=', self.env.user.id),
                                   ('active', '=', True)
                               ], limit=1))
    count_date = fields.Datetime(string='Count Date', default=fields.Datetime.now, required=True)
    expected_amount = fields.Monetary(string='Expected Amount', related='cash_drawer_id.current_balance', readonly=True)
    company_id = fields.Many2one(
        'res.company',
        related='cash_drawer_id.company_id',
        string='Company',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency',
        related='company_id.currency_id', 
        readonly=True
    )
    
    # Denominations
    notes_200 = fields.Integer(string='200 Notes', default=0)
    notes_100 = fields.Integer(string='100 Notes', default=0)
    notes_50 = fields.Integer(string='50 Notes', default=0)
    notes_20 = fields.Integer(string='20 Notes', default=0)
    notes_10 = fields.Integer(string='10 Notes', default=0)
    notes_5 = fields.Integer(string='5 Notes', default=0)
    coins_2 = fields.Integer(string='2 Coins', default=0)
    coins_1 = fields.Integer(string='1 Coins', default=0)
    coins_05 = fields.Integer(string='0.5 Coins', default=0)
    coins_025 = fields.Integer(string='0.25 Coins', default=0)
    coins_01 = fields.Integer(string='0.1 Coins', default=0)
    coins_005 = fields.Integer(string='0.05 Coins', default=0)
    
    counted_amount = fields.Monetary(string='Counted Amount', compute='_compute_counted_amount')
    discrepancy = fields.Monetary(string='Discrepancy', compute='_compute_discrepancy')
    notes = fields.Text(string='Notes')
    
    @api.depends('notes_200', 'notes_100', 'notes_50', 'notes_20', 'notes_10', 'notes_5',
                'coins_2', 'coins_1', 'coins_05', 'coins_025', 'coins_01', 'coins_005')
    def _compute_counted_amount(self):
        for wizard in self:
            wizard.counted_amount = (
                wizard.notes_200 * 200 +
                wizard.notes_100 * 100 +
                wizard.notes_50 * 50 +
                wizard.notes_20 * 20 +
                wizard.notes_10 * 10 +
                wizard.notes_5 * 5 +
                wizard.coins_2 * 2 +
                wizard.coins_1 * 1 +
                wizard.coins_05 * 0.5 +
                wizard.coins_025 * 0.25 +
                wizard.coins_01 * 0.1 +
                wizard.coins_005 * 0.05
            )
    
    @api.depends('expected_amount', 'counted_amount')
    def _compute_discrepancy(self):
        for wizard in self:
            wizard.discrepancy = wizard.counted_amount - wizard.expected_amount
    
    def action_confirm_count(self):
        """Create a drawer count record and update the drawer balance"""
        self.ensure_one()
        
        if not self.cashier_id:
            raise UserError(_("Please select a cashier for this count."))
        
        # Create the count record
        count = self.env['security.gate.cash.drawer.count'].create({
            'cash_drawer_id': self.cash_drawer_id.id,
            'cashier_id': self.cashier_id.id,
            'count_date': self.count_date,
            'expected_amount': self.expected_amount,
            'counted_amount': self.counted_amount,
            'notes_200': self.notes_200,
            'notes_100': self.notes_100,
            'notes_50': self.notes_50,
            'notes_20': self.notes_20,
            'notes_10': self.notes_10,
            'notes_5': self.notes_5,
            'coins_2': self.coins_2,
            'coins_1': self.coins_1,
            'coins_05': self.coins_05,
            'coins_025': self.coins_025,
            'coins_01': self.coins_01,
            'coins_005': self.coins_005,
            'notes': self.notes,
        })
        
        # Confirm the count
        count.action_confirm()
        
        # Start the cashier's shift
        self.cashier_id.action_start_shift()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cash Drawer Count'),
                'message': _('Cash drawer count completed and shift started successfully.'),
                'sticky': False,
                'type': 'success',
                'close': True,
            }
        }


class SecurityGateCashierEndShiftWizard(models.TransientModel):
    _name = 'security.gate.cashier.end.shift.wizard'
    _description = 'End Cashier Shift Wizard'
    
    shift_id = fields.Many2one('security.gate.cashier.shift', string='Shift', required=True)
    cashier_id = fields.Many2one(related='shift_id.cashier_id', string='Cashier', readonly=True)
    cash_drawer_id = fields.Many2one('security.gate.cash.drawer', string='Cash Drawer', required=True)
    company_id = fields.Many2one(
        'res.company',
        related='cash_drawer_id.company_id',
        string='Company',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency',
        related='company_id.currency_id', 
        readonly=True
    )
    
    # Shift details
    start_time = fields.Datetime(related='shift_id.start_time', readonly=True)
    end_time = fields.Datetime(string='End Time', default=fields.Datetime.now, required=True)
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration')
    
    # Financial details
    starting_balance = fields.Monetary(related='shift_id.starting_balance', readonly=True)
    current_balance = fields.Monetary(string='Current Balance', required=True)
    transaction_count = fields.Integer(related='shift_id.transaction_count', readonly=True)
    transaction_total = fields.Monetary(related='shift_id.transaction_total', readonly=True)
    
    # Denominations for counting
    notes_200 = fields.Integer(string='200 Notes', default=0)
    notes_100 = fields.Integer(string='100 Notes', default=0)
    notes_50 = fields.Integer(string='50 Notes', default=0)
    notes_20 = fields.Integer(string='20 Notes', default=0)
    notes_10 = fields.Integer(string='10 Notes', default=0)
    notes_5 = fields.Integer(string='5 Notes', default=0)
    coins_2 = fields.Integer(string='2 Coins', default=0)
    coins_1 = fields.Integer(string='1 Coins', default=0)
    coins_05 = fields.Integer(string='0.5 Coins', default=0)
    coins_025 = fields.Integer(string='0.25 Coins', default=0)
    coins_01 = fields.Integer(string='0.1 Coins', default=0)
    coins_005 = fields.Integer(string='0.05 Coins', default=0)
    
    counted_amount = fields.Monetary(string='Counted Amount', compute='_compute_counted_amount')
    expected_balance = fields.Monetary(related='shift_id.expected_balance', readonly=True)
    discrepancy = fields.Monetary(string='Discrepancy', compute='_compute_discrepancy')
    
    notes = fields.Text(string='Notes')
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for wizard in self:
            if wizard.start_time and wizard.end_time:
                delta = wizard.end_time - wizard.start_time
                wizard.duration = delta.total_seconds() / 3600
            else:
                wizard.duration = 0
    
    @api.depends('notes_200', 'notes_100', 'notes_50', 'notes_20', 'notes_10', 'notes_5',
                'coins_2', 'coins_1', 'coins_05', 'coins_025', 'coins_01', 'coins_005')
    def _compute_counted_amount(self):
        for wizard in self:
            wizard.counted_amount = (
                wizard.notes_200 * 200 +
                wizard.notes_100 * 100 +
                wizard.notes_50 * 50 +
                wizard.notes_20 * 20 +
                wizard.notes_10 * 10 +
                wizard.notes_5 * 5 +
                wizard.coins_2 * 2 +
                wizard.coins_1 * 1 +
                wizard.coins_05 * 0.5 +
                wizard.coins_025 * 0.25 +
                wizard.coins_01 * 0.1 +
                wizard.coins_005 * 0.05
            )
    
    @api.depends('expected_balance', 'counted_amount')
    def _compute_discrepancy(self):
        for wizard in self:
            wizard.discrepancy = wizard.counted_amount - wizard.expected_balance
    
    def action_end_shift(self):
        """End the shift and create a drawer count"""
        self.ensure_one()
        
        # Create a drawer count
        count = self.env['security.gate.cash.drawer.count'].create({
            'cash_drawer_id': self.cash_drawer_id.id,
            'cashier_id': self.cashier_id.id,
            'count_date': self.end_time,
            'expected_amount': self.expected_balance,
            'counted_amount': self.counted_amount,
            'notes_200': self.notes_200,
            'notes_100': self.notes_100,
            'notes_50': self.notes_50,
            'notes_20': self.notes_20,
            'notes_10': self.notes_10,
            'notes_5': self.notes_5,
            'coins_2': self.coins_2,
            'coins_1': self.coins_1,
            'coins_05': self.coins_05,
            'coins_025': self.coins_025,
            'coins_01': self.coins_01,
            'coins_005': self.coins_005,
            'notes': self.notes,
        })
        
        # Confirm the count
        count.action_confirm()
        
        # End the shift
        self.shift_id.write({
            'end_time': self.end_time,
            'ending_balance': self.counted_amount,
            'state': 'closed' if abs(self.discrepancy) <= 0.01 else 'discrepancy',
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shift Ended'),
                'message': _('Cashier shift has been ended successfully.'),
                'sticky': False,
                'type': 'success',
            }
        }
