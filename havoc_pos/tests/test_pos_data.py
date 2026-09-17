# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestHavocPosData(TransactionCase):

    def _ref(self, xmlid):
        return self.env.ref(f'havoc_pos.{xmlid}')

    def test_pos_configs(self):
        expected = {
            'pos_config_getraenke_1': {'Getränke', 'Essen'},
            'pos_config_getraenke_2': {'Getränke', 'Essen'},
            'pos_config_garderobe': {'Garderobe', 'Essen'},
            'pos_config_merchandise': {'Merchandise'},
            'pos_config_eintritt': {'Abendkassa'},
        }
        bargeld = self._ref('payment_method_bargeld')
        for xmlid, categories in expected.items():
            config = self._ref(xmlid)
            self.assertTrue(config.limit_categories, xmlid)
            self.assertEqual(set(config.iface_available_categ_ids.mapped('name')), categories, xmlid)
            self.assertIn(bargeld, config.payment_method_ids, xmlid)
            self.assertFalse(config.cash_control, 'Bargeld ist bewusst keine Bar-Zahlart mit Kassensturz')

    def test_bargeld_payment_method(self):
        bargeld = self._ref('payment_method_bargeld')
        self.assertTrue(bargeld.havoc_skip_accounting)
        self.assertEqual(bargeld.type, 'bank')
        self.assertFalse(bargeld.is_cash_count)
        self.assertEqual(bargeld.journal_id, self._ref('journal_bargeld'))
        self.assertTrue(bargeld.outstanding_account_id, 'Hook muss das Outstanding-Konto setzen')
        self.assertEqual(len(bargeld.config_ids), 5)

    def test_products(self):
        data = self.env['ir.model.data'].search([
            ('module', '=', 'havoc_pos'), ('model', '=', 'product.product')])
        products = self.env['product.product'].browse(data.mapped('res_id'))
        self.assertEqual(len(products), 35)
        self.assertTrue(all(products.mapped('available_in_pos')))
        self.assertTrue(all(p.pos_categ_ids for p in products))

        prices = {
            'product_schnitzelsemmel': 6, 'product_hoodie': 75, 'product_schluesselanhaenger': 5,
            'product_garderobe': 3, 'product_ticket_weekend': 50, 'product_ticket_freitag': 25,
            'product_ticket_samstag': 35, 'product_bier': 5, 'product_soda': 3,
            'product_vodka_bull': 7, 'product_klopfer': 3, 'product_flasche': 90,
            'product_zigaretten': 12, 'product_pfand_becher': 2,
        }
        for xmlid, price in prices.items():
            self.assertAlmostEqual(self._ref(xmlid).list_price, price, msg=xmlid)

        combo = self._ref('product_hoodie_superdeal')
        self.assertEqual(combo.type, 'combo')
        self.assertEqual(len(combo.combo_ids), 2)
        self.assertEqual(
            set(self._ref('combo_gratis_accessoire').combo_item_ids.mapped('product_id.name')),
            {'Fächer', 'Schlüsselanhänger', 'Fahne', 'Beutel'})

    def test_taxes_by_group(self):
        """Steuersätze sind vom Kontenplan der Firma abhängig; wenn welche gesetzt
        wurden, müssen es die richtigen Gruppen sein."""
        company = self.env.company

        def rate(xmlid):
            taxes = self._ref(xmlid).taxes_id.filtered(lambda t: t.company_id == company)
            return set(taxes.mapped('amount'))

        food, ticket, drink = rate('product_pommes'), rate('product_ticket_samstag'), rate('product_bier')
        if food:
            self.assertEqual(food, {10.0})
        if drink:
            self.assertEqual(drink, {20.0})
        if ticket and food:
            self.assertNotEqual(ticket, food, 'Tickets dürfen nicht den Essen-Satz bekommen')
