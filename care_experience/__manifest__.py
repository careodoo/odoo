# -*- coding: utf-8 -*-
{
    'name': "Care Experience",
    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    'author': "My Company",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '17.0.0.0',
    'license': 'LGPL-3',    
    'depends': ['base', 'mail', 'hr', 'project', 'care_proposal'],
    'data': [
        'security/ir.model.access.csv',
        'security/experience_security_groups.xml',
        'data/cron.xml',
        'data/sequence.xml',
        'views/care_experience.xml',
        'views/proposal.xml',
    ],
}
