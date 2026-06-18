from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class SecurityGatePassPayment(models.Model):
    _name = 'security.gate.pass.payment'
    _description = 'Gate Pass Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'payment_date desc, id desc'

    name = fields.Char(string='Receipt Reference', required=True, readonly=True, copy=False,
                     default=lambda self: _('New'))
    gate_pass_id = fields.Many2one('security.gate.pass', string='Gate Pass', required=True, tracking=True)
    client_id = fields.Many2one(related='gate_pass_id.client_id', string='Client', store=True, tracking=True)
    payment_date = fields.Date(string='Payment Date', required=True, default=fields.Date.today, tracking=True)
    amount = fields.Float(string='Amount', required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        groups='base.group_multi_company',
        help='Company this record belongs to'
    )
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id.id)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('card', 'Credit/Debit Card'),
        ('mobile', 'Mobile Payment'),
        ('other', 'Other')
    ], string='Payment Method', required=True, default='cash', tracking=True)
    payment_reference = fields.Char(string='Payment Reference')
    notes = fields.Text(string='Notes')

    # Account move integration
    move_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # Gate pass details
    visitor_id = fields.Many2one('res.partner', string='Visitor', readonly=True, store=True)
    # Directly define these fields instead of using related fields to avoid dependency issues
    visitor_name = fields.Char(string='Visitor Name', readonly=True, store=True)
    visitor_company = fields.Char(string='Visitor Company', readonly=True, store=True)
    valid_from = fields.Datetime(string='Valid From', readonly=True, store=True)
    valid_until = fields.Datetime(string='Valid Until', readonly=True, store=True)
    days_valid = fields.Integer(string='Days Valid', readonly=True, store=True)

    # Cashier fields
    cashier_id = fields.Many2one('security.gate.cashier', string='Cashier', tracking=True,
                               help="Cashier who processed this payment")
    shift_id = fields.Many2one('security.gate.cashier.shift', string='Cashier Shift')
    gate_id = fields.Many2one('security.gate', string='Gate', tracking=True)

    # Access control fields
    access_granted = fields.Boolean(string='Access Granted', default=True, tracking=True,
                                  help="Indicates if access was granted after payment")
    access_time = fields.Datetime(string='Access Time', tracking=True)
    access_notes = fields.Text(string='Access Notes')

    # Receipt information
    receipt_printed = fields.Boolean(string='Receipt Printed', default=False)
    receipt_number = fields.Char(string='Receipt Number', readonly=True)

    @api.onchange('gate_pass_id')
    def _onchange_gate_pass_id(self):
        if self.gate_pass_id:
            self.visitor_id = self.gate_pass_id.visitor_id
            self.visitor_name = self.gate_pass_id.visitor_name
            self.visitor_company = self.gate_pass_id.visitor_company
            self.valid_from = self.gate_pass_id.valid_from
            self.valid_until = self.gate_pass_id.valid_until
            if hasattr(self.gate_pass_id, 'days_valid'):
                self.days_valid = self.gate_pass_id.days_valid

    @api.onchange('cashier_id')
    def _onchange_cashier_id(self):
        if self.cashier_id:
            self.gate_id = self.cashier_id.gate_id

            # Find active shift for this cashier
            active_shift = self.env['security.gate.cashier.shift'].search([
                ('cashier_id', '=', self.cashier_id.id),
                ('state', '=', 'open')
            ], limit=1)

            if active_shift:
                self.shift_id = active_shift.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.gate.pass.payment') or _('New')

            # Generate receipt number if not provided
            if not vals.get('receipt_number'):
                vals['receipt_number'] = self.env['ir.sequence'].next_by_code('security.gate.receipt') or vals.get('name')

        return super(SecurityGatePassPayment, self).create(vals_list)

    def action_post(self):
        """Post the payment and create the corresponding account move"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only draft payments can be posted."))

        # Get the partner from the client or visitor
        partner_id = False
        if self.gate_pass_id.client_id and hasattr(self.gate_pass_id.client_id, 'partner_id') and self.gate_pass_id.client_id.partner_id:
            partner_id = self.gate_pass_id.client_id.partner_id.id
        elif self.gate_pass_id.visitor_id:
            partner_id = self.gate_pass_id.visitor_id.id

        if not partner_id:
            raise UserError(_("The gate pass must have a related partner (client or visitor) to create an invoice."))

        # Create the invoice (account.move)
        move_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner_id,
            'invoice_date': self.payment_date,
            'invoice_date_due': self.payment_date,
            'ref': self.name,
            'invoice_line_ids': [(0, 0, {
                'name': f"Gate Pass {self.gate_pass_id.name} - {self.gate_pass_id.visitor_name or ''}",
                'quantity': 1,
                'price_unit': self.amount,
                # Get the appropriate account ID
                'account_id': self._get_income_account().id,
            })],
        }

        move = self.env['account.move'].create(move_vals)
        self.write({
            'move_id': move.id,
            'state': 'posted'
        })

        # Post the invoice
        move.action_post()

        # Update the gate pass status if needed
        if self.gate_pass_id.state in ['draft', 'pending']:
            self.gate_pass_id.write({'state': 'approved'})

            # Update approval information directly on the gate pass record
            if hasattr(self.gate_pass_id, 'approved_by'):
                self.gate_pass_id.approved_by = self.env.user.id
            if hasattr(self.gate_pass_id, 'approved_date'):
                self.gate_pass_id.approved_date = fields.Datetime.now()

        # Update cash drawer if payment is cash
        if self.payment_method == 'cash' and self.cashier_id and self.cashier_id.cash_drawer_id:
            # Record the transaction in the cash drawer
            self.env['security.gate.cash.drawer.transaction'].create({
                'cash_drawer_id': self.cashier_id.cash_drawer_id.id,
                'transaction_type': 'payment',
                'amount': self.amount,
                'payment_id': self.id,
                'notes': f'Payment for gate pass {self.gate_pass_id.name}',
            })

            # Update the cash drawer balance
            self.cashier_id.cash_drawer_id.write({
                'current_balance': self.cashier_id.cash_drawer_id.current_balance + self.amount
            })

        # Record access time
        self.write({
            'access_time': fields.Datetime.now(),
            'receipt_printed': True
        })

        return True

    def _get_income_account(self):
        """Get the appropriate income account for gate pass invoices"""
        # Try to get from product category
        account = self.env['ir.property']._get('property_account_income_categ_id', 'product.category')

        # If not found, try to get from company settings
        if not account:
            # Get the company
            company = self.env.company

            # Search for a default income account in Odoo 17 format
            account = self.env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'income'),
            ], limit=1)

        if not account:
            raise UserError(_("Please define an income account for gate pass invoices in your chart of accounts."))

        return account

    def action_cancel(self):
        """Cancel the payment and the corresponding invoice"""
        self.ensure_one()
        if self.state != 'posted':
            raise UserError(_("Only posted payments can be cancelled."))

        # Cancel the invoice if it exists
        if self.move_id:
            if self.move_id.state == 'posted':
                self.move_id.button_draft()
            self.move_id.button_cancel()

        # Update cash drawer if payment was cash
        if self.payment_method == 'cash' and self.cashier_id and self.cashier_id.cash_drawer_id:
            # Record the refund transaction in the cash drawer
            self.env['security.gate.cash.drawer.transaction'].create({
                'cash_drawer_id': self.cashier_id.cash_drawer_id.id,
                'transaction_type': 'refund',
                'amount': -self.amount,
                'payment_id': self.id,
                'notes': f'Refund for cancelled payment {self.name}',
            })

            # Update the cash drawer balance
            self.cashier_id.cash_drawer_id.write({
                'current_balance': self.cashier_id.cash_drawer_id.current_balance - self.amount
            })

        self.write({'state': 'cancelled'})
        return True

    def action_view_invoice(self):
        """Open the related invoice"""
        self.ensure_one()
        if not self.move_id:
            raise UserError(_("No invoice has been created for this payment."))

        return {
            'name': _('Invoice'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'type': 'ir.actions.act_window',
        }

    def action_print_receipt(self):
        """Print the payment receipt"""
        self.ensure_one()
        # Check if the report exists
        report = self.env.ref('security_management.action_report_gate_pass_receipt', raise_if_not_found=False)
        if not report:
            raise UserError(_("Receipt report template not found. Please create the report template first."))

        # Mark receipt as printed
        self.write({'receipt_printed': True})

        return report.report_action(self)

    def action_grant_access(self):
        """Grant access to the visitor"""
        self.ensure_one()

        if self.state != 'posted':
            raise UserError(_("Payment must be posted before granting access."))

        self.write({
            'access_granted': True,
            'access_time': fields.Datetime.now()
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Access Granted'),
                'message': _('Access has been granted to %s') % (self.visitor_name or 'visitor'),
                'sticky': False,
                'type': 'success',
            }
        }

    def action_deny_access(self):
        """Deny access to the visitor"""
        self.ensure_one()

        self.write({
            'access_granted': False,
            'access_time': fields.Datetime.now()
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Access Denied'),
                'message': _('Access has been denied to %s') % (self.visitor_name or 'visitor'),
                'sticky': False,
                'type': 'warning',
            }
        }
    
    def action_draft(self):
        self.write({'state': 'draft'})
        return True

class SecurityGatePass(models.Model):
    _inherit = 'security.gate.pass'

    payment_ids = fields.One2many('security.gate.pass.payment', 'gate_pass_id', string='Payments')
    payment_count = fields.Integer(compute='_compute_payment_count', string='Payment Count')
    total_paid = fields.Float(compute='_compute_total_paid', string='Total Paid')

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for gate_pass in self:
            gate_pass.payment_count = len(gate_pass.payment_ids.filtered(lambda p: p.state == 'posted'))

    @api.depends('payment_ids')
    def _compute_total_paid(self):
        for gate_pass in self:
            gate_pass.total_paid = sum(gate_pass.payment_ids.filtered(lambda p: p.state == 'posted').mapped('amount'))

    def action_view_payments(self):
        self.ensure_one()
        return {
            'name': _('Payments'),
            'view_mode': 'tree,form',
            'res_model': 'security.gate.pass.payment',
            'domain': [('gate_pass_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_gate_pass_id': self.id},
        }

    def action_create_payment(self):
        """Create a new payment for this gate pass"""
        self.ensure_one()

        # Find active cashier for current user
        cashier = self.env['security.gate.cashier'].search([
            ('user_id', '=', self.env.user.id),
            ('active', '=', True)
        ], limit=1)

        return {
            'name': _('Create Payment'),
            'view_mode': 'form',
            'res_model': 'security.gate.pass.payment',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {
                'default_gate_pass_id': self.id,
                'default_cashier_id': cashier.id if cashier else False,
            },
        }


class SecurityClient(models.Model):
    _inherit = 'security.client'

    partner_id = fields.Many2one('res.partner', string='Related Partner',
                                help="Partner used for accounting operations")


class SecurityGate(models.Model):
    _name = 'security.gate'
    _description = 'Security Gate'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Gate Name', required=True, tracking=True)
    code = fields.Char(string='Gate Code', tracking=True)
    location = fields.Char(string='Location', tracking=True)
    gate_type = fields.Selection([
        ('entry', 'Entry Gate'),
        ('exit', 'Exit Gate'),
        ('both', 'Entry/Exit Gate'),
    ], string='Gate Type', default='both', required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        groups='base.group_multi_company',
        help='Company this gate belongs to'
    )
    active = fields.Boolean(default=True, tracking=True)

    # Related records
    cashier_ids = fields.One2many('security.gate.cashier', 'gate_id', string='Assigned Cashiers')
    cash_drawer_ids = fields.One2many('security.gate.cash.drawer', 'gate_id', string='Cash Drawers')

    # Statistics
    payment_count = fields.Integer(compute='_compute_statistics', string='Payment Count')
    access_count = fields.Integer(compute='_compute_statistics', string='Access Count')

    @api.depends('cashier_ids')
    def _compute_statistics(self):
        for gate in self:
            # Get payments related to this gate
            payments = self.env['security.gate.pass.payment'].search([
                ('gate_id', '=', gate.id),
                ('state', '=', 'posted')
            ])
            gate.payment_count = len(payments)
            gate.access_count = len(payments.filtered(lambda p: p.access_granted))

    def action_view_payments(self):
        self.ensure_one()
        return {
            'name': _('Payments'),
            'view_mode': 'tree,form',
            'res_model': 'security.gate.pass.payment',
            'domain': [('gate_id', '=', self.id)],
            'type': 'ir.actions.act_window',
        }

    def action_view_cashiers(self):
        self.ensure_one()
        return {
            'name': _('Cashiers'),
            'view_mode': 'tree,form',
            'res_model': 'security.gate.cashier',
            'domain': [('gate_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_gate_id': self.id},
        }
