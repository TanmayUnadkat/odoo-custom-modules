{
    'name': 'Stock Newsletter Alert',
    'version': '19.0.1.0.0',
    'summary': 'Notify newsletter subscribers on low stock and restock',
    'category': 'Website',
    'author': 'Custom',
    'depends': ['product', 'website', 'stock', 'mass_mailing', 'website_mass_mailing'],
    'data': [
        'data/mailing_list_data.xml',
        'data/cron_data.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
