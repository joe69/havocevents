# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import models


class MailMail(models.Model):
    _inherit = 'mail.mail'

    def _prepare_outgoing_body(self):
        """Bei Mails von der noreply-Adresse einen Hinweis anhängen, dass
        Antworten nicht gelesen werden. Kontaktadresse anpassbar über den
        Systemparameter `havoc.mail_contact_email`."""
        body = super()._prepare_outgoing_body()
        if body and 'noreply' in (self.email_from or '').lower():
            # Odoo (z. B. E-Mail-Marketing mit Tracking-Links) liefert den Body
            # teils als plain str. Markup + str würde den gesamten Body escapen
            # (Markup.__radd__) -> HTML käme als Text an. Daher explizit als
            # bereits sicheres HTML markieren.
            if not isinstance(body, Markup):
                body = Markup(body)
            contact = self.env['ir.config_parameter'].sudo().get_param(
                'havoc.mail_contact_email', 'office@havoc.events')
            body += Markup(
                '<div style="margin-top:16px;padding-top:12px;'
                'border-top:1px solid #dddddd;font-size:12px;color:#777777;">'
                'Dies ist eine automatisch versendete Nachricht &#8212; '
                'Antworten auf diese E-Mail werden nicht gelesen.<br/>'
                'Bei Fragen erreichst du uns unter '
                '<a href="mailto:%(contact)s">%(contact)s</a>.'
                '</div>'
            ) % {'contact': contact}
        return body
