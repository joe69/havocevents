# -*- coding: utf-8 -*-
{
    'name': 'Havoc Ticket-Verwaltungsgebühr',
    'summary': 'Verwaltungsgebühr und Zusatzpakete (z. B. VIP-Package) für Event-Tickets',
    'description': 'Schlägt beim Ticketkauf automatisch eine einstellbare '
                   'prozentuale Verwaltungsgebühr auf Event-Tickets auf.',
    'category': 'Website/Website',
    'version': '19.0.1.0.0',
    'author': 'wegot.vision',
    'license': 'LGPL-3',
    'depends': [
        'website_event_sale',
    ],
    'data': [
        'data/product_data.xml',
        'views/res_config_settings_views.xml',
        'views/event_ticket_views.xml',
        'views/event_question_views.xml',
        'views/website_event_templates.xml',
        'report/ticket_report_templates.xml',
    ],
}
