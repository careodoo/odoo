# -*- coding: utf-8 -*-
# Collection payments on the invoice request (request.invoice): cash/cheque/transfer,
# with support for partial payment, the cheque image, and the cheque cycle.
from odoo import api, fields, models, _


class CollectionPayment(models.Model):
    _name = 'care.collection.payment'
    _description = 'دفعة تحصيل'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(string='Voucher number', default='/', copy=False, readonly=True, index=True)
    request_id = fields.Many2one('request.invoice', string='Invoice', required=True,
                                 ondelete='cascade', index=True, tracking=True)
    partner_id = fields.Many2one(related='request_id.partner_id', string='Client', store=True)
    collector_id = fields.Many2one('res.users', string='Collector',
                                   default=lambda s: s.env.user, tracking=True)
    date = fields.Date(string='Collection date', default=fields.Date.context_today, tracking=True)
    method = fields.Selection([
        ('cash', 'Cash'), ('cheque', 'Cheque'), ('transfer', 'Transfer'),
    ], string='Payment method', required=True, default='cash', tracking=True)
    amount = fields.Monetary(string='Collected amount', required=True, currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one(related='request_id.currency_id', store=True)

    # Cheque data + its image
    cheque_no = fields.Char(string='Cheque number')
    cheque_bank = fields.Char(string='Bank')
    cheque_due = fields.Date(string='Cheque due date')
    cheque_image = fields.Binary(string='Cheque image', attachment=True)
    cheque_image_name = fields.Char()
    cheque_state = fields.Selection([
        ('under_collection', 'Under collection'), ('collected', 'Collected'), ('bounced', 'Returned'),
    ], string='Cheque status', default='collected', tracking=True)

    # Snapshot of the invoice for quick display
    invoice_total = fields.Monetary(related='request_id.amount_total', string='Invoice total', currency_field='currency_id')
    residual_after = fields.Monetary(string='Remaining after payment', compute='_compute_residual', store=True, currency_field='currency_id')
    is_partial = fields.Boolean(string='Pay', compute='_compute_residual', store=True)
    recipient_name = fields.Char(string='Recipient / Signatory name')
    note = fields.Text(string='Notes')

    @api.depends('amount', 'request_id.amount_total', 'request_id.collection_residual')
    def _compute_residual(self):
        for p in self:
            total = p.request_id.amount_total or 0.0
            residual = (p.request_id.collection_residual or 0.0)
            p.residual_after = max(0.0, residual)
            p.is_partial = total > 0 and (p.amount or 0.0) < total

    @api.model
    def _autocollect_methods(self):
        """طرق الدفع المُعتبَرة محصّلة تلقائيًا (من الإعدادات)."""
        ICP = self.env['ir.config_parameter'].sudo()
        out = set()
        if ICP.get_param('care_collections.autocollect_cash', 'True') == 'True':
            out.add('cash')
        if ICP.get_param('care_collections.autocollect_cheque', 'False') == 'True':
            out.add('cheque')
        if ICP.get_param('care_collections.autocollect_transfer', 'True') == 'True':
            out.add('transfer')
        return out

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code('care.collection.payment') or '/'
            # كل دفعة تُعيَّن «محصّل» مباشرة عند التسجيل (طلب الإدارة) — أيًّا كانت طريقة الدفع.
            # (يبقى «تحت التحصيل»/«مرتجع» متاحًا يدويًا عبر تعديل الحالة لاحقًا إن لزم)
            if 'cheque_state' not in vals:
                vals['cheque_state'] = 'collected'
        recs = super().create(vals_list)
        for r in recs:
            r.request_id.sudo().message_post(body=_('💵 دفعة تحصيل %s %s عبر %s%s.') % (
                '{:,.3f}'.format(r.amount), r.currency_id.name or '',
                dict(self._fields['method'].selection).get(r.method),
                ' (مدفوع جزئياً)' if r.is_partial else ''))
            # On full collection the invoice is marked «compliant» (unless it is legally transferred)
            if not r.is_partial and r.request_id.collection_state != 'legal':
                r.request_id.sudo().with_context(skip_coll_notify=True).write({'collection_state': 'ok'})
        # When collection is complete (sum of payments ≥ invoice total) the invoice is marked
        # «collected» automatically, so the «mark collected» button disappears and the back end matches the app.
        for req in recs.mapped('request_id').sudo():
            total = req.amount_total or 0.0
            collected = sum(req.collection_payment_ids.mapped('amount'))
            if total > 0 and collected >= total - 0.01 and not req.collection_settled:
                dates = [d for d in req.collection_payment_ids.mapped('date') if d]
                req.with_context(skip_coll_notify=True).write({
                    'collection_settled': True,
                    'collection_settled_date': max(dates) if dates else fields.Date.context_today(req),
                    # Fully collected → no longer «expected to be collected», we clear the tag
                    'collection_forecast': False,
                })
            # Push notification for recording the collection
            req = r.request_id.sudo()
            r.request_id._notify_collection_event(
                'payment', '💵 تحصيل جديد',
                'سُجّلت دفعة %s %s على فاتورة %s (%s)%s.' % (
                    '{:,.3f}'.format(r.amount), r.currency_id.name or '',
                    req.name or '', req.partner_id.display_name or '',
                    ' — جزئي' if r.is_partial else ''),
                actor=r.collector_id)
        return recs

    def unlink(self):
        """عند التراجع عن دفعة: إن لم تعد الفاتورة مغطّاة بالكامل تُلغى علامة
        «محصّلة» التلقائية، فيعود التحصيل كما لو لم يُسجَّل."""
        reqs = self.mapped('request_id')
        res = super().unlink()
        for req in reqs.sudo().exists():
            total = req.amount_total or 0.0
            collected = sum(req.collection_payment_ids.mapped('amount'))
            if req.collection_settled and total > 0 and collected < total - 0.01:
                req.with_context(skip_coll_notify=True).write({
                    'collection_settled': False, 'collection_settled_date': False})
            req.message_post(body=_('↩️ تمّ التراجع عن دفعة تحصيل — المبلغ المحصّل الآن %s %s.') % (
                '{:,.3f}'.format(collected), req.currency_id.name or ''))
        return res
