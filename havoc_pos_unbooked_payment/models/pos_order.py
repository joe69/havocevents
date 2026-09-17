# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero


class PosOrder(models.Model):
    _inherit = 'pos.order'

    havoc_accounting_skipped = fields.Boolean(
        string='Blacky (nicht verbucht)',
        readonly=True, copy=False,
        help='Diese Bestellung wurde beim Abschluss der Kassensitzung nicht in die '
             'Buchhaltung übernommen (Zahlart mit Schalter "Nicht verbuchen").',
    )
    havoc_is_unbooked = fields.Boolean(
        string='Blacky',
        compute='_compute_havoc_is_unbooked', search='_search_havoc_is_unbooked',
        help='Läuft als Blacky: bereits nicht verbucht (abgeschlossene Sitzung) oder '
             'wird beim Abschluss der laufenden Sitzung nicht verbucht.',
    )

    @api.depends('havoc_accounting_skipped', 'session_id.state',
                 'payment_ids.amount', 'payment_ids.payment_method_id.havoc_skip_accounting')
    def _compute_havoc_is_unbooked(self):
        for order in self:
            order.havoc_is_unbooked = order._havoc_is_unbooked()

    def _search_havoc_is_unbooked(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise NotImplementedError(_('Nur =/!= True/False werden unterstützt.'))
        # abgeschlossen und markiert, oder offen und (ausschließlich) mit
        # nicht verbuchter Zahlart bezahlt — Mischzahlungen sind ohnehin gesperrt
        domain = [
            '|',
            ('havoc_accounting_skipped', '=', True),
            '&', '&',
            ('session_id.state', '!=', 'closed'),
            ('state', 'not in', ('draft', 'cancel')),
            ('payment_ids.payment_method_id.havoc_skip_accounting', '=', True),
        ]
        if (operator == '=') != value:
            domain = ['!'] + domain
        return domain

    # ------------------------------------------------------------------
    # Helfer
    # ------------------------------------------------------------------
    def _havoc_relevant_payments(self):
        """Zahlungen mit Betrag ungleich null (Nullzeilen sind buchhalterisch irrelevant)."""
        self.ensure_one()
        rounding = self.currency_id.rounding or 0.01
        return self.payment_ids.filtered(
            lambda p: not float_is_zero(p.amount, precision_rounding=rounding))

    def _havoc_is_unbooked(self):
        """True, wenn die Bestellung nicht verbucht wurde bzw. beim
        Sitzungsabschluss nicht verbucht wird.

        Abgeschlossene Sitzungen: entscheidend ist die beim Abschluss gesetzte
        Markierung. Offene Sitzungen: entscheidend ist der aktuelle Stand des
        Schalters an der Zahlart, d.h. der Schalter kann bis zum Abschluss der
        Sitzung noch umgelegt werden.
        """
        self.ensure_one()
        if self.havoc_accounting_skipped:
            return True
        if self.session_id.state == 'closed':
            return False
        payments = self._havoc_relevant_payments()
        return bool(payments) and all(
            p.payment_method_id.havoc_skip_accounting for p in payments)

    def _havoc_check_payment_mix(self):
        for order in self:
            payments = order._havoc_relevant_payments()
            unbooked = payments.filtered('payment_method_id.havoc_skip_accounting')
            if unbooked and unbooked != payments:
                raise ValidationError(_(
                    'Bestellung %(order)s: Die Zahlart "%(method)s" wird nicht verbucht '
                    'und kann daher nicht mit anderen Zahlarten kombiniert werden.',
                    order=order.name,
                    method=', '.join(unbooked.payment_method_id.mapped('name')),
                ))

    # ------------------------------------------------------------------
    # Rechnung sperren
    # ------------------------------------------------------------------
    def _generate_pos_order_invoice(self):
        blocked = self.filtered(lambda o: o._havoc_is_unbooked())
        if blocked:
            raise UserError(_(
                'Die Bestellung(en) %(orders)s wurden mit einer Zahlart bezahlt, die '
                'nicht verbucht wird, und können daher nicht fakturiert werden.',
                orders=', '.join(blocked.mapped('name')),
            ))
        return super()._generate_pos_order_invoice()
