{
    "name": "Argentina - Factura de Turismo WSCT (Enterprise)",
    "version": "18.0.1.0.0",
    "category": "Localization/Argentina",
    "summary": "Solicitud de CAE para comprobantes de turismo (RG3971 - WSCT) sobre l10n_ar_edi",
    "description": """
Factura de Turismo - WSCT (Odoo Enterprise)
===========================================

Agrega el web service **WSCT** (Comprobantes de Turismo, RG 3971) a la
facturacion electronica argentina de Odoo Enterprise (``l10n_ar_edi``, que usa
``zeep``).

Habilita los comprobantes clase T (codigos 195, 196 y 197) y expone el sistema
de punto de venta "Comprobantes de Turismo - Web Service".

Es el equivalente Enterprise de ``l10n_ar_afipws_wsct``. Los dos modulos son
mutuamente excluyentes: implementan el mismo web service sobre stacks distintos
(``l10n_ar_edi`` con zeep uno, ``l10n_ar_afipws_fe`` con pyafipws el otro) y no
comparten ni los nombres de los campos ni los de los metodos.

.. warning::

   El codigo esta escrito siguiendo el patron de ``l10n_ar_wsmtxca_ws`` de ADHOC
   (el unico agregado publico de un web service sobre ``l10n_ar_edi``), pero
   ``l10n_ar_edi`` es un modulo de Odoo Enterprise, de codigo cerrado. No se pudo
   compilar ni ejecutar contra la fuente real, asi que **hay que probarlo en el
   entorno de homologacion de AFIP/ARCA antes de usarlo en produccion**.
""",
    "author": "aceleradora.la",
    "website": "https://www.aceleradora.la",
    "license": "AGPL-3",
    "depends": [
        "l10n_ar_wsct_base",
        "l10n_ar_edi",
    ],
    "data": [],
    "installable": True,
    "auto_install": False,
    "application": False,
}
