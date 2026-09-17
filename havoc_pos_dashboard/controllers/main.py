# -*- coding: utf-8 -*-
from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request


class HavocPosDashboardController(http.Controller):

    @http.route('/havoc/kassen', type='http', auth='user', methods=['GET'])
    def kassen_dashboard(self, period='session', **kwargs):
        if not request.env.user.has_group('point_of_sale.group_pos_user'):
            raise Forbidden()
        values = request.env['havoc.pos.dashboard']._get_data(period)
        return request.render('havoc_pos_dashboard.page', values)
