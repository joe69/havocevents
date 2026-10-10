# -*- coding: utf-8 -*-
from odoo import api, fields, models


class EventEventTicket(models.Model):
    _inherit = 'event.event.ticket'

    # Verkaufsphasen (Early -> Normal -> Late): ein Ticket startet erst, wenn
    # die vorherige Phase vorbei ist (Verkaufsende erreicht oder ausverkauft).
    havoc_previous_phase_id = fields.Many2one(
        'event.event.ticket', string='Startet nach',
        domain="[('event_id', '=', event_id), ('id', '!=', id)]",
        help='Verkaufsphase: Dieses Ticket ist erst buchbar, wenn das gewählte '
             'Ticket nicht mehr verkauft wird (Verkaufsende erreicht oder '
             'ausverkauft). Eigene Start-/Enddaten gelten zusätzlich.',
    )
    havoc_phase_waiting = fields.Boolean(
        string='Wartet auf vorherige Phase', compute='_compute_havoc_phase_waiting')

    @api.depends('havoc_previous_phase_id')
    def _compute_havoc_phase_waiting(self):
        for ticket in self:
            prev = ticket.havoc_previous_phase_id
            ticket.havoc_phase_waiting = bool(prev) and not prev.is_expired and not prev.is_sold_out

    def _compute_sale_available(self):
        super()._compute_sale_available()
        for ticket in self:
            if ticket.havoc_phase_waiting:
                ticket.sale_available = False

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
