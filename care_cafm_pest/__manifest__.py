# -*- coding: utf-8 -*-
{
    'name': 'CARE — مكافحة الحشرات (Pest Control)',
    'summary': 'برامج مكافحة دورية، شبكة محطات مرقّمة، سجل مبيدات معتمدة، وزيارات موثّقة',
    'version': '17.0.1.0.0',
    'author': 'CARE',
    'license': 'LGPL-3',
    'depends': ['care_cafm', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/pest_data.xml',
        'views/pest_views.xml',
    ],
    'installable': True,
    'application': True,
}
