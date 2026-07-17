# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class HavocTaxReport(models.AbstractModel):
    _name = 'report.havoc_tax_report.report_template'
    _description = 'Mama Steuern — Berichtsdaten'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['havoc.tax.report.wizard'].browse(docids)[:1]
        company = self.env.company
        currency = company.currency_id
        date_from = wizard.date_from
        date_to = wizard.date_to
        dt_from = fields.Datetime.to_datetime(date_from)
        dt_end = fields.Datetime.to_datetime(date_to) + timedelta(days=1)

        # ------------------------------------------------------------------
        # Verkaufsaufträge: Website vs. Backend/manuell
        # ------------------------------------------------------------------
        orders = self.env['sale.order'].search([
            ('company_id', '=', company.id),
            ('state', '=', 'sale'),
            ('date_order', '>=', dt_from),
            ('date_order', '<', dt_end),
        ])
        web_orders = orders.filtered('website_id')
        back_orders = orders - web_orders

        # POS-Bestellungen
        pos_orders = self.env['pos.order'].search([
            ('company_id', '=', company.id),
            ('state', 'in', ('paid', 'done', 'invoiced')),
            ('date_order', '>=', dt_from),
            ('date_order', '<', dt_end),
        ])

        def block(count, untaxed, tax_amount):
            return {
                'count': count,
                'untaxed': untaxed,
                'tax': tax_amount,
                'total': untaxed + tax_amount,
            }

        channels = [
            ('Website-Verkauf', block(
                len(web_orders),
                sum(web_orders.mapped('amount_untaxed')),
                sum(web_orders.mapped('amount_tax')))),
            ('POS-Verkauf (Abendkassa)', block(
                len(pos_orders),
                sum(o.amount_total - o.amount_tax for o in pos_orders),
                sum(pos_orders.mapped('amount_tax')))),
            ('Backend / manuell', block(
                len(back_orders),
                sum(back_orders.mapped('amount_untaxed')),
                sum(back_orders.mapped('amount_tax')))),
        ]
        total = block(
            sum(c[1]['count'] for c in channels),
            sum(c[1]['untaxed'] for c in channels),
            sum(c[1]['tax'] for c in channels))

        # ------------------------------------------------------------------
        # Umsatz je Tickettyp (aus Verkaufsaufträgen)
        # ------------------------------------------------------------------
        tickets = {}
        for line in orders.order_line.filtered('event_ticket_id'):
            ticket = line.event_ticket_id
            entry = tickets.setdefault(ticket.id, {
                'name': '%s — %s' % (ticket.event_id.name, ticket.name),
                'qty': 0.0, 'untaxed': 0.0, 'total': 0.0,
            })
            entry['qty'] += line.product_uom_qty
            entry['untaxed'] += line.price_subtotal
            entry['total'] += line.price_total
        ticket_rows = sorted(tickets.values(), key=lambda t: -t['total'])

        # ------------------------------------------------------------------
        # Steuern nach Satz (gebuchte Belege in Verkaufsjournalen:
        # Kundenrechnungen, Gutschriften, POS-Sitzungsbuchungen)
        # ------------------------------------------------------------------
        AML = self.env['account.move.line']
        common_domain = [
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('journal_id.type', '=', 'sale'),
        ]
        taxes = {}
        for line in AML.search(common_domain + [('tax_ids', '!=', False)]):
            for tax in line.tax_ids:
                entry = taxes.setdefault(tax.id, {
                    'name': tax.name, 'percent': tax.amount,
                    'base': 0.0, 'amount': 0.0,
                })
                entry['base'] += -line.balance
        for line in AML.search(common_domain + [('tax_line_id', '!=', False)]):
            tax = line.tax_line_id
            entry = taxes.setdefault(tax.id, {
                'name': tax.name, 'percent': tax.amount,
                'base': 0.0, 'amount': 0.0,
            })
            entry['amount'] += -line.balance
        uva_kz = {20.0: 'KZ 022', 13.0: 'KZ 006', 10.0: 'KZ 029'}
        tax_rows = sorted(
            (dict(t, kz=uva_kz.get(t['percent'], '')) for t in taxes.values()),
            key=lambda t: -t['percent'])

        # ------------------------------------------------------------------
        # Zahlarten — Online (Zahlungsanbieter) und POS (Zahlungsmethoden),
        # zum Abgleich mit den Auszahlungen der Anbieter / der Kassa
        # ------------------------------------------------------------------
        online_payments = {}
        transactions = self.env['payment.transaction'].search([
            ('company_id', '=', company.id),
            ('state', '=', 'done'),
            ('last_state_change', '>=', dt_from),
            ('last_state_change', '<', dt_end),
        ])
        for tx in transactions:
            entry = online_payments.setdefault(tx.provider_id.id, {
                'name': tx.provider_id.name, 'count': 0, 'amount': 0.0,
            })
            entry['count'] += 1
            entry['amount'] += tx.amount
        online_rows = sorted(online_payments.values(), key=lambda p: -p['amount'])

        pos_payments = {}
        for payment in self.env['pos.payment'].search([
            ('payment_date', '>=', dt_from),
            ('payment_date', '<', dt_end),
            ('pos_order_id.company_id', '=', company.id),
            ('pos_order_id.state', 'in', ('paid', 'done', 'invoiced')),
        ]):
            method = payment.payment_method_id
            entry = pos_payments.setdefault(method.id, {
                'name': method.name, 'count': 0, 'amount': 0.0,
            })
            entry['count'] += 1
            entry['amount'] += payment.amount
        pos_pay_rows = sorted(pos_payments.values(), key=lambda p: -p['amount'])

        return {
            'doc_ids': docids,
            'doc_model': 'havoc.tax.report.wizard',
            'docs': wizard,
            'company': company,
            'currency': currency,
            'date_from': date_from,
            'date_to': date_to,
            'channels': channels,
            'total': total,
            'ticket_rows': ticket_rows,
            'tax_rows': tax_rows,
            'online_rows': online_rows,
            'pos_pay_rows': pos_pay_rows,
        }
