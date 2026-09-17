# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models

PERIODS = [
    ('session', 'Laufende / letzte Sitzung'),
    ('today', 'Heute'),
    ('all', 'Gesamt'),
]
REFRESH_SECONDS = 60
TOP_PRODUCTS = 10


class HavocPosDashboard(models.AbstractModel):
    _name = 'havoc.pos.dashboard'
    _description = 'Kassen-Dashboard (live)'

    @api.model
    def _today_bounds_utc(self):
        """Heutiger Tag in der Zeitzone des Benutzers, als naive UTC-Grenzen."""
        now_local = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = (start_local - start_local.utcoffset()).replace(tzinfo=None)
        return start_utc, start_utc + timedelta(days=1)

    @api.model
    def _session_for(self, config):
        """Laufende Sitzung, sonst die zuletzt abgeschlossene."""
        if config.current_session_id:
            return config.current_session_id
        return self.env['pos.session'].search(
            [('config_id', '=', config.id), ('state', '=', 'closed')],
            order='stop_at desc, id desc', limit=1)

    @api.model
    def _session_label(self, session):
        if not session:
            return 'noch keine Sitzung'
        if session.state == 'closed':
            stamp = session.stop_at or session.start_at
            when = fields.Datetime.context_timestamp(self, stamp).strftime('%d.%m. %H:%M') if stamp else ''
            return f'geschlossen {when}'.strip()
        when = fields.Datetime.context_timestamp(self, session.start_at).strftime('%d.%m. %H:%M') if session.start_at else ''
        return f'offen seit {when}'.strip()

    @api.model
    def _get_data(self, period='session'):
        if period not in dict(PERIODS):
            period = 'session'
        company = self.env.company
        Order = self.env['pos.order']
        configs = self.env['pos.config'].search([('company_id', '=', company.id)], order='name, id')

        base_domain = [
            ('company_id', '=', company.id),
            ('state', 'in', ('paid', 'done', 'invoiced')),
        ]
        if period == 'today':
            start, end = self._today_bounds_utc()
            base_domain += [('date_order', '>=', start), ('date_order', '<', end)]

        rows = []
        all_orders = Order
        method_amounts = defaultdict(float)
        for config in configs:
            domain = base_domain + [('config_id', '=', config.id)]
            session_label = ''
            if period == 'session':
                session = self._session_for(config)
                session_label = self._session_label(session)
                if not session:
                    rows.append(self._row(config, session_label, Order))
                    continue
                domain += [('session_id', '=', session.id)]
            orders = Order.search(domain)
            all_orders |= orders
            row = self._row(config, session_label, orders)
            for method, amount in row['payments'].items():
                method_amounts[method] += amount
            rows.append(row)

        methods = self.env['pos.payment.method'].browse(
            [m.id for m in method_amounts]).sorted(lambda m: (m.sequence, m.id))
        blacky_orders = all_orders.filtered(lambda o: o._havoc_is_unbooked())
        totals = {
            'orders': len(all_orders),
            'booked': sum((all_orders - blacky_orders).mapped('amount_total')),
            'blacky': sum(blacky_orders.mapped('amount_total')),
            'total': sum(all_orders.mapped('amount_total')),
            'payments': {m: method_amounts[m] for m in methods},
        }
        return {
            'period': period,
            'periods': PERIODS,
            'rows': rows,
            'methods': methods,
            'totals': totals,
            'top_products': self._top_products(all_orders),
            'currency': company.currency_id,
            'company': company,
            'generated_at': fields.Datetime.context_timestamp(self, fields.Datetime.now()).strftime('%d.%m.%Y %H:%M:%S'),
            'refresh': REFRESH_SECONDS,
        }

    @api.model
    def _row(self, config, session_label, orders):
        blacky = orders.filtered(lambda o: o._havoc_is_unbooked())
        payments = defaultdict(float)
        for payment in orders.payment_ids:
            payments[payment.payment_method_id] += payment.amount
        return {
            'config': config,
            'session_label': session_label,
            'orders': len(orders),
            'booked': sum((orders - blacky).mapped('amount_total')),
            'blacky': sum(blacky.mapped('amount_total')),
            'total': sum(orders.mapped('amount_total')),
            'payments': dict(payments),
        }

    @api.model
    def _top_products(self, orders):
        """Meistverkaufte Produkte (alle Bestellungen, auch Blacky – Ware ist Ware)."""
        if not orders:
            return []
        groups = self.env['pos.order.line']._read_group(
            [('order_id', 'in', orders.ids)],
            groupby=['product_id'],
            aggregates=['qty:sum', 'price_subtotal_incl:sum'],
            order='qty:sum desc',
            limit=TOP_PRODUCTS,
        )
        return [{'product': product, 'qty': qty, 'amount': amount} for product, qty, amount in groups]
