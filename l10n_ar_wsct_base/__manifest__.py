{
    "name": "Argentina - Factura de Turismo (base)",
    "version": "18.0.1.0.0",
    "category": "Localization/Argentina",
    "summary": "Modelo de datos comun para la Factura de Turismo (RG3971 / WSCT)",
    "description": """
Factura de Turismo - Modelo de datos comun
==========================================

Agrega los campos que necesita la Factura de Turismo (comprobantes clase T,
RG 3971) y que son independientes del web service que se use para pedir el CAE:

* ``product.category``: tipo de item y codigo de turismo.
* ``res.partner``: codigo de relacion emisor / receptor.
* ``account.tax``: marca de IVA Reintegro Turismo.

Ademas crea los tipos de documento clase T (codigos 195, 196 y 197), que Odoo
admite como letra valida pero no trae cargados.

Este modulo no habla con AFIP/ARCA. Lo hacen los modulos que dependen de el:

* ``l10n_ar_afipws_wsct`` para Odoo Community (stack ADHOC ``l10n_ar_afipws_fe``).
* ``l10n_ar_edi_wsct`` para Odoo Enterprise (stack ``l10n_ar_edi``).
""",
    "author": "aceleradora.la",
    "website": "https://www.aceleradora.la",
    "license": "AGPL-3",
    "depends": [
        "account",
        "l10n_ar",
    ],
    "data": [
        "data/l10n_latam_document_type_data.xml",
        "views/account_tax_views.xml",
        "views/product_category_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
