# -*- coding: utf-8 -*-
{
    'name': "SaaS F&B Enterprise",
    'summary': 'Solusi POS, Inventaris, dan CRM Terintegrasi',
    'description': 'Modul untuk menggantikan sistem lama dengan ekosistem POS, manajemen inventaris, dan manajemen komplain yang terintegrasi.',
    'sequence': -100,
    'author': "Kelompok IF3141",
    'category': 'Sales',
    'version': '1.0',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/menus.xml',
        'views/inventory_views.xml',
        'views/order_views.xml',
        'views/complaint_views.xml',
        'views/menu_views.xml',
        'views/reservation_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}