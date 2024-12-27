{
    "name": "On Hand Quantity in Purchase Order",
    "version": "17.0",
    "category": 'Purchase',
    "summary": "Display on hand quantity and forecasted qty in purchase order line.",
    'author': 'INKERP',
    'website': "https://www.INKERP.com",
    "depends": ['purchase'],

    "data": [
        'views/purchase_order_view.xml',
        # 'report/purchase_order_report.xml'
    ],

    'images': ['static/description/banner.png'],
    'license': "OPL-1",
    'installable': True,
    'auto_install': False,
    'application': True,
}
