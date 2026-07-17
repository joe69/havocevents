# -*- coding: utf-8 -*-
{
    'name': 'Havoc Mama Steuern',
    'summary': 'Steuerbericht für die österreichische Steuererklärung',
    'description': 'Menü "Mama Steuern" mit Umsatz- und Steuerbericht: '
                   'Umsatz gesamt, nach Verkaufskanal (Website, POS, Backend), '
                   'je Tickettyp und Steuern nach Satz inkl. UVA-Kennzahlen.',
    'category': 'Accounting',
    'version': '19.0.1.0.0',
    'author': 'wegot.vision',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'point_of_sale',
        'website_event_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/report_actions.xml',
        'report/report_templates.xml',
        'views/wizard_views.xml',
    ],
}
