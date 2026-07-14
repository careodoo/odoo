# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PmsMaterial(models.Model):
    _name = 'care.pms.material'
    _description = 'Project Material Balance'
    _order = 'project_id, id'

    project_id = fields.Many2one('project.project', string='Project', required=True,
                                 ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Char(string='Item', required=True)
    uom_name = fields.Char(string='Unit', default='وحدة')
    min_qty = fields.Float(string='Min. Qty')

    receipt_ids = fields.One2many('care.pms.material.receipt', 'material_id', string='Receipts')
    line_ids = fields.One2many('care.pms.delivery.note.line', 'material_id', string='Issues')

    received_qty = fields.Float(string='Received', compute='_compute_balance', store=True)
    issued_qty = fields.Float(string='Issued', compute='_compute_balance', store=True)
    available_qty = fields.Float(string='Available', compute='_compute_balance', store=True)
    is_low = fields.Boolean(string='Below Min', compute='_compute_balance', store=True)

    @api.depends('receipt_ids.qty', 'line_ids.qty', 'line_ids.note_id.state', 'min_qty')
    def _compute_balance(self):
        for m in self:
            received = sum(m.receipt_ids.mapped('qty'))
            issued = sum(l.qty for l in m.line_ids if l.note_id.state == 'done')
            m.received_qty = received
            m.issued_qty = issued
            m.available_qty = received - issued
            m.is_low = (received - issued) <= m.min_qty

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id:
            self.name = self.product_id.display_name
            if self.product_id.uom_id:
                self.uom_name = self.product_id.uom_id.name


class PmsMaterialReceipt(models.Model):
    _name = 'care.pms.material.receipt'
    _description = 'Material Monthly Receipt'
    _order = 'date desc, id desc'

    material_id = fields.Many2one('care.pms.material', string='Material', required=True,
                                  ondelete='cascade', index=True)
    qty = fields.Float(string='Received Qty', required=True)
    date = fields.Date(string='Date', default=fields.Date.today)
    ref = fields.Char(string='Reference')


class PmsDeliveryNote(models.Model):
    _name = 'care.pms.delivery.note'
    _description = 'Project Material Delivery Note'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string='Reference', default='/', copy=False, readonly=True)
    project_id = fields.Many2one('project.project', string='Project', required=True, index=True, tracking=True)
    location = fields.Char(string='Delivery Site', tracking=True)
    date = fields.Date(string='Date', default=fields.Date.today, tracking=True)
    receiver_name = fields.Char(string='Received By', tracking=True)
    receiver_signature = fields.Binary(string='Signature')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Confirmed')],
                             default='draft', tracking=True)
    line_ids = fields.One2many('care.pms.delivery.note.line', 'note_id', string='Lines')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.pms.delivery.note') or '/'
        return super().create(vals_list)

    def action_confirm(self):
        for note in self:
            # balance guard: sum requested per material must not exceed available
            per_material = {}
            for line in note.line_ids:
                per_material.setdefault(line.material_id, 0.0)
                per_material[line.material_id] += line.qty
            for material, qty in per_material.items():
                if qty > material.available_qty:
                    raise UserError(_(
                        'لا يمكن التسليم: الكمية المطلوبة من «%s» (%s) تتجاوز المتاح (%s).'
                    ) % (material.name, qty, material.available_qty))
            note.state = 'done'
        return True

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_print(self):
        return self.env.ref('care_pms.action_report_delivery_note').report_action(self)


class PmsDeliveryNoteLine(models.Model):
    _name = 'care.pms.delivery.note.line'
    _description = 'Delivery Note Line'

    note_id = fields.Many2one('care.pms.delivery.note', string='Note', required=True,
                              ondelete='cascade', index=True)
    material_id = fields.Many2one('care.pms.material', string='Material', required=True)
    qty = fields.Float(string='Quantity', required=True)
    available_qty = fields.Float(related='material_id.available_qty', string='Available', readonly=True)
    project_id = fields.Many2one(related='note_id.project_id', store=True)

    @api.onchange('qty', 'material_id')
    def _onchange_qty_guard(self):
        if self.material_id and self.qty > self.material_id.available_qty:
            return {'warning': {
                'title': _('تجاوز الرصيد'),
                'message': _('الكمية (%s) تتجاوز المتاح من «%s» (%s).')
                % (self.qty, self.material_id.name, self.material_id.available_qty)}}
