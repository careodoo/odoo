# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class LetterClassification(models.Model):
    _name = 'letter.classification'
    _description = 'Letter Classification'
    _order = 'sequence, id'

    name = fields.Char(string='Classification', required=True, translate=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(default=10)
    color = fields.Integer(string='Color')
    active = fields.Boolean(default=True)
    default_delivery_mode = fields.Selection(
        [('ack_required', 'Acknowledgement Required'), ('no_ack', 'No Acknowledgement — Auto Archive')],
        string='Default Delivery Mode', default='ack_required',
        help='Letters created with this classification default to this delivery mode.')
    letter_count = fields.Integer(compute='_compute_letter_count')

    def _compute_letter_count(self):
        data = self.env['letter.file'].read_group(
            [('classification_id', 'in', self.ids)], ['classification_id'], ['classification_id'])
        mapped = {d['classification_id'][0]: d['classification_id_count'] for d in data}
        for rec in self:
            rec.letter_count = mapped.get(rec.id, 0)


class LetterFee(models.Model):
    _name = 'letter.fee'
    _description = 'Letter Government Fee'

    letter_id = fields.Many2one('letter.file', string='Letter', required=True, ondelete='cascade')
    name = fields.Char(string='Description', required=True)
    amount = fields.Float(string='Amount (KWD)')
    state = fields.Selection([('unpaid', 'Unpaid'), ('paid', 'Paid')],
                             string='Status', default='unpaid')
    receipt = fields.Binary(string='Receipt')
    paid_date = fields.Date(string='Paid On')


class LetterTemplate(models.Model):
    _name = 'letter.template'
    _description = 'Letter Template'
    _order = 'sequence, id'

    name = fields.Char(string='Template Name', required=True, translate=True)
    sequence = fields.Integer(default=10)
    direction = fields.Selection([('outgoing', 'Outgoing'), ('incoming', 'Incoming')],
                                 default='outgoing')
    classification_id = fields.Many2one('letter.classification', string='Classification')
    subject = fields.Char(string='Default Subject', translate=True)
    body = fields.Text(string='Body', translate=True,
                       help='Use placeholders like [Employee], [Salary], [Job].')
    active = fields.Boolean(default=True)

    def action_create_letter(self):
        self.ensure_one()
        letter = self.env['letter.file'].create({
            'name': self.subject or self.name,
            'direction': self.direction,
            'classification_id': self.classification_id.id,
            'letter_contain': self.body or '',
            'letter_state': 'draft',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Letter'),
            'res_model': 'letter.file',
            'res_id': letter.id,
            'view_mode': 'form',
            'target': 'current',
        }


class LetterDashboard(models.TransientModel):
    _name = 'letter.dashboard'
    _description = 'Letters Dashboard'

    total = fields.Integer(readonly=True)
    outgoing = fields.Integer(readonly=True)
    incoming = fields.Integer(readonly=True)
    to_sign = fields.Integer(readonly=True)
    to_scan = fields.Integer(readonly=True)
    with_delegate = fields.Integer(readonly=True)
    overdue = fields.Integer(readonly=True)
    delivered = fields.Integer(readonly=True)
    acknowledged = fields.Integer(readonly=True)
    no_delivery = fields.Integer(readonly=True)
    no_scan = fields.Integer(readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        L = self.env['letter.file']
        res.update({
            'total': L.search_count([]),
            'outgoing': L.search_count([('direction', '=', 'outgoing')]),
            'incoming': L.search_count([('direction', '=', 'incoming')]),
            'to_sign': L.search_count([('letter_state', '=', 'to_sign')]),
            'to_scan': L.search_count([('letter_state', '=', 'signed')]),
            'with_delegate': L.search_count([('letter_state', '=', 'with_delegate')]),
            'overdue': L.search_count([('is_overdue', '=', True)]),
            'delivered': L.search_count([('letter_state', '=', 'delivered')]),
            'acknowledged': L.search_count([('letter_state', '=', 'acknowledged')]),
            'no_delivery': L.search_count([('deli_date', '=', False)]),
            'no_scan': L.search_count([('image_letter', '=', False)]),
        })
        return res

    def _open(self, domain, name):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'letter.file',
            'view_mode': 'tree,kanban,form',
            'domain': domain,
            'target': 'current',
        }

    def open_overdue(self):
        return self._open([('is_overdue', '=', True)], _('Overdue Deliveries'))

    def open_to_sign(self):
        return self._open([('letter_state', '=', 'to_sign')], _('Awaiting Signature'))

    def open_with_delegate(self):
        return self._open([('letter_state', '=', 'with_delegate')], _('With Delegate'))

    def open_no_delivery(self):
        return self._open([('deli_date', '=', False)], _('No Delivery Date'))
