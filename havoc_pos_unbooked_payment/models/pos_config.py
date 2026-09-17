# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    havoc_current_booked_amount = fields.Monetary(
        string='Umsatz laufende Sitzung', compute='_compute_havoc_current',
        currency_field='currency_id',
        help='Brutto-Umsatz der laufenden Sitzung, der beim Abschluss verbucht wird.')
    havoc_current_blacky_amount = fields.Monetary(
        string='Blacky laufende Sitzung', compute='_compute_havoc_current',
        currency_field='currency_id',
        help='Brutto-Summe der Bestellungen der laufenden Sitzung mit einer Zahlart '
             'mit Schalter "Nicht verbuchen".')

    @api.depends('current_session_id')
    def _compute_havoc_current(self):
        for config in self:
            session = config.current_session_id
            orders = session.order_ids.filtered(lambda o: o.state not in ('draft', 'cancel'))
            blacky = orders.filtered(lambda o: o._havoc_is_unbooked())
            config.havoc_current_blacky_amount = sum(blacky.mapped('amount_total'))
            config.havoc_current_booked_amount = sum((orders - blacky).mapped('amount_total'))
