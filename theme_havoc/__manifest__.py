# -*- coding: utf-8 -*-
{
    'name': 'Havoc Theme',
    'description': 'Schwarz/Weiß Event-Theme für HAVOC — Ticketverkauf über Odoo Events.',
    'summary': 'Black & white event theme with red accents for havoc.events',
    'category': 'Theme/Entertainment',
    'version': '19.0.1.0.0',
    'author': 'wegot.vision',
    'license': 'LGPL-3',
    'depends': [
        'website_event_sale',
    ],
    'data': [
        'data/website.xml',
        'views/homepage.xml',
        'views/website_sale_templates.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'theme_havoc/static/src/scss/primary_variables.scss',
        ],
        'web._assets_frontend_helpers': [
            ('prepend', 'theme_havoc/static/src/scss/bootstrap_overridden.scss'),
        ],
        'web.assets_frontend': [
            'theme_havoc/static/src/scss/theme.scss',
        ],
    },
    'images': [
        'static/description/cover.png',
    ],
}
