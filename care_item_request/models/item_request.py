# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CareItemRequest(models.Model):
    _name = 'care.item.request'
    _description = 'طلب أصناف'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='المرجع', default='/', copy=False, readonly=True, index=True)
    project_id = fields.Many2one('project.project', string='المشروع', required=True, index=True, tracking=True)
    department_id = fields.Many2one('hr.department', related='project_id.pms_department_id',
                                    string='القسم', store=True)
    requested_by = fields.Many2one('res.users', string='مقدّم الطلب', default=lambda s: s.env.user,
                                   readonly=True, tracking=True)
    request_date = fields.Date(string='تاريخ الطلب', default=fields.Date.context_today, tracking=True)
    needed_by = fields.Date(string='مطلوب بحلول', tracking=True)
    priority = fields.Selection([('0', 'عادي'), ('1', 'عاجل')], string='الأولوية', default='0', tracking=True)
    note = fields.Text(string='ملاحظات / سبب الطلب')

    line_ids = fields.One2many('care.item.request.line', 'request_id', string='الأصناف')
    line_count = fields.Integer(compute='_compute_line_count')
    total_qty = fields.Float(string='إجمالي الكمية', compute='_compute_line_count')

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('submitted', 'مُرسل للاعتماد'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
    ], string='الحالة', default='draft', tracking=True, index=True)
    approved_by = fields.Many2one('res.users', string='اعتمده', readonly=True, tracking=True)
    approval_date = fields.Datetime(string='تاريخ الاعتماد', readonly=True)
    reject_reason = fields.Char(string='سبب الرفض')

    # the supply document created when the request is approved
    supply_id = fields.Many2one('care.pms.supply', string='التوريد الناتج', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('line_ids.qty')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)
            rec.total_qty = sum(rec.line_ids.mapped('qty'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.item.request') or '/'
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_('أضف صنفًا واحدًا على الأقل قبل الإرسال.'))
            rec.state = 'submitted'
            rec.message_post(body=_('تم إرسال طلب الأصناف «%s» للاعتماد (%s صنف).')
                             % (rec.name, len(rec.line_ids)))

    def action_approve(self):
        for rec in self:
            if rec.state not in ('submitted', 'draft'):
                continue
            # push the requested items into a project supply, ready to receive
            supply = self.env['care.pms.supply'].sudo().create({
                'project_id': rec.project_id.id,
                'source': _('طلب أصناف %s') % rec.name,
                'line_ids': [(0, 0, {
                    'product_id': l.product_id.id if l.product_id else False,
                    'name': l.name, 'uom_name': l.uom_name or 'وحدة', 'qty': l.qty,
                }) for l in rec.line_ids],
            })
            if hasattr(supply, 'action_send'):
                try:
                    supply.action_send()
                except Exception:
                    pass
            rec.write({'state': 'approved', 'approved_by': self.env.uid,
                       'approval_date': fields.Datetime.now(), 'supply_id': supply.id})
            rec.message_post(body=_('تم اعتماد الطلب وإنشاء توريد للمشروع: %s') % supply.name)

    def action_reject(self):
        for rec in self:
            rec.write({'state': 'rejected', 'approved_by': self.env.uid,
                       'approval_date': fields.Datetime.now()})
            rec.message_post(body=_('تم رفض طلب الأصناف «%s».') % rec.name)

    def action_reset(self):
        self.write({'state': 'draft'})

    def action_print(self):
        return self.env.ref('care_item_request.action_report_item_request').report_action(self)


class CareItemRequestLine(models.Model):
    _name = 'care.item.request.line'
    _description = 'سطر طلب أصناف'

    request_id = fields.Many2one('care.item.request', string='الطلب', required=True,
                                 ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='المنتج')
    name = fields.Char(string='الصنف', required=True)
    uom_name = fields.Char(string='الوحدة', default='وحدة')
    qty = fields.Float(string='الكمية', required=True, default=1.0)
    note = fields.Char(string='ملاحظة')

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id:
            self.name = self.product_id.display_name
            if self.product_id.uom_id:
                self.uom_name = self.product_id.uom_id.name
