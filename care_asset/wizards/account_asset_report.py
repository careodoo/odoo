from odoo import fields, models, api


class AccountAssetReport(models.TransientModel):
    _name = 'account.asset.report'
    _description = 'Account Asset Report'

    line_ids = fields.One2many('account.asset.report.line', 'asset_report_id')
    department_ids = fields.Many2many('hr.department', string='Departments')
    category_ids = fields.Many2many('account.asset.category', string='Categories')
    type = fields.Selection(selection=[
        ('sale', 'Sale: Revenue Recognition'),
        ('purchase', 'Purchase: Asset'),
        ('expense', 'Deferred Expense'),
    ])
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('open', 'Open'),
        ('paused', 'On Hold'), ('close', 'Closed'),
    ])
    # label
    print_format = fields.Selection([('2x7xprice', '2 x 7 with price')], string="Format", default='2x7xprice', required=True)
    custom_quantity = fields.Integer('Quantity', default=1, required=True)
    asset_ids = fields.Many2many('account.asset')
    rows = fields.Integer(default=7)
    columns = fields.Integer(default=2)

    def _prepare_report_data(self):
        xml_id = 'care_asset.action_report_asset_label'
        assets = self.line_ids.mapped('asset_id').ids
        data = {
            'active_model': 'account.asset',
            'quantity_by_asset': {a: self.custom_quantity for a in assets},
            'asset_wizard': self.id,
            'price_included': True,
        }
        return xml_id, data

    def process(self):
        self.ensure_one()
        xml_id, data = self._prepare_report_data()
        report_action = self.env.ref(xml_id).report_action(None, data=data)
        report_action.update({'close_on_report_download': True})
        return report_action

    def button_search(self):
        self.line_ids = [(5, 0, 0)]
        domain = []
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        if self.category_ids:
            domain.append(('category_id', 'in', self.category_ids.ids))
        if self.type:
            domain.append(('asset_type', '=', self.type))
        if self.state:
            domain.append(('state', '=', self.state))
        assets = self.env['account.asset'].search(domain)
        for asset in assets:
            self.env['account.asset.report.line'].create({
                'asset_id': asset.id,
                'asset_report_id': self.id
            })

        return {
            'name': 'Asset Report',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.asset.report',
            'target': 'new',
            'res_id': self.id,
        }

    def print_report(self):
        return self.env.ref("care_asset.action_asset_list_report").report_action(self)

    def print_report_xlsx(self):
        return self.env.ref("care_asset.action_asset_list_xlsx_report").report_action(self)


class AccountAssetReportLine(models.TransientModel):
    _name = 'account.asset.report.line'
    _description = 'Account Asset Report Line'

    asset_report_id = fields.Many2one('account.asset.report')
    asset_id = fields.Many2one('account.asset')
    name = fields.Char(related='asset_id.name')
    currency_id = fields.Many2one('res.currency', related='asset_id.currency_id', store=True)
    acquisition_date = fields.Date(related='asset_id.acquisition_date')
    original_value = fields.Monetary(related='asset_id.original_value')
    method = fields.Selection(related='asset_id.method')
    first_depreciation_date = fields.Date(related='asset_id.first_depreciation_date')
    value_residual = fields.Monetary(related='asset_id.value_residual')
    state = fields.Selection(related='asset_id.state')
    department_id = fields.Many2one('hr.department', related='asset_id.department_id')
    category_id = fields.Many2one('account.asset.category', related='asset_id.category_id')
    type = fields.Selection(related='asset_id.asset_type')
