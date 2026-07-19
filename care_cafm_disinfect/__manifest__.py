# -*- coding: utf-8 -*-
{
    'name': 'CARE — التعقيم (Disinfection)',
    'summary': 'جولات تعقيم موثّقة بزمن التلامس، مطهّرات معتمدة، ومسح ATP',
    'version': '17.0.1.0.0', 'author': 'CARE', 'license': 'LGPL-3',
    'depends': ['care_cafm', 'hr'],
    'data': ['security/ir.model.access.csv', 'data/disinfect_data.xml', 'views/disinfect_views.xml'],
    'installable': True, 'application': True,
}
