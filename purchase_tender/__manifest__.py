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
        'data/mail_templates.xml',
        'data/tender_cron.xml',
        'views/purchase_tender.xml',
        'views/bid_type.xml',
        'views/tender_follower.xml',
        'views/tender_record.xml',
        'views/res_partner.xml',
        'views/res_config_settings.xml',
        'views/competitor_analysis.xml',
        'views/dashboard.xml',
        'reports/tender_bid_result.xml',
        'reports/purchase_tender.xml',
        'reports/tender_summary.xml',
        'reports/tender_requirements.xml',
        'reports/competitor_profile.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'purchase_tender/static/src/dashboard/tender_dashboard.scss',
            'purchase_tender/static/src/dashboard/tender_dashboard.js',
            'purchase_tender/static/src/dashboard/tender_dashboard.xml',
            'purchase_tender/static/src/kanban/tender_kanban.scss',
            'purchase_tender/static/src/competitor_dashboard/competitor_dashboard.js',
            'purchase_tender/static/src/competitor_dashboard/competitor_dashboard.xml',
        ],
    },
}
