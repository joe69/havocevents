# -*- coding: utf-8 -*-
import odoo
from odoo import fields
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestTaxReportUnbooked(TestPoSCommon):
    """Nicht verbuchte POS-Bestellungen zählen im Steuerbericht nicht als Umsatz."""

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

    def _report_values(self):
        today = fields.Date.context_today(self.env.user)
        wizard = self.env['havoc.tax.report.wizard'].create({'date_from': today, 'date_to': today})
        return self.env['report.havoc_tax_report.report_template']._get_report_values(wizard.ids)

    def _assert_only_bank_counted(self):
        values = self._report_values()
        pos_channel = dict(values['channels'])['POS-Verkauf (Abendkassa)']
        self.assertEqual(pos_channel['count'], 1)
        self.assertAlmostEqual(pos_channel['total'], 20)
        self.assertAlmostEqual(pos_channel['blacky'], 10, msg='Blacky-Spalte zeigt den Bargeld-Brutto')
        self.assertAlmostEqual(values['total']['blacky'], 10)
        self.assertEqual(values['blacky_count'], 1)
        pay_rows = {row['name']: row for row in values['pos_pay_rows']}
        self.assertEqual(pay_rows[self.bargeld_pm.name]['count'], 0)
        self.assertAlmostEqual(pay_rows[self.bargeld_pm.name]['amount'], 0)
        self.assertAlmostEqual(pay_rows[self.bargeld_pm.name]['blacky'], 10)
        self.assertAlmostEqual(pay_rows[self.bank_pm1.name]['amount'], 20)
        self.assertAlmostEqual(pay_rows[self.bank_pm1.name]['blacky'], 0)

    def test_pos_revenue_excludes_unbooked_orders(self):
        self.open_new_session()
        orders = [
            self.create_ui_order_data([(self.product1, 1)], payments=[(self.bargeld_pm, 10)]),
            self.create_ui_order_data([(self.product2, 1)], payments=[(self.bank_pm1, 20)]),
        ]
        self.env['pos.order'].sync_from_ui(orders)

        # vor dem Abschluss (Schalterstand) ...
        self._assert_only_bank_counted()
        # ... und nach dem Abschluss (eingefrorene Markierung)
        self.pos_session.action_pos_session_validate()
        self._assert_only_bank_counted()
