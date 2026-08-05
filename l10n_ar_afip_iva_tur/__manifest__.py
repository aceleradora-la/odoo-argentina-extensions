{
    "name": "Argentina - AFIP IVA Turismo Exportable",
    "version": "18.0.1.0.0",
    "category": "Localization/Argentina",
    "summary": "Generación del exportable para el Régimen de Alojamiento de Turistas Extranjeros (IVA Turismo).",
    "description": """
AFIP/ARCA - Exportable de IVA Turismo
=====================================

Genera el archivo TXT de presentación del Régimen de Alojamiento de Turistas
Extranjeros (régimen 8089) a partir de los comprobantes clase T emitidos por
el web service WSCT.

Funciona tanto sobre Odoo Community como sobre Odoo Enterprise: no depende de
un stack de facturación electrónica en particular, sino que lee el XML del
pedido de CAE a través del método ``account.move._l10n_ar_iva_tur_get_afip_xml``,
que implementan ``l10n_ar_afipws_wsct`` (Community) y ``l10n_ar_edi_wsct``
(Enterprise).
""",
    "author": "aceleradora.la",
    "website": "https://www.aceleradora.la",
    "license": "AGPL-3",
    "depends": [
        "l10n_ar_wsct_base",
        "l10n_latam_invoice_document",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/afip_iva_tur_security.xml",
        "views/res_company_views.xml",
        "views/account_journal_view.xml",
        "wizard/afip_iva_tur_wizard_views.xml",
        "views/afip_iva_tur_report_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "images": ["static/description/icon.png"],
}
