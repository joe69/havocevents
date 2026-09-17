# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    havoc_unbooked_count = fields.Integer(
        string='Blacky: Bestellungen',
        compute='_compute_havoc_unbooked')
    havoc_unbooked_amount = fields.Monetary(
        string='Blacky: Betrag',
        compute='_compute_havoc_unbooked', currency_field='currency_id',
        help='Summe der Bestellungen dieser Sitzung, die nicht in die Buchhaltung '
             'übernommen werden bzw. wurden (Zahlart mit Schalter "Nicht verbuchen").')

    @api.depends('order_ids.state', 'order_ids.amount_total',
                 'order_ids.havoc_accounting_skipped',
                 'order_ids.payment_ids.payment_method_id.havoc_skip_accounting')
    def _compute_havoc_unbooked(self):
        for session in self:
            orders = session.order_ids.filtered(
                lambda o: o.state not in ('draft', 'cancel') and o._havoc_is_unbooked())
            session.havoc_unbooked_count = len(orders)
            session.havoc_unbooked_amount = sum(orders.mapped('amount_total'))

    # ------------------------------------------------------------------
    # Sitzungsabschluss: nicht verbuchte Bestellungen aus der Buchung nehmen
    # ------------------------------------------------------------------
    def _get_closed_orders(self):
        # Odoo sammelt die zu buchenden Beträge in `_accumulate_amounts` über
        # `_get_closed_orders()`. Nur innerhalb von `_create_account_move`
        # (Kontext-Flag) werden nicht verbuchte Bestellungen ausgeblendet;
        # Lagerbuchungen, Zähler usw. sehen weiterhin alle Bestellungen.
        orders = super()._get_closed_orders()
        if self.env.context.get('havoc_exclude_unbooked'):
            orders = orders.filtered(lambda o: not o._havoc_is_unbooked())
        return orders

    def _create_account_move(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        unbooked = self._get_closed_orders().filtered(lambda o: o._havoc_is_unbooked())
        session = self.with_context(havoc_exclude_unbooked=True)
        data = super(PosSession, session)._create_account_move(
            balancing_account, amount_to_balance, bank_payment_method_diffs)
        if unbooked:
            # Markierung einfrieren: ab jetzt zählt nicht mehr der Schalter,
            # sondern was beim Abschluss tatsächlich (nicht) gebucht wurde.
            unbooked.write({'havoc_accounting_skipped': True})
        return data

    def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        res = super()._validate_session(balancing_account, amount_to_balance, bank_payment_method_diffs)
        # Odoo setzt beim Abschluss alle bezahlten Bestellungen auf "Gebucht".
        # Nicht verbuchte Bestellungen bleiben ehrlicherweise auf "Bezahlt".
        self.sudo().order_ids.filtered(
            lambda o: o.havoc_accounting_skipped and o.state == 'done'
        ).write({'state': 'paid'})
        return res
