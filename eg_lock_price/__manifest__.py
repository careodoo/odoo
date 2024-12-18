{
    'name': 'Lock Price',
    'version': '17.0',
    'category': 'Sales/Sales',
    'summary': 'Make Readonly sales price in Sale Order and Account Invoice',
    'author': 'INKERP',
    'website': 'https://www.INKERP.com/',
    'depends': ['sale', 'account', 'product'],
    
    'data': [
        'security/security.xml',
        'views/product_template_view.xml',
        'views/product_product_view.xml',
        'views/sale_order_view.xml',
        'views/account_move_view.xml',
        'views/purchase_order_view.xml',
    ],
    
    'images': ['static/description/banner.png'],
    'license': "OPL-1",
    'installable': True,
    'application': True,
    'auto_install': False,
}
