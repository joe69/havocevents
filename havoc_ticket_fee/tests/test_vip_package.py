# -*- coding: utf-8 -*-
from odoo import Command
from odoo.tests import tagged

from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon


@tagged('post_install', '-at_install')
class TestHavocVipPackage(TestWebsiteEventSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('havoc_ticket_fee.percent', '5.0')
        cls.package = cls.env['product.product'].create({
            'name': 'VIP-Package', 'type': 'service', 'list_price': 80.0,
            'taxes_id': [Command.set(cls.zero_tax.ids)],
        })
        cls.vip = cls.env['event.event.ticket'].create({
            'event_id': cls.event.id, 'name': 'VIP', 'product_id': cls.product_event.id,
            'price': 40.0, 'havoc_package_product_id': cls.package.id,
        })

    def _cart(self):
        return self.env['sale.order'].create({
            'partner_id': self.env.ref('base.partner_admin').id,
            'website_id': self.website.id,
            'pricelist_id': self.pricelist.id if hasattr(self, 'pricelist') else False,
        })

    def _lines(self, order):
        ticket = order.order_line.filtered(lambda l: l.event_ticket_id and not l.is_havoc_package and not l.is_havoc_fee)
        return ticket, order.order_line.filtered('is_havoc_package'), order.order_line.filtered('is_havoc_fee')

    def test_display_price_includes_package(self):
        self.assertAlmostEqual(self.vip.price_reduce_taxinc, 120.0)
        self.assertAlmostEqual(self.ticket.price_reduce_taxinc, 100.0, msg='Tickets ohne Paket unverändert')

    def test_cart_adds_package_and_fee(self):
        order = self._cart()
        order._cart_add(product_id=self.product_event.id, quantity=2, event_ticket_id=self.vip.id)
        ticket, package, fee = self._lines(order)
        self.assertEqual(ticket.product_uom_qty, 2)
        self.assertEqual(len(package), 1)
        self.assertEqual(package.product_id, self.package)
        self.assertEqual(package.product_uom_qty, 2)
        self.assertAlmostEqual(package.price_total, 160.0)
        self.assertFalse(package.event_ticket_id, 'Paketzeile erzeugt keine eigene Anmeldung')
        self.assertAlmostEqual(fee.price_total, 12.0, msg='5 % auf 80 + 160')
        self.assertAlmostEqual(order.amount_total, 252.0)

        # Ticketmenge ändern -> Paket folgt, Gebühr neu
        order._cart_update_line_quantity(ticket.id, 1)
        ticket, package, fee = self._lines(order)
        self.assertEqual(package.product_uom_qty, 1)
        self.assertAlmostEqual(order.amount_total, 126.0)

        # Paket "löschen" -> kommt zurück
        order._cart_update_line_quantity(package.id, 0)
        ticket, package, fee = self._lines(order)
        self.assertEqual(package.product_uom_qty, 1)
        self.assertFalse(package._is_sellable())

        # Ticket entfernen -> Paket und Gebühr weg
        order._cart_update_line_quantity(ticket.id, 0)
        self.assertFalse(order.order_line)

    def test_standard_ticket_without_package(self):
        order = self._cart()
        order._cart_add(product_id=self.product_event.id, quantity=1, event_ticket_id=self.ticket.id)
        ticket, package, fee = self._lines(order)
        self.assertFalse(package)
        self.assertAlmostEqual(fee.price_total, 5.0)

    def test_event_without_ticket_not_bookable(self):
        event = self.env['event.event'].create({
            'name': 'Ohne Ticket', 'date_begin': self.event.date_begin, 'date_end': self.event.date_end,
        })
        self.assertFalse(event.event_registrations_open)
        self.assertTrue(self.event.event_registrations_open)
