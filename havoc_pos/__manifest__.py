# -*- coding: utf-8 -*-
{
    'name': 'Havoc POS Stammdaten',
    'summary': 'Kassen, Kategorien, Produkte und Zahlart Bargeld für HAVOC-Events',
    'description': 'Legt die Kassenstruktur laut Preisliste an: POS-Kategorien '
                   '(Essen, Getränke, Merchandise, Garderobe, Abendkassa) mit allen '
                   'Produkten, fünf Kassen (2x Getränke, Garderobe, Merchandise, Eintritt) '
                   'und die Zahlart "Bargeld", die standardmäßig nur mitgetrackt, aber '
                   'nicht verbucht wird (Schalter an der Zahlart).',
    'category': 'Sales/Point of Sale',
    'version': '19.0.1.0.0',
    'author': 'wegot.vision',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'havoc_pos_unbooked_payment',
    ],
    'data': [
        'data/pos_category_data.xml',
        'data/product_data.xml',
        'data/payment_method_data.xml',
        'data/pos_config_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
}
