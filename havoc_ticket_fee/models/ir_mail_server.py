# -*- coding: utf-8 -*-
from email.utils import formataddr, parseaddr

from odoo import models


class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'

    def send_email(self, message, *args, **kwargs):
        """Absender-Anzeigename auf die Marke zwingen (statt Firmenname).
        Die E-Mail-Adresse selbst bleibt unverändert (noreply@havoc.events);
        das Unternehmen in Odoo heißt weiterhin wie im Firmenbuch.
        Anpassbar über den Systemparameter `havoc.mail_sender_name`."""
        sender_name = self.env['ir.config_parameter'].sudo().get_param(
            'havoc.mail_sender_name', 'Havoc Events')
        if sender_name:
            for header in ('From', 'Reply-To'):
                value = message.get(header)
                if value:
                    _old_name, email_addr = parseaddr(value)
                    if email_addr:
                        message.replace_header(
                            header, formataddr((sender_name, email_addr)))
            # Firmenname im Betreff durch den Markennamen ersetzen
            # (die Standardvorlagen setzen überall den Unternehmensnamen ein)
            subject = message.get('Subject')
            if subject:
                subject = str(subject)
                new_subject = subject
                for company_name in self.env['res.company'].sudo().search([]).mapped('name'):
                    if company_name:
                        new_subject = new_subject.replace(company_name, sender_name)
                if new_subject != subject:
                    message.replace_header('Subject', new_subject)
        return super().send_email(message, *args, **kwargs)
