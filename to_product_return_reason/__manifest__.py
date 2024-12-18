{
    'name': 'Product Return Reasons',
    'name_vi_VN': 'Lý do trả hàng',

    'summary': 'Base application for product return reasons management',
    'summary_vi_VN': 'Ứng dụng cơ sở cho việc quản lý lý do trả hàng',

    'description': """
Demo video: `Product Return Reasons <https://youtu.be/EHyaV14ikSw>`_

Summary
=======

This technical module offers a new model for users to define return reason. A return reason consists of the following information:

1. Name: The name of the Return Reason, for example: Bad quality, Customer changed mind, etc.
2. Description: Description of the reason.

Editions Supported
==================
1. Community Edition
2. Enterprise Edition

    """,
    'description_vi_VN': """
Demo video: `Lý do trả hàng <https://youtu.be/EHyaV14ikSw>`_

Tổng quan
=========

Đây là module kỹ thuật tạo ra một model mới để định nghĩa các lý do trả hàng. Một lý do trả hàng bao gồm các thông tin sau:

1. Tên: Tên của lý do trả hàng, ví dụ: Chất lượng kém, khách hàng đổi ý, v.v.
2. Mô tả: Mô tả lý do.

Ấn bản hỗ trợ
==================
1. Ấn bản cộng đồng
2. Ấn bản doanh nghiệp

    """,

    'version': '1.0.0',
    'author': 'T.V.T Marine Automation (aka TVTMA),Viindoo',
    'website': 'https://viindoo.com/apps/app/17.0/to_product_return_reason',
    'live_test_url': "https://v17demo-int.viindoo.com",
    'live_test_url_vi_VN': "https://v17demo-vn.viindoo.com",
    'demo_video_url': "https://youtu.be/EHyaV14ikSw",
    'support': 'apps.support@viindoo.com',
    'sequence': 30,
    'category': 'Sales',
    'depends': ['product'],
    'data': [
        'security/module_security.xml',
        'security/ir.model.access.csv',
        'views/products_return_reason.xml',
    ],
    'demo': [
        'data/data_demo.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'price': 0.0,
    'currency': 'EUR',
    'license': 'OPL-1',
}
