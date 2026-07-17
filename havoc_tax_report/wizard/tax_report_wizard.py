# -*- coding: utf-8 -*-
from datetime import date

from odoo import fields, models


class HavocTaxReportWizard(models.TransientModel):
    _name = 'havoc.tax.report.wizard'
    _description = 'Mama Steuern — Berichtsassistent'

    date_from = fields.Date(
        string='Von', required=True,
        default=lambda self: date.today().replace(month=1, day=1))
    date_to = fields.Date(
        string='Bis', required=True,
        default=fields.Date.today)

    def action_print(self):
        self.ensure_one()
        return self.env.ref(
            'havoc_tax_report.action_havoc_tax_report').report_action(self)

    def action_view(self):
        self.ensure_one()
        return self.env.ref(
            'havoc_tax_report.action_havoc_tax_report_html').report_action(self)
