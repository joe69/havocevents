# -*- coding: utf-8 -*-
from odoo import api, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    @api.constrains('payment_method_id', 'amount')
    def _check_havoc_unbooked_not_mixed(self):
        # Sicherheitsnetz zum Frontend-Check: eine nicht verbuchte Zahlart darf
        # nicht mit verbuchten Zahlarten in einer Bestellung gemischt werden,
        # sonst wäre die Sitzungsbuchung nicht mehr sauber abgrenzbar.
        self.pos_order_id._havoc_check_payment_mix()
