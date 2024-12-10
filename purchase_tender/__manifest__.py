{
    'name':
        "purchase Tender",
    'version':
        '17.0.0.0.0',
    'depends': ['base', 'purchase_requisition'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'data/tender.xml',
        'views/purchase_tender.xml',
        'views/bid_type.xml',
        'views/tender_follower.xml',
        'views/tender_record.xml',
        'reports/tender_bid_result.xml',
        'reports/purchase_tender.xml',
    ],
}
