# -*- coding: utf-8 -*-
from odoo import api, models


class EventEvent(models.Model):
    _inherit = 'event.event'

    @api.depends('event_ticket_ids')
    def _compute_event_registrations_open(self):
        # Odoo lässt bei Events ohne Tickettyp eine kostenlose Anmeldung zu.
        # HAVOC verkauft ausschließlich über Tickets: ohne Ticket keine Anmeldung,
        # damit ein angekündigtes Event vor dem Vorverkaufsstart nicht gratis buchbar ist.
        super()._compute_event_registrations_open()
        for event in self:
            if not event.is_multi_slots and not event.event_ticket_ids:
                event.event_registrations_open = False
