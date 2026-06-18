from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class SecurityGateCashier(models.Model):
    _name = 'security.gate.cashier'
    _description = 'Security Gate Cashier'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Name', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Related Employee', tracking=True)
    user_id = fields.Many2one('res.users', string='Related User', tracking=True,
                             help="User account for this cashier to access the system")
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        groups='base.group_multi_company',
        help='Company this cashier belongs to'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True
    )
    gate_id = fields.Many2one('security.gate', string='Assigned Gate', tracking=True)
    shift_start = fields.Float(string='Shift Start Time', tracking=True)
    shift_end = fields.Float(string='Shift End Time', tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    # Cash drawer management
    cash_drawer_id = fields.Many2one('security.gate.cash.drawer', string='Cash Drawer', tracking=True)
    drawer_balance = fields.Monetary(related='cash_drawer_id.current_balance', string='Current Drawer Balance', readonly=True)
    last_balance_check = fields.Datetime(related='cash_drawer_id.last_balance_check', string='Last Balance Check', readonly=True)

    # Statistics
    total_transactions_today = fields.Integer(compute='_compute_statistics', string='Transactions Today')
    total_amount_today = fields.Monetary(compute='_compute_statistics', string='Amount Collected Today')
    transaction_ids = fields.One2many('security.gate.pass.payment', 'cashier_id', string='Transactions')

    # Access control statistics
    access_granted_count = fields.Integer(compute='_compute_access_statistics', string='Access Granted')
    access_denied_count = fields.Integer(compute='_compute_access_statistics', string='Access Denied')

    # Security & compliance
    last_training_date = fields.Date(string='Last Security Training', tracking=True)
    security_level = fields.Selection([
        ('1', 'Level 1 - Basic'),
        ('2', 'Level 2 - Intermediate'),
        ('3', 'Level 3 - Advanced'),
    ], string='Security Clearance Level', default='1', tracking=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Cashier name must be unique per company!')
    ]

    @api.depends('transaction_ids')
    def _compute_statistics(self):
        today = fields.Date.today()
        for cashier in self:
            today_transactions = cashier.transaction_ids.filtered(
                lambda t: t.payment_date == today and t.state == 'posted'
            )
            cashier.total_transactions_today = len(today_transactions)
            cashier.total_amount_today = sum(today_transactions.mapped('amount'))

    @api.depends('transaction_ids.access_granted')
    def _compute_access_statistics(self):
        for cashier in self:
            cashier.access_granted_count = len(cashier.transaction_ids.filtered(lambda t: t.access_granted))
            cashier.access_denied_count = len(cashier.transaction_ids.filtered(lambda t: not t.access_granted and t.state == 'posted'))

    def action_open_cash_drawer(self):
        """Open the cash drawer and record the event"""
        self.ensure_one()
        if not self.cash_drawer_id:
            raise UserError(_("No cash drawer assigned to this cashier."))

        return self.cash_drawer_id.action_open_drawer()

    def action_count_drawer(self):
        """Start the cash drawer counting process"""
        self.ensure_one()
        if not self.cash_drawer_id:
            raise UserError(_("No cash drawer assigned to this cashier."))

        return {
            'name': _('Count Cash Drawer'),
            'view_mode': 'form',
            'res_model': 'security.gate.cash.drawer.count.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_cash_drawer_id': self.cash_drawer_id.id},
        }

    def action_view_transactions(self):
        """View all transactions processed by this cashier"""
        self.ensure_one()
        return {
            'name': _('Transactions'),
            'view_mode': 'tree,form',
            'res_model': 'security.gate.pass.payment',
            'domain': [('cashier_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_cashier_id': self.id},
        }

    def action_start_shift(self):
        """Start the cashier's shift"""
        self.ensure_one()
        if not self.cash_drawer_id:
            raise UserError(_("Cannot start shift: No cash drawer assigned to this cashier."))

        # Create shift record
        shift = self.env['security.gate.cashier.shift'].create({
            'cashier_id': self.id,
            'start_time': fields.Datetime.now(),
            'starting_balance': self.cash_drawer_id.current_balance,
            'gate_id': self.gate_id.id if self.gate_id else False,
        })

        # Open the drawer for initial count
        return self.action_count_drawer()

    def action_end_shift(self):
        """End the cashier's shift"""
        self.ensure_one()

        # Find open shift
        shift = self.env['security.gate.cashier.shift'].search([
            ('cashier_id', '=', self.id),
            ('end_time', '=', False)
        ], limit=1)

        if not shift:
            raise UserError(_("No active shift found for this cashier."))

        # Open wizard to count drawer and end shift
        return {
            'name': _('End Shift'),
            'view_mode': 'form',
            'res_model': 'security.gate.cashier.end.shift.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_shift_id': shift.id,
                'default_cash_drawer_id': self.cash_drawer_id.id,
                'default_current_balance': self.cash_drawer_id.current_balance,
            },
        }


class SecurityGateCashDrawer(models.Model):
    _name = 'security.gate.cash.drawer'
    _description = 'Security Gate Cash Drawer'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Drawer Name', required=True, tracking=True)
    gate_id = fields.Many2one('security.gate', string='Gate', tracking=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        groups='base.group_multi_company',
        help='Company this cash drawer belongs to'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True
    )
    current_balance = fields.Monetary(string='Current Balance', default=0.0, tracking=True)
    last_balance_check = fields.Datetime(string='Last Balance Check', tracking=True)
    status = fields.Selection([
        ('closed', 'Closed'),
        ('open', 'Open'),
        ('counting', 'Counting'),
        ('discrepancy', 'Discrepancy Reported'),
    ], string='Status', default='closed', tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    # Cash drawer history
    transaction_ids = fields.One2many('security.gate.cash.drawer.transaction', 'cash_drawer_id', string='Transactions')
    count_ids = fields.One2many('security.gate.cash.drawer.count', 'cash_drawer_id', string='Counts')

    def action_open_drawer(self):
        """Open the cash drawer and record the event"""
        self.ensure_one()

        # Record the drawer opening event
        self.env['security.gate.cash.drawer.transaction'].create({
            'cash_drawer_id': self.id,
            'transaction_type': 'open',
            'amount': 0.0,
            'notes': 'Drawer opened by ' + self.env.user.name,
        })

        self.write({
            'status': 'open',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cash Drawer'),
                'message': _('Cash drawer opened successfully.'),
                'sticky': False,
                'type': 'success',
            }
        }

    def action_close_drawer(self):
        """Close the cash drawer and record the event"""
        self.ensure_one()

        # Record the drawer closing event
        self.env['security.gate.cash.drawer.transaction'].create({
            'cash_drawer_id': self.id,
            'transaction_type': 'close',
            'amount': 0.0,
            'notes': 'Drawer closed by ' + self.env.user.name,
        })

        self.write({
            'status': 'closed',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cash Drawer'),
                'message': _('Cash drawer closed successfully.'),
                'sticky': False,
                'type': 'success',
            }
        }


class SecurityGateCashDrawerTransaction(models.Model):
    _name = 'security.gate.cash.drawer.transaction'
    _description = 'Cash Drawer Transaction'
    _order = 'transaction_date desc, id desc'

    cash_drawer_id = fields.Many2one('security.gate.cash.drawer', string='Cash Drawer', required=True)
    transaction_date = fields.Datetime(string='Transaction Date', default=fields.Datetime.now, required=True)
    transaction_type = fields.Selection([
        ('open', 'Open Drawer'),
        ('close', 'Close Drawer'),
        ('add', 'Add Cash'),
        ('remove', 'Remove Cash'),
        ('count', 'Count Drawer'),
        ('payment', 'Customer Payment'),
        ('refund', 'Customer Refund'),
        ('adjustment', 'Balance Adjustment'),
    ], string='Transaction Type', required=True)
    amount = fields.Float(string='Amount', default=0.0)
    payment_id = fields.Many2one('security.gate.pass.payment', string='Related Payment')
    count_id = fields.Many2one('security.gate.cash.drawer.count', string='Related Count')
    notes = fields.Text(string='Notes')
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


class SecurityGateCashDrawerCount(models.Model):
    _name = 'security.gate.cash.drawer.count'
    _description = 'Cash Drawer Count'
    _order = 'count_date desc, id desc'

    cash_drawer_id = fields.Many2one('security.gate.cash.drawer', string='Cash Drawer', required=True)
    cashier_id = fields.Many2one('security.gate.cashier', string='Cashier', required=True)
    count_date = fields.Datetime(string='Count Date', default=fields.Datetime.now, required=True)
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

    # Count details
    expected_amount = fields.Monetary(string='Expected Amount', required=True)
    counted_amount = fields.Monetary(string='Counted Amount', required=True)
    discrepancy = fields.Monetary(string='Discrepancy', compute='_compute_discrepancy', store=True)

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

    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('discrepancy', 'Discrepancy Reported'),
    ], string='Status', default='draft')

    @api.depends('expected_amount', 'counted_amount')
    def _compute_discrepancy(self):
        for count in self:
            count.discrepancy = count.counted_amount - count.expected_amount

    @api.onchange('notes_200', 'notes_100', 'notes_50', 'notes_20', 'notes_10', 'notes_5',
                 'coins_2', 'coins_1', 'coins_05', 'coins_025', 'coins_01', 'coins_005')
    def _onchange_denominations(self):
        """Calculate the total amount based on denominations"""
        self.counted_amount = (
            self.notes_200 * 200 +
            self.notes_100 * 100 +
            self.notes_50 * 50 +
            self.notes_20 * 20 +
            self.notes_10 * 10 +
            self.notes_5 * 5 +
            self.coins_2 * 2 +
            self.coins_1 * 1 +
            self.coins_05 * 0.5 +
            self.coins_025 * 0.25 +
            self.coins_01 * 0.1 +
            self.coins_005 * 0.05
        )

    def action_confirm(self):
        """Confirm the cash drawer count"""
        self.ensure_one()

        # Update the cash drawer balance
        self.cash_drawer_id.write({
            'current_balance': self.counted_amount,
            'last_balance_check': fields.Datetime.now(),
        })

        # Create transaction record
        self.env['security.gate.cash.drawer.transaction'].create({
            'cash_drawer_id': self.cash_drawer_id.id,
            'transaction_type': 'count',
            'amount': self.discrepancy,  # Record the discrepancy amount
            'count_id': self.id,
            'notes': f'Drawer count by {self.cashier_id.name}. Discrepancy: {self.discrepancy}',
        })

        # Update status
        if abs(self.discrepancy) > 0:
            self.write({'state': 'discrepancy'})
            self.cash_drawer_id.write({'status': 'discrepancy'})
        else:
            self.write({'state': 'confirmed'})

        return True


class SecurityGateCashierShift(models.Model):
    _name = 'security.gate.cashier.shift'
    _description = 'Cashier Shift'
    _order = 'start_time desc, id desc'

    cashier_id = fields.Many2one('security.gate.cashier', string='Cashier', required=True)
    gate_id = fields.Many2one('security.gate', string='Gate')
    start_time = fields.Datetime(string='Start Time', default=fields.Datetime.now, required=True)
    end_time = fields.Datetime(string='End Time')
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True)
    company_id = fields.Many2one(
        'res.company',
        related='cashier_id.company_id',
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

    # Financial data
    starting_balance = fields.Monetary(string='Starting Balance', required=True)
    ending_balance = fields.Monetary(string='Ending Balance')
    expected_balance = fields.Monetary(string='Expected Balance', compute='_compute_expected_balance')
    discrepancy = fields.Monetary(string='Discrepancy', compute='_compute_discrepancy', store=True)

    # Transaction data
    transaction_count = fields.Integer(string='Transaction Count', compute='_compute_transactions')
    transaction_total = fields.Monetary(string='Transaction Total', compute='_compute_transactions')
    transaction_ids = fields.One2many('security.gate.pass.payment', 'shift_id', string='Transactions')

    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('discrepancy', 'Discrepancy Reported'),
    ], string='Status', default='open')

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for shift in self:
            if shift.start_time and shift.end_time:
                delta = shift.end_time - shift.start_time
                shift.duration = delta.total_seconds() / 3600
            else:
                shift.duration = 0

    @api.depends('transaction_ids.amount', 'transaction_ids.state', 'starting_balance')
    def _compute_expected_balance(self):
        for shift in self:
            posted_transactions = shift.transaction_ids.filtered(lambda t: t.state == 'posted')
            transaction_total = sum(posted_transactions.mapped('amount'))
            shift.expected_balance = shift.starting_balance + transaction_total

    @api.depends('expected_balance', 'ending_balance')
    def _compute_discrepancy(self):
        for shift in self:
            if shift.ending_balance:
                shift.discrepancy = shift.ending_balance - shift.expected_balance
            else:
                shift.discrepancy = 0

    @api.depends('transaction_ids.amount', 'transaction_ids.state')
    def _compute_transactions(self):
        for shift in self:
            posted_transactions = shift.transaction_ids.filtered(lambda t: t.state == 'posted')
            shift.transaction_count = len(posted_transactions)
            shift.transaction_total = sum(posted_transactions.mapped('amount'))
