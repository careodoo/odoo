{
    'name': 'Care Request Invoice',
    'version': '1.0',
    'description': 'Care Request Invoice',
    'summary': 'Care Request Invoice',
    'license': 'LGPL-3',
    'category': 'Uncategorized',
    'depends': [
        'base','account','product','uom','hr','project'
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/account_move.xml',
        'views/request_invoice.xml',
        'views/sequence.xml',
    ],
    'application': True,
}