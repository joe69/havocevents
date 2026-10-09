# -*- coding: utf-8 -*-
from odoo import fields, models


class EventEventTicket(models.Model):
    _inherit = 'event.event.ticket'

    havoc_package_product_id = fields.Many2one(
        'product.product', string='Zusatzpaket',
        help='Wird pro Ticket automatisch als eigene Position in den Warenkorb '
             'gelegt (eigene Steuer, z. B. VIP-Package mit 20 %). Menge folgt '
             'immer der Ticketmenge; die Verwaltungsgebühr gilt für beides.',
    )

    def _havoc_package_price_incl(self):
        """Bruttopreis des Zusatzpakets (so, wie ihn der Kunde im Warenkorb sieht)."""
        self.ensure_one()
        product = self.sudo().havoc_package_product_id
        if not product:
            return 0.0
        company = self.event_id.company_id or self.env.company
        taxes = product.taxes_id.filtered(lambda t: t.company_id == company)
        return taxes.compute_all(
            product.lst_price, company.currency_id, 1.0, product=product)['total_included']

    def _compute_price_reduce_taxinc(self):
        # Nur Anzeige (Ticket-Popup, Preisspanne, Startseite): Ticket + Paket,
        # damit beim VIP-Ticket der Gesamtpreis (z. B. 120 €) erscheint.
        super()._compute_price_reduce_taxinc()
        for ticket in self:
            if ticket.havoc_package_product_id:
                ticket.price_reduce_taxinc += ticket._havoc_package_price_incl()
