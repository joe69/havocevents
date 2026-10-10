# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon


@tagged('post_install', '-at_install')
class TestHavocTicketPhases(TestWebsiteEventSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('havoc_ticket_fee.percent', '0')
        now = fields.Datetime.now()
        Ticket = cls.env['event.event.ticket']
        cls.early = Ticket.create({'event_id': cls.event.id, 'name': 'Early', 'product_id': cls.product_event.id, 'price': 35})
        cls.normal = Ticket.create({'event_id': cls.event.id, 'name': 'Normal', 'product_id': cls.product_event.id, 'price': 42,
                                    'havoc_previous_phase_id': cls.early.id, 'end_sale_datetime': now + timedelta(days=2)})
        cls.late = Ticket.create({'event_id': cls.event.id, 'name': 'Late', 'product_id': cls.product_event.id, 'price': 49,
                                  'havoc_previous_phase_id': cls.normal.id, 'start_sale_datetime': now + timedelta(days=2)})

    def _cart(self):
        return self.env['sale.order'].create({'partner_id': self.env.ref('base.partner_admin').id, 'website_id': self.website.id})

    def test_phase_chain(self):
        # Early läuft -> Normal wartet, Late wartet
        self.assertTrue(self.early.sale_available)
        self.assertTrue(self.normal.havoc_phase_waiting)
        self.assertFalse(self.normal.sale_available)
        self.assertFalse(self.late.sale_available)

        # Early beendet (Enddatum in der Vergangenheit) -> Normal buchbar, Late noch nicht (Startdatum)
        self.early.end_sale_datetime = fields.Datetime.now() - timedelta(minutes=1)
        self.env.invalidate_all()
        self.assertFalse(self.early.sale_available)
        self.assertFalse(self.normal.havoc_phase_waiting)
        self.assertTrue(self.normal.sale_available)
        self.assertFalse(self.late.sale_available)

    def test_phase_ends_when_sold_out(self):
        self.early.write({'seats_limited': True, 'seats_max': 1})
        self.env['event.registration'].create({'event_id': self.event.id, 'event_ticket_id': self.early.id, 'name': 'X'})
        self.env.invalidate_all()
        self.assertTrue(self.early.is_sold_out)
        self.assertTrue(self.normal.sale_available, 'Early ausverkauft -> Normal startet')

    def test_waiting_ticket_cannot_be_added_to_cart(self):
        order = self._cart()
        order._cart_add(product_id=self.product_event.id, quantity=1, event_ticket_id=self.normal.id)
        self.assertFalse(order.order_line.filtered(lambda l: l.event_ticket_id == self.normal))
        order._cart_add(product_id=self.product_event.id, quantity=1, event_ticket_id=self.early.id)
        self.assertEqual(order.order_line.filtered(lambda l: l.event_ticket_id == self.early).product_uom_qty, 1)
