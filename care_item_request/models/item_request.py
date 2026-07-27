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
    estimated_cost = fields.Monetary(string='تكلفة الطلب التقديرية', compute='_compute_cost',
                                     store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='العملة',
                                  default=lambda s: s.env.company.currency_id, readonly=True)

    # الميزانية الشهرية عبر مركز التكلفة — يُربط تلقائياً من إدارة المشروع
    cost_center_id = fields.Many2one('cost.center', string='مركز التكلفة',
                                     compute='_compute_cost_center', store=True, readonly=False, tracking=True)
    month_budget = fields.Monetary(string='ميزانية الشهر', compute='_compute_budget', currency_field='currency_id')
    month_used = fields.Monetary(string='المصروف هذا الشهر', compute='_compute_budget', currency_field='currency_id')
    month_remaining = fields.Monetary(string='المتبقّي للطلبات', compute='_compute_budget', currency_field='currency_id')
    over_budget = fields.Boolean(string='يتجاوز الميزانية', compute='_compute_budget')

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

    @api.depends('line_ids.subtotal')
    def _compute_cost(self):
        for rec in self:
            rec.estimated_cost = sum(rec.line_ids.mapped('subtotal'))

    @api.depends('department_id')
    def _compute_cost_center(self):
        """ربط تلقائي: مركز التكلفة المرتبط بنفس إدارة المشروع (أول مطابقة).
        لا يوجد ربط مباشر مشروع↔مركز، فنمرّ عبر hr.department."""
        CC = self.env.get('cost.center')
        for rec in self:
            if CC is not None and rec.department_id and not rec.cost_center_id:
                cc = self.env['cost.center'].sudo().search(
                    [('department_id', '=', rec.department_id.id)], limit=1)
                rec.cost_center_id = cc.id if cc else False
            elif not rec.department_id:
                rec.cost_center_id = rec.cost_center_id  # اترك التعديل اليدوي كما هو

    @api.depends('cost_center_id', 'request_date', 'estimated_cost', 'state')
    def _compute_budget(self):
        """المتبقّي = ميزانية شهر مركز التكلفة − (مصروف أوامر الشراء + مبالغ طلبات
        الأصناف المعتمدة لنفس المركز/الشهر)."""
        for rec in self:
            budget = used = 0.0
            cc = rec.cost_center_id
            d = rec.request_date or fields.Date.context_today(rec)
            if cc and 'month_ids' in cc._fields and d:
                month = cc.month_ids.filtered(
                    lambda m: m.date and m.date.month == d.month and m.date.year == d.year)[:1]
                if month:
                    budget = month.total_budget
                    used = month.used_budget  # مصروف أوامر الشراء
            # + مبالغ طلبات الأصناف المعتمدة لنفس المركز والشهر (عدا هذا السجل)
            if cc and d:
                others = self.sudo().search([
                    ('cost_center_id', '=', cc.id), ('state', '=', 'approved'),
                    ('id', '!=', rec.id or 0)])
                used += sum(
                    o.estimated_cost for o in others
                    if o.request_date and o.request_date.month == d.month
                    and o.request_date.year == d.year)
            rec.month_budget = budget
            rec.month_used = used
            rec.month_remaining = budget - used
            rec.over_budget = bool(budget) and (rec.estimated_cost > (budget - used))

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

    def action_duplicate(self):
        """نسخ طلب سابق كمسودّة جديدة قابلة للتعديل قبل الإتمام."""
        self.ensure_one()
        new = self.copy({
            'state': 'draft', 'name': '/', 'supply_id': False,
            'approved_by': False, 'approval_date': False, 'reject_reason': False,
            'request_date': fields.Date.context_today(self),
        })
        return {
            'type': 'ir.actions.act_window', 'res_model': 'care.item.request',
            'res_id': new.id, 'view_mode': 'form', 'target': 'current',
        }

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
    unit_price = fields.Float(string='سعر الوحدة')
    subtotal = fields.Monetary(string='الإجمالي', compute='_compute_subtotal', store=True,
                               currency_field='currency_id')
    currency_id = fields.Many2one(related='request_id.currency_id', string='العملة', store=True)
    note = fields.Char(string='ملاحظة')

    @api.depends('qty', 'unit_price')
    def _compute_subtotal(self):
        for l in self:
            l.subtotal = (l.qty or 0.0) * (l.unit_price or 0.0)

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id:
            self.name = self.product_id.display_name
            if self.product_id.uom_id:
                self.uom_name = self.product_id.uom_id.name
            # سعر افتراضي من المنتج (سعر البيع أو التكلفة)
            if not self.unit_price:
                self.unit_price = self.product_id.list_price or self.product_id.standard_price or 0.0
