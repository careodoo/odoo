# -*- coding: utf-8 -*-
from markupsafe import Markup, escape
from odoo import api, fields, models, _


class PmsSupply(models.Model):
    _name = 'care.pms.supply'
    _description = 'Project Material Supply (Incoming)'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string='Reference', default='/', copy=False, readonly=True)
    project_id = fields.Many2one('project.project', string='Project', required=True, index=True, tracking=True)
    source = fields.Char(string='Source / PR Ref', tracking=True)
    request_id = fields.Many2one('purchase.request', string='Purchase Request', index=True, tracking=True)
    po_id = fields.Many2one('purchase.order', string='Purchase Order', index=True, tracking=True)
    so_id = fields.Many2one('sale.order', string='Sales Order', index=True, tracking=True)
    date = fields.Date(string='Date', default=fields.Date.today, tracking=True)
    received_date = fields.Date(string='Received On', readonly=True)
    receiver_name = fields.Char(string='Received By')
    state = fields.Selection(
        [('draft', 'Draft'), ('sent', 'In Transit'),
         ('partial', 'Partially Received'), ('received', 'Received'),
         ('rejected', 'Rejected')],
        string='Status', default='draft', tracking=True)
    line_ids = fields.One2many('care.pms.supply.line', 'supply_id', string='Items')
    delivery_note = fields.Binary(string='Delivery Voucher', attachment=True)
    delivery_note_name = fields.Char(string='Delivery Voucher Filename')

    def _recompute_state(self):
        """Roll the header state up from the per-line receive/reject decisions."""
        for supply in self:
            lines = supply.line_ids
            if not lines:
                continue
            done = lines.filtered(lambda l: l.line_state in ('received', 'rejected'))
            received = lines.filtered(lambda l: l.line_state == 'received')
            if not done:
                continue
            if len(done) < len(lines):
                supply.state = 'partial'
            elif received:
                supply.state = 'received'
                if not supply.received_date:
                    supply.received_date = fields.Date.today()
            else:
                supply.state = 'rejected'
            if received and supply.state == 'received':
                supply._notify_purchasing_received()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.pms.supply') or '/'
        return super().create(vals_list)

    def action_send(self):
        self.write({'state': 'sent'})
        self._notify_project_manager()

    def _notify_project_manager(self):
        """Alert the project manager that materials are on the way to be received."""
        for supply in self:
            manager = supply.project_id.project_manager_id or supply.project_id.user_id
            if not manager or not manager.partner_id:
                continue
            items = ''.join(
                '<li style="margin:2px 0;">%s — <b>%s</b> %s</li>' % (
                    escape(line.name or ''), escape(line.qty), escape(line.uom_name or ''))
                for line in supply.line_ids)
            base = supply.get_base_url()
            url = '%s/my/pm/p/%s/supplies' % (base, supply.project_id.id)
            body = Markup(
                '<div style="max-width:560px;font-family:Tahoma,Arial,sans-serif;direction:rtl;'
                'border:1px solid #e4e8f0;border-radius:12px;overflow:hidden;">'
                '<div style="background:#15213b;padding:14px 20px;">'
                '<span style="color:#f0663c;font-weight:bold;font-size:18px;">CARE</span>'
                '<span style="color:#aeb8cc;font-size:12px;"> · واردات المشروع</span></div>'
                '<div style="background:#e08a00;height:5px;"></div>'
                '<div style="padding:20px;">'
                '<h2 style="margin:0 0 6px;color:#15213b;font-size:18px;">📥 وارد مواد جديد بانتظار الاستلام</h2>'
                '<p style="color:#555;font-size:14px;line-height:1.7;margin:0 0 12px;">'
                'تم إرسال مواد إلى مشروع <b>%s</b> من المشتريات (المصدر: %s). '
                'برجاء استلامها من البورتال لتُضاف إلى مخزون المشروع.</p>'
                '<ul style="color:#1d2433;font-size:13px;padding-inline-start:20px;margin:0 0 16px;">%s</ul>'
                '<div style="text-align:center;">'
                '<a href="%s" style="display:inline-block;background:#2f6df6;color:#fff;padding:10px 24px;'
                'border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px;">استلام الواردات ←</a></div>'
                '</div></div>') % (
                    escape(supply.project_id.name or ''), escape(supply.source or '—'),
                    Markup(items), escape(url))
            supply.message_post(
                body=body, subject=_('وارد مواد جديد: %s') % supply.name,
                partner_ids=manager.partner_id.ids, message_type='notification',
                subtype_xmlid='mail.mt_comment', email_layout_xmlid='mail.mail_notification_light')
            supply._push_inapp(
                manager.partner_id, _('وارد مواد جديد: %s') % supply.name,
                _('وصلت مواد إلى مشروع %s بانتظار الاستلام.') % (supply.project_id.name or ''))

    def _push_inapp(self, partners, title, body):
        """Mirror a supply notification into the mobile notification inbox."""
        if 'care.cafm.notification' not in self.env or not partners:
            return
        try:
            users = self.env['res.users'].sudo().search(
                [('partner_id', 'in', partners.ids), ('active', '=', True)])
            if users:
                self.env['care.cafm.notification'].sudo().push(
                    users, title, body, ntype='task', author=self.env.user,
                    action_url='/pms/project/%s' % self.project_id.id)
        except Exception:
            pass

    def action_receive(self):
        """Receive every still-pending line in full (whole-document shortcut)."""
        for supply in self:
            for line in supply.line_ids.filtered(lambda l: l.line_state == 'pending'):
                line.action_receive_line(line.qty)
        return True

    def _notify_purchasing_received(self):
        """Confirm back to the purchasing requester that the materials arrived."""
        for supply in self:
            req = supply.request_id
            if not req:
                continue
            requester = req.create_uid
            items = ''.join(
                '<li style="margin:2px 0;">%s — <b>%s</b> %s</li>' % (
                    escape(line.name or ''), escape(line.qty), escape(line.uom_name or ''))
                for line in supply.line_ids)
            body = Markup(
                '<div style="max-width:560px;font-family:Tahoma,Arial,sans-serif;direction:rtl;'
                'border:1px solid #e4e8f0;border-radius:12px;overflow:hidden;">'
                '<div style="background:#15213b;padding:14px 20px;">'
                '<span style="color:#f0663c;font-weight:bold;font-size:18px;">CARE</span>'
                '<span style="color:#aeb8cc;font-size:12px;"> · تأكيد استلام</span></div>'
                '<div style="background:#27ae60;height:5px;"></div>'
                '<div style="padding:20px;">'
                '<h2 style="margin:0 0 6px;color:#15213b;font-size:18px;">✅ تم استلام المواد في المشروع</h2>'
                '<p style="color:#555;font-size:14px;line-height:1.7;margin:0 0 12px;">'
                'تم استلام المواد الخاصة بطلب الشراء <b>%s</b> في مشروع <b>%s</b> '
                'بتاريخ %s وإضافتها إلى مخزون المشروع.</p>'
                '<ul style="color:#1d2433;font-size:13px;padding-inline-start:20px;margin:0;">%s</ul>'
                '</div></div>') % (
                    escape(req.name or ''), escape(supply.project_id.name or ''),
                    escape(supply.received_date or ''), Markup(items))
            # chatter on the purchase request
            try:
                req.message_post(body=body, subject=_('تم استلام مواد الطلب %s') % req.name,
                                 message_type='notification', subtype_xmlid='mail.mt_note')
            except Exception:
                pass
            # notify the requester by email
            if requester and requester.partner_id:
                supply.message_post(
                    body=body, subject=_('تأكيد استلام: %s') % supply.name,
                    partner_ids=requester.partner_id.ids, message_type='notification',
                    subtype_xmlid='mail.mt_comment', email_layout_xmlid='mail.mail_notification_light')
                supply._push_inapp(
                    requester.partner_id, _('تأكيد استلام: %s') % supply.name,
                    _('تم استلام مواد الطلب %s في مشروع %s.')
                    % (req.name or '', supply.project_id.name or ''))

    def action_draft(self):
        self.write({'state': 'draft'})


class PmsSupplyLine(models.Model):
    _name = 'care.pms.supply.line'
    _description = 'Supply Line'

    supply_id = fields.Many2one('care.pms.supply', string='Supply', required=True,
                                ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Char(string='Item', required=True)
    uom_name = fields.Char(string='Unit', default='وحدة')
    qty = fields.Float(string='Quantity', required=True)
    received_qty = fields.Float(string='Received Qty', default=0.0)
    line_state = fields.Selection(
        [('pending', 'Pending'), ('received', 'Received'), ('rejected', 'Rejected')],
        string='Line Status', default='pending', required=True)
    reject_reason = fields.Char(string='Reject Reason')

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id:
            self.name = self.product_id.display_name
            if self.product_id.uom_id:
                self.uom_name = self.product_id.uom_id.name

    def action_receive_line(self, qty=None):
        """Receive this single line: post its received qty into project stock."""
        Material = self.env['care.pms.material']
        Receipt = self.env['care.pms.material.receipt']
        for line in self:
            take = line.qty if qty is None else float(qty)
            if take <= 0:
                continue
            mat = Material.search([('project_id', '=', line.supply_id.project_id.id),
                                   ('name', '=', line.name)], limit=1)
            if not mat:
                mat = Material.create({
                    'project_id': line.supply_id.project_id.id, 'name': line.name,
                    'uom_name': line.uom_name or 'وحدة',
                    'product_id': line.product_id.id,
                })
            Receipt.create({'material_id': mat.id, 'qty': take,
                            'ref': line.supply_id.name, 'date': fields.Date.today()})
            line.write({'received_qty': take, 'line_state': 'received',
                        'reject_reason': False})
            line.supply_id._recompute_state()
        return True

    def action_reject_line(self, reason=None):
        for line in self:
            line.write({'line_state': 'rejected', 'received_qty': 0.0,
                        'reject_reason': reason or ''})
            line.supply_id._recompute_state()
        return True


class PurchaseRequestPms(models.Model):
    _inherit = 'purchase.request'

    def action_pms_send_to_project(self):
        """Create an incoming supply document for the linked project (in transit)."""
        Supply = self.env['care.pms.supply']
        created = self.env['care.pms.supply']
        for req in self:
            if not req.project_id:
                continue
            created |= Supply.create({
                'project_id': req.project_id.id,
                'source': req.name,
                'request_id': req.id,
                'state': 'sent',
            })
        if created:
            created._notify_project_manager()
            return {
                'type': 'ir.actions.act_window',
                'name': _('Supply to Project'),
                'res_model': 'care.pms.supply',
                'view_mode': 'form' if len(created) == 1 else 'tree,form',
                'res_id': created.id if len(created) == 1 else False,
                'domain': [('id', 'in', created.ids)],
            }
        return True
