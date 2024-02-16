from odoo import fields, models, api
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    signature_users = fields.Many2many('res.users', compute='compute_signature_users', store=True)

    @api.depends('signature_lines')
    def compute_signature_users(self):
        for rec in self:
            rec.signature_users = False
            if rec.signature_lines:
                rec.signature_users = [(6, 0, [u.id for u in rec.signature_lines.mapped('employee_id').mapped('user_id')])]

    @api.model
    def create(self, vals):
        res = super(PurchaseOrder, self).create(vals)
        if res.amount_total and res.cost_center_id:
            if res.cost_center_id.purchase_limit and res.amount_total > res.cost_center_id.purchase_limit:
                raise ValidationError("You have exceeded purchase limit for {} cost center".format(res.cost_center_id.name))
        return res

    def write(self, vals):
        res = super().write(vals)
        if self.amount_total and self.cost_center_id:
            if self.cost_center_id.purchase_limit and self.amount_total > self.cost_center_id.purchase_limit:
                raise ValidationError(
                    "You have exceeded purchase limit for {} cost center".format(self.cost_center_id.name))
        return res

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        if self.cost_center_id and self.date_order and self.cost_center_id.month_ids and self.state in ['purchase', 'done']:
            month = False
            if self.cost_center_id.type == 'total' and self.cost_center_id.month_ids:
                if self.cost_center_id.budget_start_date and self.cost_center_id.budget_end_date:
                    if self.cost_center_id.budget_start_date <= self.date_order.date() <= self.cost_center_id.budget_end_date:
                        month = self.cost_center_id.month_ids[0]
            elif self.cost_center_id.type == 'month':
                month = self.cost_center_id.month_ids.filtered(
                    lambda m: m.date.month == self.date_order.month and m.date.year == self.date_order.year
                )
            elif self.cost_center_id.type == 'annual':
                month = self.cost_center_id.month_ids.filtered(
                    lambda m: m.date.year == self.date_order.year
                )
            if not month:
                raise ValidationError(f"Cost Center is not covering {self.date_order}!")
            if (month.used_budget + self.amount_total) > month.total_budget:
                raise ValidationError("Used budget can't exceed total budget for {}!".format(month.date_string))
            month.used_budget += self.amount_total
            month.purchase_order_ids = [(4, self.id)]
        return res

    def button_cancel(self):
        if self.state in ['purchase', 'done'] and self.date_order and self.cost_center_id.month_ids:
            month = False
            if self.cost_center_id.type == 'total' and self.cost_center_id.month_ids:
                if self.cost_center_id.budget_start_date and self.cost_center_id.budget_end_date:
                    if self.cost_center_id.budget_start_date <= self.date_order.date() <= self.cost_center_id.budget_end_date:
                        month = self.cost_center_id.month_ids[0]
            elif self.cost_center_id.type == 'month':
                month = self.cost_center_id.month_ids.filtered(
                    lambda m: m.date.month == self.date_order.month and m.date.year == self.date_order.year
                )
            elif self.cost_center_id.type == 'annual':
                month = self.cost_center_id.month_ids.filtered(
                    lambda m: m.date.year == self.date_order.year
                )
            if not month:
                raise ValidationError(f"Cost Center is not covering {self.date_order}!")
            month.used_budget -= self.amount_total
            month.purchase_order_ids = [(3, self.id)]
        res = super(PurchaseOrder, self).button_cancel()
        return res
