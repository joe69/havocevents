# -*- coding: utf-8 -*-
from odoo import fields, http
from odoo.http import request
from odoo.addons.website.controllers.main import Website


class HavocWebsite(Website):

    @http.route('/', auth='public', website=True, sitemap=True)
    def index(self, **kw):
        """One-Pager: Startseite zeigt direkt das (einzige) Event mit
        Banner, Tickettypen und Infos. Nächstes bevorstehendes Event zuerst,
        sonst das zuletzt gelaufene. Ohne veröffentlichtes Event greift der
        Standard-Fallback von Odoo."""
        Event = request.env['event.event']
        domain = [('website_published', '=', True)]
        event = Event.search(
            domain + [('date_end', '>=', fields.Datetime.now())],
            order='date_begin asc', limit=1,
        ) or Event.search(domain, order='date_begin desc', limit=1)
        if not event:
            return super().index(**kw)
        values = {
            'event': event,
            'main_object': event,
            'range': range,
            'registration_error_code': kw.get('registration_error_code'),
            'slots': event.event_slot_ids._filter_open_slots().grouped('date'),
            'website_visitor_timezone': request.env['website.visitor']._get_visitor_timezone(),
        }
        return request.render('theme_havoc.homepage', values)
