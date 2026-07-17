# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_havoc_fee = fields.Boolean(string='Ist Verwaltungsgebühr', default=False)

    def _compute_price_unit(self):
        """Gebührenzeilen vom Preislisten-Neuberechnen ausnehmen — der Betrag
        wird ausschließlich von _havoc_update_fee_line() gesetzt (analog zu
        Versandkostenzeilen in `delivery`)."""
        fee_lines = self.filtered('is_havoc_fee')
        super(SaleOrderLine, self - fee_lines)._compute_price_unit()


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_add(self, *args, **kwargs):
        res = super()._cart_add(*args, **kwargs)
        self._havoc_update_fee_line()
        return res

    def _cart_update_line_quantity(self, *args, **kwargs):
        res = super()._cart_update_line_quantity(*args, **kwargs)
        self._havoc_update_fee_line()
        return res

    def _havoc_update_fee_line(self):
        """Hält die Gebührenzeile aktuell: X% des Ticket-Bruttopreises (das,
        was der Käufer sieht). Damit der angezeigte Gebührenbetrag exakt
        stimmt, muss die Steuer am Gebühren-Produkt "im Preis enthalten" sein.
        Wird nach jeder Warenkorb-Änderung neu berechnet — die Zeile lässt
        sich dadurch auch nicht dauerhaft aus dem Warenkorb löschen."""
        self.ensure_one()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        try:
            percent = float(get_param('havoc_ticket_fee.percent', '0') or '0')
        except ValueError:
            percent = 0.0

        fee_lines = self.order_line.filtered('is_havoc_fee')
        ticket_lines = self.order_line.filtered(
            lambda l: l.event_ticket_id and not l.is_havoc_fee)
        base = sum(ticket_lines.mapped('price_total'))
        amount = self.currency_id.round(base * percent / 100.0)

        if percent <= 0 or not ticket_lines or self.currency_id.is_zero(amount):
            fee_lines.unlink()
            return

        product = self.env.ref(
            'havoc_ticket_fee.product_admin_fee', raise_if_not_found=False)
        if not product or not product.active:
            return

        vals = {
            'price_unit': amount,
            'product_uom_qty': 1.0,
            'name': 'Verwaltungsgebühr (%g %%)' % percent,
        }
        if fee_lines:
            fee_lines[0].write(vals)
            fee_lines[1:].unlink()
        else:
            self.env['sale.order.line'].create({
                'order_id': self.id,
                'product_id': product.id,
                'is_havoc_fee': True,
                **vals,
            })
