# -*- coding: utf-8 -*-
import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestHavocPosDashboard(TestPoSCommon):

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

    def _row_for_config(self, data):
        rows = [r for r in data['rows'] if r['config'] == self.config]
        self.assertEqual(len(rows), 1)
        return rows[0]

    def test_dashboard_numbers(self):
        Dashboard = self.env['havoc.pos.dashboard']
        data = Dashboard._get_data('session')
        row = self._row_for_config(data)
        self.assertEqual(row['orders'], 0)
        self.assertEqual(row['session_label'], 'noch keine Sitzung')

        self.open_new_session()
        self.env['pos.order'].sync_from_ui([
            self.create_ui_order_data([(self.product1, 3)], payments=[(self.bargeld_pm, 30)]),
            self.create_ui_order_data([(self.product2, 1)], payments=[(self.bank_pm1, 20)]),
        ])

        for period in ('session', 'today', 'all'):
            data = Dashboard._get_data(period)
            row = self._row_for_config(data)
            self.assertEqual(row['orders'], 2, period)
            self.assertAlmostEqual(row['booked'], 20, msg=period)
            self.assertAlmostEqual(row['blacky'], 30, msg=period)
            self.assertAlmostEqual(row['total'], 50, msg=period)
            self.assertAlmostEqual(row['payments'][self.bargeld_pm], 30, msg=period)
            self.assertAlmostEqual(row['payments'][self.bank_pm1], 20, msg=period)
            self.assertIn(self.bargeld_pm, data['methods'])
            self.assertAlmostEqual(data['totals']['payments'][self.bargeld_pm], 30, msg=period)
            top = data['top_products']
            self.assertEqual(top[0]['product'], self.product1)
            self.assertAlmostEqual(top[0]['qty'], 3)
        self.assertTrue(self._row_for_config(Dashboard._get_data('session'))['session_label'].startswith('offen seit'))

        # nach dem Abschluss: letzte Sitzung bleibt sichtbar, Blacky bleibt Blacky
        self.pos_session.action_pos_session_validate()
        data = Dashboard._get_data('session')
        row = self._row_for_config(data)
        self.assertTrue(row['session_label'].startswith('geschlossen'))
        self.assertAlmostEqual(row['blacky'], 30)
        self.assertAlmostEqual(row['booked'], 20)

    def test_unknown_period_falls_back(self):
        self.assertEqual(self.env['havoc.pos.dashboard']._get_data('xyz')['period'], 'session')


@odoo.tests.tagged('post_install', '-at_install')
class TestHavocPosDashboardHttp(odoo.tests.HttpCase):

    def test_page_renders_for_pos_user(self):
        self.authenticate('admin', 'admin')
        response = self.url_open('/havoc/kassen?period=all')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Kassen-Dashboard', response.text)
        self.assertIn('Gesamt', response.text)
