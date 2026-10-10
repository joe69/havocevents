# -*- coding: utf-8 -*-
from odoo import _
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.website_event_sale.controllers.main import WebsiteEventSaleController


class HavocWebsiteEventSaleController(WebsiteEventSaleController):

    def _create_attendees_from_registration_post(self, event, registration_data):
        # Tickets außerhalb ihrer Verkaufsphase (wartet auf Vorphase, noch nicht
        # gestartet, abgelaufen) über die Website nicht anmelden lassen —
        # Odoo würde sonst eine Anmeldung ohne Warenkorbzeile anlegen.
        ticket_ids = {int(d['event_ticket_id']) for d in registration_data if d.get('event_ticket_id')}
        tickets = request.env['event.event.ticket'].sudo().browse(list(ticket_ids)).exists()
        unavailable = tickets.filtered(lambda t: not t.sale_available)
        if unavailable:
            raise UserError(_('Folgende Tickets sind derzeit nicht erhältlich: %s', ', '.join(unavailable.mapped('name'))))
        return super()._create_attendees_from_registration_post(event, registration_data)
