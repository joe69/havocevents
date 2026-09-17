# -*- coding: utf-8 -*-
{
    'name': 'Havoc POS: Zahlart ohne Verbuchung',
    'summary': 'Kassen-Zahlarten, die nur mitgetrackt, aber nicht verbucht werden',
    'description': 'Schalter "Nicht verbuchen" an der Kassen-Zahlart: Bestellungen, die '
                   'vollständig mit so einer Zahlart bezahlt werden, erhalten einen normalen '
                   'Bon, werden beim Abschluss der Kassensitzung aber nicht in die Buchhaltung '
                   'übernommen (kein Umsatz, keine USt, kein Zahlungseingang). Sie bleiben im '
                   'Kassensystem nachvollziehbar (Filter "Nicht verbucht", Betrag je Sitzung).',
    'category': 'Sales/Point of Sale',
    'version': '19.0.1.0.0',
    'author': 'wegot.vision',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'views/pos_payment_method_views.xml',
        'views/pos_order_views.xml',
        'views/pos_payment_views.xml',
        'views/pos_session_views.xml',
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'havoc_pos_unbooked_payment/static/src/**/*',
        ],
    },
}
