{
    "name": "On Hand Quantity in Purchase Order",
    "summary": "Display on hand quantity and forecasted qty in purchase order line.",
    "version": "17.0",
    "category": 'Purchase',
    'author': 'INKERP',
    'website': "https://www.INKERP.com",
    "description": "This app will use to display on hand quantity and forecasted qty in purchase order line.",
    "depends": [
        'purchase',
    ],
    
    "data": [
        'views/purchase_order_view.xml',
        'report/purchase_order_report.xml'
    ],
    
    'images': ['static/description/banner.png'],
    'license': "OPL-1",
    'installable': True,
    'auto_install': False,
    'application': True,
}
