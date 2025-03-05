{
    'name': 'Care Request Invoice',
    'version': '1.0',
    'description': 'Care Request Invoice',
    'summary': 'Care Request Invoice',
    'license': 'LGPL-3',
    'category': 'Uncategorized',
    'depends': [
        'base','account','product','uom','hr','project','care_experience','care_proposal', 'care_invoice_report'
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/activity_type.xml',
        'wizard/insert_pricelist_item_wizard.xml',
        'wizard/refusal_reason_wizard_view.xml',
        'views/account_move.xml',
        'views/product_pricelist.xml',
        'views/request_invoice.xml',
        'views/sequence.xml',
    ],
    'application': True,
}