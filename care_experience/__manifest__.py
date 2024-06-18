# -*- coding: utf-8 -*-
{
    'name': "Care Experience",
    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    'description': """
        Long description of module's purpose
    """,
    'author': "My Company",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base', 'mail', 'care_proposal'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/care_experience.xml',
        'views/proposal.xml',
    ],
}
