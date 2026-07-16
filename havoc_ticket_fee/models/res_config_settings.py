# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    havoc_ticket_fee_percent = fields.Float(
        string='Verwaltungsgebühr auf Tickets (%)',
        config_parameter='havoc_ticket_fee.percent',
        help='Prozentualer Aufschlag auf Event-Tickets im Warenkorb. '
             '0 = keine Gebühr.',
    )
