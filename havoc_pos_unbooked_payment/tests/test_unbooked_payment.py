# -*- coding: utf-8 -*-
import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.exceptions import UserError, ValidationError


@odoo.tests.tagged('post_install', '-at_install')
class TestUnbookedPayment(TestPoSCommon):
    """Zahlart mit Schalter "Nicht verbuchen" im Sitzungsabschluss."""

    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.bargeld_pm = self.env['pos.payment.method'].create({
            'name': 'Bargeld (Test)',
            'journal_id': self.company_data['default_journal_bank'].id,
            'outstanding_account_id': self.outstanding_bank.id,
            'havoc_skip_accounting': True,
        })
        self.config.write({'payment_method_ids': [(4, self.bargeld_pm.id)]})
        self.product1 = self.create_product('Produkt 1', self.categ_basic, 10.0)
        self.product2 = self.create_product('Produkt 2', self.categ_basic, 20.0)

    # ------------------------------------------------------------------
    # Helfer
    # ------------------------------------------------------------------
    def _order(self, ui_data):
        order = self.env['pos.order'].search([('uuid', '=', ui_data['uuid'])])
        self.assertEqual(len(order), 1)
        return order

    def _income_total(self, move):
        lines = move.line_ids.filtered(lambda l: l.account_id.account_type == 'income')
        return sum(lines.mapped('credit')) - sum(lines.mapped('debit'))

    def _session_payments(self, method):
        return self.env['account.payment'].search([
            ('pos_session_id', '=', self.pos_session.id),
            ('pos_payment_method_id', '=', method.id),
        ])

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_field_loaded_in_pos_frontend(self):
        fields = self.env['pos.payment.method']._load_pos_data_fields(self.config)
        self.assertIn('havoc_skip_accounting', fields)

    def test_unbooked_order_excluded_from_session_entry(self):
        """Gemischte Sitzung: Bargeld-Bestellung fehlt in der Buchung, Bank-Bestellung nicht."""
        self.open_new_session()
        ui_bar = self.create_ui_order_data([(self.product1, 1)], payments=[(self.bargeld_pm, 10)])
        ui_bank = self.create_ui_order_data([(self.product2, 1)], payments=[(self.bank_pm1, 20)])
        self.env['pos.order'].sync_from_ui([ui_bar, ui_bank])
        order_bar, order_bank = self._order(ui_bar), self._order(ui_bank)

        self.assertTrue(order_bar._havoc_is_unbooked())
        self.assertFalse(order_bank._havoc_is_unbooked())
        self.assertEqual(self.pos_session.havoc_unbooked_count, 1)
        self.assertAlmostEqual(self.pos_session.havoc_unbooked_amount, 10)

        self.pos_session.action_pos_session_validate()
        self.assertEqual(self.pos_session.state, 'closed')

        move = self.pos_session.move_id
        self.assertTrue(move)
        self.assertEqual(move.state, 'posted')
        self.assertAlmostEqual(self._income_total(move), 20, msg='Nur die Bank-Bestellung darf Umsatz buchen')
        self.assertFalse(self._session_payments(self.bargeld_pm), 'Kein Zahlungseingang für Bargeld')
        self.assertTrue(self._session_payments(self.bank_pm1))

        self.assertTrue(order_bar.havoc_accounting_skipped)
        self.assertEqual(order_bar.state, 'paid', 'Nicht verbucht bleibt "Bezahlt"')
        self.assertFalse(order_bank.havoc_accounting_skipped)
        self.assertEqual(order_bank.state, 'done')

        # Markierung ist eingefroren: Schalter umlegen ändert Abgeschlossenes nicht mehr
        self.bargeld_pm.havoc_skip_accounting = False
        self.assertTrue(order_bar._havoc_is_unbooked())
        self.assertFalse(order_bank._havoc_is_unbooked())
        self.assertAlmostEqual(self.pos_session.havoc_unbooked_amount, 10)

        # Nachträgliche Rechnung aus dem Backend ist gesperrt
        with self.assertRaises(UserError):
            order_bar.action_pos_order_invoice()

    def test_session_with_only_unbooked_orders_closes_cleanly(self):
        self.open_new_session()
        ui = self.create_ui_order_data([(self.product1, 2)], payments=[(self.bargeld_pm, 20)])
        self.env['pos.order'].sync_from_ui([ui])

        self.pos_session.action_pos_session_validate()
        self.assertEqual(self.pos_session.state, 'closed')
        self.assertFalse(self.pos_session.move_id, 'Ohne buchbare Bestellung entsteht keine Buchung')
        self.assertFalse(self.env['account.payment'].search([('pos_session_id', '=', self.pos_session.id)]))

        order = self._order(ui)
        self.assertTrue(order.havoc_accounting_skipped)
        self.assertEqual(order.state, 'paid')

    def test_switch_off_books_normally(self):
        """Schalter aus: Bargeld wird wie jede andere Zahlart gebucht."""
        self.bargeld_pm.havoc_skip_accounting = False
        self.open_new_session()
        ui = self.create_ui_order_data([(self.product1, 1)], payments=[(self.bargeld_pm, 10)])
        self.env['pos.order'].sync_from_ui([ui])
        order = self._order(ui)
        self.assertFalse(order._havoc_is_unbooked())
        self.assertEqual(self.pos_session.havoc_unbooked_count, 0)

        self.pos_session.action_pos_session_validate()
        move = self.pos_session.move_id
        self.assertTrue(move)
        self.assertAlmostEqual(self._income_total(move), 10)
        payment = self._session_payments(self.bargeld_pm)
        self.assertEqual(len(payment), 1)
        self.assertAlmostEqual(payment.amount, 10)
        self.assertFalse(order.havoc_accounting_skipped)
        self.assertEqual(order.state, 'done')

    def test_switch_locked_while_session_open_and_applies_to_next_session(self):
        """Odoo sperrt Änderungen an der Zahlart bei offener Sitzung; der Schalter
        wird also zwischen den Sitzungen umgelegt und gilt ab der nächsten."""
        self.open_new_session()
        ui = self.create_ui_order_data([(self.product1, 1)], payments=[(self.bargeld_pm, 10)])
        self.env['pos.order'].sync_from_ui([ui])
        first_order = self._order(ui)

        with self.assertRaises(UserError):
            self.bargeld_pm.havoc_skip_accounting = False

        self.pos_session.action_pos_session_validate()
        self.assertTrue(first_order.havoc_accounting_skipped)
        self.assertFalse(self.pos_session.move_id)

        # Schalter aus, neue Sitzung: jetzt wird gebucht
        self.bargeld_pm.havoc_skip_accounting = False
        self.open_new_session()
        ui2 = self.create_ui_order_data([(self.product1, 1)], payments=[(self.bargeld_pm, 10)])
        self.env['pos.order'].sync_from_ui([ui2])
        second_order = self._order(ui2)
        self.assertFalse(second_order._havoc_is_unbooked())

        self.pos_session.action_pos_session_validate()
        self.assertTrue(self.pos_session.move_id)
        self.assertAlmostEqual(self._income_total(self.pos_session.move_id), 10)
        self.assertFalse(second_order.havoc_accounting_skipped)
        self.assertEqual(second_order.state, 'done')
        # die alte Bestellung bleibt unverändert markiert
        self.assertTrue(first_order._havoc_is_unbooked())

    def test_blacky_counter_search_covers_open_and_closed_sessions(self):
        """Menü "Blacky": suchbares Feld findet laufende und abgeschlossene Blacky-Bestellungen."""
        Order = self.env['pos.order']
        self.open_new_session()
        ui_bar = self.create_ui_order_data([(self.product1, 1)], payments=[(self.bargeld_pm, 10)])
        ui_bank = self.create_ui_order_data([(self.product2, 1)], payments=[(self.bank_pm1, 20)])
        Order.sync_from_ui([ui_bar, ui_bank])
        order_bar, order_bank = self._order(ui_bar), self._order(ui_bank)

        found = Order.search([('havoc_is_unbooked', '=', True), ('session_id', '=', self.pos_session.id)])
        self.assertEqual(found, order_bar, 'laufende Sitzung: Bargeld-Bestellung zählt als Blacky')
        self.assertIn(order_bank, Order.search([('havoc_is_unbooked', '=', False)]))
        self.assertTrue(order_bar.havoc_is_unbooked)
        self.assertFalse(order_bank.havoc_is_unbooked)

        self.pos_session.action_pos_session_validate()
        found = Order.search([('havoc_is_unbooked', '=', True), ('session_id', '=', self.pos_session.id)])
        self.assertEqual(found, order_bar, 'abgeschlossene Sitzung: Markierung zählt')
        self.assertNotIn(order_bank, Order.search([('havoc_is_unbooked', '=', True)]))

    def test_mixed_payment_rejected(self):
        self.open_new_session()
        ui = self.create_ui_order_data(
            [(self.product2, 1)], payments=[(self.bargeld_pm, 5), (self.bank_pm1, 15)])
        with self.assertRaises(ValidationError):
            self.env['pos.order'].sync_from_ui([ui])

    def test_invoice_from_pos_rejected(self):
        self.open_new_session()
        ui = self.create_ui_order_data(
            [(self.product1, 1)], payments=[(self.bargeld_pm, 10)],
            customer=self.customer, is_invoiced=True)
        with self.assertRaises(UserError):
            self.env['pos.order'].sync_from_ui([ui])
