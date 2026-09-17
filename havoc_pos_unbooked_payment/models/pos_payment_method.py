# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    havoc_skip_accounting = fields.Boolean(
        string='Nicht verbuchen (nur mittracken)',
        help='Bestellungen, die vollständig mit dieser Zahlart bezahlt werden, '
             'werden beim Abschluss der Kassensitzung nicht in die Buchhaltung '
             'übernommen: kein Umsatz, keine USt, kein Zahlungseingang. '
             'Der Bon wird ganz normal gedruckt; die Bestellung bleibt im '
             'Kassensystem erhalten und ist über den Filter "Nicht verbucht" '
             'auswertbar. Solche Bestellungen können nicht fakturiert und nicht '
             'mit anderen Zahlarten kombiniert werden. '
             'Der Schalter lässt sich (wie alle Zahlart-Einstellungen) nur ändern, '
             'solange keine Kassensitzung mit dieser Zahlart geöffnet ist; er gilt '
             'dann für alle danach eröffneten Sitzungen.',
    )

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['havoc_skip_accounting']
