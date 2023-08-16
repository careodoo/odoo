# -*- coding: utf-8 -*-

from collections import defaultdict
from odoo import _, models


def _prepare_asset_report_data(env, data):
    Asset = env['account.asset'].with_context(display_default_code=False)
    total = 0
    quantity_by_asset = defaultdict(list)
    for p, q in data.get('quantity_by_asset').items():
        asset = Asset.browse(int(p))
        quantity_by_asset[asset].append((asset.barcode, q))
        total += q

    asset_wizard = env['account.asset.report'].browse(data.get('asset_wizard'))
    if not asset_wizard:
        return {}

    return {
        'quantity': quantity_by_asset,
        'rows': asset_wizard.rows,
        'columns': asset_wizard.columns,
        # 'page_numbers': (total - 1) // (asset_wizard.rows * asset_wizard.columns) + 1,
        'page_numbers': total,
        'price_included': data.get('price_included'),
    }


class AssetLabelReport(models.AbstractModel):
    _name = 'report.care_asset.report_asset_label'
    _description = 'Asset Label Report'

    def _get_report_values(self, docids, data):
        return _prepare_asset_report_data(self.env, data)
