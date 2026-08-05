{
    "name": "Argentina - Factura de Turismo WSCT (Community)",
    "version": "19.0.1.0.0",
    "category": "Localization/Argentina",
    "summary": "Solicitud de CAE para comprobantes de turismo (RG3971 - WSCT) sobre el stack AFIP de ADHOC",
    "description": """
Factura de Turismo - WSCT (Odoo Community)
==========================================

Agrega el web service **WSCT** (Comprobantes de Turismo, RG 3971) al stack de
facturacion electronica de ADHOC para Odoo Community (``l10n_ar_afipws_fe``,
que usa ``pyafipws``).

Habilita los comprobantes clase T (codigos 195, 196 y 197) y expone el sistema
de punto de venta "Comprobantes de Turismo - Web Service".

Para Odoo Enterprise usar ``l10n_ar_edi_wsct`` en su lugar. Ambos modulos son
mutuamente excluyentes: implementan el mismo web service sobre stacks distintos.
""",
    "author": "aceleradora.la",
    "website": "https://www.aceleradora.la",
    "license": "AGPL-3",
    "depends": [
        "l10n_ar_wsct_base",
        "l10n_ar_afipws",
        "l10n_ar_afipws_fe",
    ],
    "external_dependencies": {"python": ["pyafipws"]},
    "data": [],
    "installable": True,
    "auto_install": False,
    "application": False,
}
