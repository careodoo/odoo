# -*- coding: utf-8 -*-
{
    'name': 'CARE — تنظيف خزانات المياه (Water Tanks)',
    'summary': 'سجل الخزانات، دورة تنظيف موثّقة بشهادة وتحليل مخبري',
    'version': '17.0.1.0.0', 'author': 'CARE', 'license': 'LGPL-3',
    'depends': ['care_cafm', 'hr'],
    'data': ['security/ir.model.access.csv', 'data/tank_data.xml', 'views/tank_views.xml'],
    'installable': True, 'application': True,
}
