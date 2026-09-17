# -*- coding: utf-8 -*-
{
    'name': 'Havoc Kassen-Dashboard',
    'summary': 'Live-Übersicht der aktuellen Zahlen aller Kassen (inkl. Blacky)',
    'description': 'Kleines Dashboard unter Kassensystem › Berichte: je Kasse Bestellungen, '
                   'verbuchter Umsatz, Blacky (nicht verbuchte Zahlart) und eine Spalte je '
                   'Zahlart – umschaltbar zwischen laufender/letzter Sitzung, heute und gesamt. '
                   'Dazu die Top-Produkte. Aktualisiert sich automatisch, auch am Handy lesbar.',
    'category': 'Sales/Point of Sale',
    'version': '19.0.1.0.0',
    'author': 'wegot.vision',
    'license': 'LGPL-3',
    'depends': [
        'havoc_pos_unbooked_payment',
    ],
    'data': [
        'views/dashboard_templates.xml',
        'views/menu.xml',
    ],
}
