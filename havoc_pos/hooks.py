# -*- coding: utf-8 -*-
"""Nachbearbeitung bei der Installation.

Alles, was von der konkreten Datenbank abhängt (Steuersätze der Firma,
Outstanding-Konto, bereits vorhandene Zahlarten wie Kartenterminals), kann
nicht statisch in den XML-Daten stehen und wird hier gesetzt.
"""
import logging

_logger = logging.getLogger(__name__)

MODULE = 'havoc_pos'

FOOD_PRODUCTS = ('product_pommes', 'product_chicken_nuggets', 'product_mozzarella_sticks')
TICKET_PRODUCTS = ('product_ticket_weekend', 'product_ticket_freitag', 'product_ticket_samstag')
POS_CONFIGS = (
    'pos_config_getraenke_1', 'pos_config_getraenke_2', 'pos_config_garderobe',
    'pos_config_merchandise', 'pos_config_eintritt',
)


def post_init_hook(env):
    company = env.ref(f'{MODULE}.journal_bargeld').company_id or env.company
    _setup_taxes(env, company)
    _setup_bargeld_method(env, company)
    _setup_pos_payment_methods(env, company)


# ----------------------------------------------------------------------
# Steuern
# ----------------------------------------------------------------------
def _search_sale_tax(env, company, percent, price_include=None):
    domain = [
        ('company_id', '=', company.id),
        ('type_tax_use', '=', 'sale'),
        ('amount_type', '=', 'percent'),
        ('amount', '=', percent),
        ('active', '=', True),
    ]
    if price_include is not None:
        domain.append(('price_include', '=', price_include))
    return env['account.tax'].search(domain, order='sequence, id', limit=1)


def _find_sale_tax(env, company, template_xmlid, percent):
    """Steuer der Firma über die l10n-Vorlage, sonst nach Prozentsatz.

    Die Preisliste nennt Bruttopreise. Ist die gefundene Steuer nicht
    preisinklusiv, wird eine preisinklusive Variante mit gleichem Satz
    bevorzugt, damit die Kassa 5 € Bier nicht als 6 € verkauft."""
    tax = env['account.chart.template'].with_company(company).ref(
        template_xmlid, raise_if_not_found=False)
    if not (tax and tax.active and tax.type_tax_use == 'sale' and tax.company_id == company):
        tax = _search_sale_tax(env, company, percent)
    if tax and not tax.price_include:
        tax = _search_sale_tax(env, company, percent, price_include=True) or tax
    return tax


def _ensure_price_included(env, company, tax):
    """Liefert eine preisinklusive Steuer zu ``tax`` (Preisliste = Bruttopreise).

    Reihenfolge:
    1. Steuer ist schon preisinklusiv -> unverändert.
    2. Firma hat noch nicht gebucht -> Firmenstandard "Preise inkl. Steuern"
       setzen (Odoo erlaubt das später nicht mehr).
    3. Sonst eine vorhandene inklusive Steuer gleichen Satzes verwenden,
    4. sonst eine Kopie "<Name> (inkl.)" anlegen, damit bestehende Steuern,
       Produkte und Rechnungen unverändert bleiben.
    """
    if not tax or tax.price_include:
        return tax
    if (company.account_price_include != 'tax_included'
            and not company.sudo()._existing_accounting()):
        company.account_price_include = 'tax_included'
        env['account.tax'].invalidate_model(['price_include', 'company_price_include'])
        _logger.info('havoc_pos: Firmenstandard "Preise inkl. Steuern" gesetzt '
                     '(noch keine Buchungen vorhanden).')
        if tax.price_include:
            return tax
    copy_name = f'{tax.name} (inkl.)'
    existing = env['account.tax'].search([
        ('company_id', '=', company.id), ('type_tax_use', '=', 'sale'),
        ('name', '=', copy_name), ('active', '=', True),
    ], limit=1) or _search_sale_tax(env, company, tax.amount, price_include=True)
    if existing:
        return existing
    copy = tax.copy({'name': copy_name, 'price_include_override': 'tax_included'})
    _logger.info('havoc_pos: preisinklusive Steuer "%s" als Kopie von "%s" angelegt.',
                 copy.name, tax.name)
    return copy


def _find_ticket_taxes(env, company):
    """Abendkassa-Tickets wie die Online-Tickets besteuern; sonst 13 % (AT)."""
    Ticket = env.get('event.event.ticket')
    if Ticket is not None and 'product_id' in Ticket._fields:
        tickets = Ticket.sudo().search(
            [('company_id', 'in', (company.id, False))], order='id desc')
        for ticket in tickets:
            taxes = ticket.product_id.taxes_id.filtered(
                lambda t: t.company_id == company and t.type_tax_use == 'sale')
            if taxes:
                return taxes
    return _find_sale_tax(env, company, 'account_tax_template_sales_13_code006', 13.0)


def _module_products(env):
    data = env['ir.model.data'].search([
        ('module', '=', MODULE), ('model', '=', 'product.product')])
    return env['product.product'].browse(data.mapped('res_id')).exists()


def _apply_taxes(company, products, taxes, label):
    if not taxes:
        _logger.warning('havoc_pos: keine Steuer für %s gefunden, Firmenstandard bleibt.', label)
        return
    for template in products.product_tmpl_id:
        keep = template.taxes_id.filtered(lambda t: t.company_id != company)
        template.taxes_id = [(6, 0, (keep | taxes).ids)]
    _logger.info('havoc_pos: %s -> %s (%d Produkte)', label,
                 ', '.join(taxes.mapped('name')), len(products))
    if any(not t.price_include for t in taxes):
        _logger.warning(
            'havoc_pos: Steuer "%s" ist NICHT preisinklusiv. Die Produktpreise sind '
            'Bruttopreise laut Preisliste; die Kassa würde die Steuer zusätzlich '
            'aufschlagen. Bitte in Einstellungen > Buchhaltung "Standard-Verkaufspreise: '
            'inkl. Steuern" setzen oder an der Steuer "Im Preis enthalten" aktivieren.',
            ', '.join(taxes.mapped('name')))


def _setup_taxes(env, company):
    products = _module_products(env)
    food = env['product.product'].browse([env.ref(f'{MODULE}.{x}').id for x in FOOD_PRODUCTS])
    tickets = env['product.product'].browse([env.ref(f'{MODULE}.{x}').id for x in TICKET_PRODUCTS])
    rest = products - food - tickets

    food_tax = _ensure_price_included(
        env, company, _find_sale_tax(env, company, 'account_tax_template_sales_10_code029', 10.0))
    ticket_taxes = env['account.tax']
    for tax in _find_ticket_taxes(env, company):
        ticket_taxes |= _ensure_price_included(env, company, tax)
    rest_tax = _ensure_price_included(
        env, company, _find_sale_tax(env, company, 'account_tax_template_sales_20_code022', 20.0))

    _apply_taxes(company, food, food_tax, 'Essen 10 %')
    _apply_taxes(company, tickets, ticket_taxes, 'Abendkassa-Tickets')
    _apply_taxes(company, rest, rest_tax, 'Getränke/Merch/Garderobe 20 %')


# ----------------------------------------------------------------------
# Zahlart Bargeld
# ----------------------------------------------------------------------
def _setup_bargeld_method(env, company):
    """Outstanding-Konto wie Odoo es für Bank-Zahlarten selbst vorschlägt
    (siehe pos.payment.method._onchange_journal_id)."""
    method = env.ref(f'{MODULE}.payment_method_bargeld')
    if method.outstanding_account_id:
        return
    chart_template = env['account.chart.template'].with_company(company)
    account = (chart_template.ref('account_journal_payment_debit_account_id', raise_if_not_found=False)
               or company.transfer_account_id)
    if account:
        method.outstanding_account_id = account
    else:
        _logger.warning('havoc_pos: kein Outstanding-Konto für Zahlart Bargeld gefunden.')


def _setup_pos_payment_methods(env, company):
    """Vorhandene Nicht-Bar-Zahlarten (z. B. Kartenterminal) an alle neuen Kassen hängen."""
    bargeld = env.ref(f'{MODULE}.payment_method_bargeld')
    methods = env['pos.payment.method'].search([
        ('company_id', '=', company.id),
        ('id', '!=', bargeld.id),
        ('journal_id.type', '=', 'bank'),
        ('journal_id.currency_id', 'in', (False, company.currency_id.id)),
        ('split_transactions', '=', False),
    ])
    configs = env['pos.config'].browse([env.ref(f'{MODULE}.{x}').id for x in POS_CONFIGS])
    # Odoo erlaubt keine Zahlart-Änderung bei offener Sitzung (bei der
    # Erstinstallation gibt es noch keine; relevant nur bei Wiederholung)
    configs = configs.filtered(lambda c: not c.current_session_id)
    if methods and configs:
        configs.write({'payment_method_ids': [(4, m.id) for m in methods]})
    _logger.info('havoc_pos: Zahlarten je Kasse: %s',
                 ', '.join((bargeld | methods).mapped('name')))
