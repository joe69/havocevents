# -*- coding: utf-8 -*-
from odoo import fields, models


class EventQuestion(models.Model):
    _inherit = 'event.question'

    havoc_event_ticket_ids = fields.Many2many(
        'event.event.ticket', string='Nur für Tickets',
        help='Leer = Frage wird bei allen Tickets gestellt. Sonst nur bei den '
             'gewählten Tickettypen (z. B. T-Shirt-Größe nur beim VIP-Ticket). '
             'Gilt für Fragen, die pro Teilnehmer gestellt werden.',
    )
